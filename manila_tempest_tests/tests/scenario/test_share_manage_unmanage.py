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

import ddt

from oslo_log import log as logging
from tempest import config
from tempest.lib import exceptions
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.scenario import manager_share as manager
from manila_tempest_tests import utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


@ddt.ddt
class ShareManageUnmanageBase(manager.ShareScenarioTest):

    """This test case uses the following flow:

     * Launch an instance
     * Create share (1GB)
     * Configure RW access to the share
     * Perform ssh to instance
     * Mount share
     * Write data in share
     * Unmount share
     * Unmanage share
     * Attempt to access share (fail expected)
     * Manage share
     * Configure RW access to the share
     * Mount share
     * Read data from share
     * Unmount share
     * Delete share
     * Attempt to manage share (fail expected)
     * Delete failed managed share
     * Terminate the instance
    """

    @classmethod
    def skip_checks(cls):
        super(ShareManageUnmanageBase, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_manage_unmanage_tests,
        "Manage/unmanage tests are disabled.")
    @testtools.skipIf(
        CONF.share.multitenancy_enabled,
        "Manage/unmanage tests are skipped when DHSS is enabled")
    def test_create_manage_and_write(self):
        share_size = CONF.share.share_size

        LOG.debug('Step 1 - create instance')
        instance = self.boot_instance(wait_until="BUILD")

        LOG.debug('Step 2 - create share of size {} Gb'.format(share_size))
        share = self.create_share(size=share_size, cleanup=False)
        instance = self.wait_for_active_instance(instance["id"])

        LOG.debug('Step 3 - SSH to UVM')
        remote_client = self.init_remote_client(instance)

        LOG.debug('Step 4 - provide access to instance')
        self.provide_access_to_auxiliary_instance(instance, share=share)

        if utils.is_microversion_lt(CONF.share.max_api_microversion, "2.9"):
            locations = share['export_locations']
        else:
            exports = self.shares_v2_client.list_share_export_locations(
                share['id'])
            locations = [x['path'] for x in exports]

        LOG.debug('Step 5 - mount')
        self.mount_share(locations[0], remote_client)

        # Update share info, needed later
        share = self.shares_admin_v2_client.get_share(share['id'])

        LOG.debug('Step 6a - create file')
        remote_client.exec_command("sudo touch /mnt/t1")

        LOG.debug('Step 6b - write data')
        LOG.debug('Step 6b - writing 640mb')
        self.write_data_to_mounted_share_using_dd(remote_client,
                                                  '/mnt/t1', 1024,
                                                  2048, '/dev/zero')
        ls_result = remote_client.exec_command("sudo ls -lA /mnt/")
        LOG.debug(ls_result)

        LOG.debug('Step 7 - unmount share')
        self.unmount_share(remote_client)

        LOG.debug('Step 8a - unmanage share')
        self.shares_admin_v2_client.unmanage_share(share['id'])

        LOG.debug('Step 8b - wait for status change')
        self.shares_admin_v2_client.wait_for_resource_deletion(
            share_id=share['id'])

        LOG.debug('Step 9 - get share, should fail')
        self.assertRaises(
            exceptions.NotFound,
            self.shares_admin_v2_client.get_share,
            self.share['id'])

        LOG.debug('Step 10 - manage share')
        share_type = self.get_share_type()
        managed_share = self.shares_admin_v2_client.manage_share(
            share['host'],
            share['share_proto'],
            locations[0],
            share_type['id'])
        self.shares_admin_v2_client.wait_for_share_status(
            managed_share['id'], 'available')

        LOG.debug('Step 11 - grant access again')
        self.provide_access_to_auxiliary_instance(
            instance,
            share=managed_share,
            client=self.shares_admin_v2_client)

        exports = self.shares_admin_v2_client.list_share_export_locations(
            managed_share['id'])
        locations = [x['path'] for x in exports]

        LOG.debug('Step 12 - mount')
        self.mount_share(locations[0], remote_client)

        LOG.debug('Step 12 - verify data')
        ls_result = remote_client.exec_command("sudo ls -lA /mnt/")
        LOG.debug(ls_result)

        LOG.debug('Step 13 - unmount share')
        self.unmount_share(remote_client)

        LOG.debug('Step 14 - delete share')
        self.shares_admin_v2_client.delete_share(managed_share['id'])
        self.shares_admin_v2_client.wait_for_resource_deletion(
            share_id=managed_share['id'])

        LOG.debug('Step 15 - manage share, should fail')
        remanaged_share = self.shares_admin_v2_client.manage_share(
            share['host'],
            share['share_proto'],
            locations[0],
            share_type['id'])
        self.shares_admin_v2_client.wait_for_share_status(
            remanaged_share['id'], 'manage_error')

        self.shares_admin_v2_client.reset_state(remanaged_share['id'])

        LOG.debug('Step 16 - delete failed managed share')
        self.shares_admin_v2_client.delete_share(remanaged_share['id'])
        self.shares_admin_v2_client.wait_for_resource_deletion(
            share_id=remanaged_share['id'])


class ShareManageUnmanageNFS(ShareManageUnmanageBase):
    protocol = "nfs"

    def mount_share(self, location, remote_client, target_dir=None):
        target_dir = target_dir or "/mnt"
        remote_client.exec_command(
            "sudo mount -vt nfs \"%s\" %s" % (location, target_dir)
        )


class ShareManageUnmanageCIFS(ShareManageUnmanageBase):
    protocol = "cifs"

    def mount_share(self, location, remote_client, target_dir=None):
        location = location.replace("\\", "/")
        target_dir = target_dir or "/mnt"
        remote_client.exec_command(
            "sudo mount.cifs \"%s\" %s -o guest" % (location, target_dir)
        )


# NOTE(u_glide): this function is required to exclude ShareManageUnmanageBase
# from executed test cases.
# See: https://docs.python.org/3/library/unittest.html#load-tests-protocol
# for details.
def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareManageUnmanageBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
