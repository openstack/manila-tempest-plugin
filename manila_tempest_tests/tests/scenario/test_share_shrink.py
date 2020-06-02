#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import six
import time

from oslo_log import log as logging
from tempest import config
from tempest.lib import exceptions
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.scenario import manager_share as manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ShareShrinkBase(manager.ShareScenarioTest):

    """This test case uses the following flow:

     * Launch an instance
     * Create share (Configured size + 1)
     * Configure RW access to the share
     * Perform ssh to instance
     * Mount share
     * Write data in share (in excess of 1GB)
     * Shrink share to 1GB (fail expected)
     * Delete data from share
     * Shrink share to 1GB
     * Write more than 1GB of data (fail expected)
     * Unmount share
     * Delete share
     * Terminate the instance
    """

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_shrink_tests, 'Shrink share tests are disabled.')
    def test_create_shrink_and_write(self):
        default_share_size = CONF.share.share_size
        share_size = CONF.share.share_size + 1

        LOG.debug('Step 1 - create instance')
        instance = self.boot_instance(wait_until="BUILD")

        LOG.debug('Step 2 - create share of size {} Gb'.format(share_size))
        share = self.create_share(size=share_size)

        LOG.debug('Step 3 - wait for active instance')
        instance = self.wait_for_active_instance(instance["id"])
        remote_client = self.init_remote_client(instance)

        LOG.debug('Step 4 - grant access')
        location = self.get_share_export_location_for_mount(share)
        self.allow_access(instance=instance, remote_client=remote_client,
                          locations=location)

        LOG.debug('Step 5 - mount')
        self.mount_share(location, remote_client)

        total_blocks = (1024 * default_share_size) / 64
        blocks = total_blocks + 4
        LOG.debug('Step 6 - writing {} * 64MB blocks'.format(blocks))
        self.write_data_to_mounted_share_using_dd(remote_client,
                                                  '/mnt/t1', '64M',
                                                  blocks, '/dev/urandom')
        ls_result = remote_client.exec_command("sudo ls -lAh /mnt/")
        LOG.debug(ls_result)

        LOG.debug('Step 8 - try update size, shrink and wait')
        self.shares_v2_client.shrink_share(share['id'],
                                           new_size=default_share_size)
        self.shares_v2_client.wait_for_share_status(
            share['id'], ['shrinking_possible_data_loss_error', 'available'])

        share = self.shares_v2_client.get_share(share["id"])

        if share["status"] == constants.STATUS_AVAILABLE:
            params = {'resource_id': share['id']}
            messages = self.shares_v2_client.list_messages(params=params)
            self.assertIn('009',
                          [message['action_id'] for message in messages])
            self.assertEqual(share_size, int(share["size"]))

        LOG.debug('Step 9 - delete data')
        remote_client.exec_command("sudo rm /mnt/t1")

        ls_result = remote_client.exec_command("sudo ls -lAh /mnt/")
        LOG.debug(ls_result)

        # Deletion of files can be an asynchronous activity on the backend.
        # Thus we need to wait until timeout for the space to be released
        # and repeating the shrink request until success
        LOG.debug('Step 10 - reset and shrink')
        self.share_shrink_retry_until_success(share["id"],
                                              new_size=default_share_size)

        share = self.shares_v2_client.get_share(share["id"])
        self.assertEqual(default_share_size, int(share["size"]))

        LOG.debug('Step 11 - write more data than allocated, should fail')
        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            self.write_data_to_mounted_share_using_dd,
            remote_client, '/mnt/t1', '64M', blocks, '/dev/urandom')

        LOG.debug('Step 12 - unmount')
        self.unmount_share(remote_client)

    def share_shrink_retry_until_success(self, share_id, new_size,
                                         status_attr='status'):
        """Try share reset, followed by shrink, until timeout"""

        check_interval = CONF.share.build_interval * 2
        share = self.shares_v2_client.get_share(share_id)
        share_current_size = share["size"]
        share_status = share[status_attr]
        start = int(time.time())
        while share_current_size != new_size:
            if (share_status ==
                    constants.STATUS_SHRINKING_POSSIBLE_DATA_LOSS_ERROR):
                self.shares_admin_v2_client.reset_state(
                    share_id, status=constants.STATUS_AVAILABLE)
            elif share_status != constants.STATUS_SHRINKING:
                try:
                    self.shares_v2_client.shrink_share(share_id,
                                                       new_size=new_size)
                except exceptions.BadRequest as e:
                    if ('New size for shrink must be less than current size'
                            in six.text_type(e)):
                        break

            time.sleep(check_interval)
            share = self.shares_v2_client.get_share(share_id)
            share_status = share[status_attr]
            share_current_size = share["size"]
            if share_current_size == new_size:
                return
            if int(time.time()) - start >= CONF.share.build_timeout:
                message = ("Share %(share_id)s failed to shrink within the "
                           "required time %(seconds)s." %
                           {"share_id": share["id"],
                            "seconds": CONF.share.build_timeout})
                raise exceptions.TimeoutException(message)


class TestShareShrinkNFS(ShareShrinkBase):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareShrinkBase, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_auxiliary_instance(
            instance=kwargs['instance'], access_level=access_level)

    def mount_share(self, location, ssh_client, target_dir=None):
        target_dir = target_dir or "/mnt"
        ssh_client.exec_command(
            "sudo mount -vt nfs \"%s\" %s" % (location, target_dir)
        )


class TestShareShrinkCIFS(ShareShrinkBase):
    protocol = "cifs"

    @classmethod
    def skip_checks(cls):
        super(ShareShrinkBase, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_auxiliary_instance(
            instance=kwargs['instance'], access_level=access_level)

    def mount_share(self, location, ssh_client, target_dir=None):
        location = location.replace("\\", "/")
        target_dir = target_dir or "/mnt"
        ssh_client.exec_command(
            "sudo mount.cifs \"%s\" %s -o guest" % (location, target_dir)
        )


class TestShareShrinkCEPHFS(ShareShrinkBase, manager.BaseShareCEPHFSTest):
    protocol = "cephfs"

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_shrink_and_write_with_ceph_fuse_client(self):
        self.mount_client = 'fuse'
        super(TestShareShrinkCEPHFS, self).test_create_shrink_and_write()


# NOTE(u_glide): this function is required to exclude ShareShrinkBase from
# executed test cases.
# See: https://docs.python.org/3/library/unittest.html#load-tests-protocol
# for details.
def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareShrinkBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
