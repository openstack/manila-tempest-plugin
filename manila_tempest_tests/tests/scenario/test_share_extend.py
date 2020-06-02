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
import six

from oslo_log import log as logging
from oslo_utils import units
from tempest import config
from tempest.lib import exceptions
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.scenario import manager_share as manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


@ddt.ddt
class ShareExtendBase(manager.ShareScenarioTest):

    """This test case uses the following flow:

     * Launch an instance
     * Create share (1GB)
     * Configure RW access to the share
     * Perform ssh to instance
     * Mount share
     * Write data in share
     * Extend share (2GB)
     * Write more data in share
     * Unmount share
     * Delete share
     * Terminate the instance
    """

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_extend_and_write(self):
        default_share_size = CONF.share.share_size

        LOG.debug('Step 1 - create instance')
        instance = self.boot_instance(wait_until="BUILD")

        LOG.debug('Step 2 - create share of size {} Gb'
                  .format(default_share_size))
        share = self.create_share(size=default_share_size)

        LOG.debug('Step 3 - wait for active instance')
        instance = self.wait_for_active_instance(instance["id"])
        remote_client = self.init_remote_client(instance)

        LOG.debug('Step 4 - grant access')
        location = self.get_share_export_location_for_mount(share)
        self.allow_access(instance=instance, remote_client=remote_client,
                          locations=location)

        LOG.debug('Step 5 - mount')
        self.mount_share(location, remote_client)

        total_blocks = (units.Ki * default_share_size) / 64
        three_quarter_blocks = (total_blocks / 4) * 3
        LOG.debug('Step 6 - writing {} * 64MB blocks'
                  .format(three_quarter_blocks))
        self.write_data_to_mounted_share_using_dd(remote_client,
                                                  '/mnt/t1', '64M',
                                                  three_quarter_blocks,
                                                  '/dev/urandom')
        ls_result = remote_client.exec_command("sudo ls -lAh /mnt/")
        LOG.debug(ls_result)

        over_one_quarter_blocks = total_blocks - three_quarter_blocks + 5
        LOG.debug('Step 6b - Write more data, should fail')
        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            self.write_data_to_mounted_share_using_dd,
            remote_client, '/mnt/t2', '64M', over_one_quarter_blocks,
            '/dev/urandom')
        ls_result = remote_client.exec_command("sudo ls -lAh /mnt/")
        LOG.debug(ls_result)

        LOG.debug('Step 7 - extend and wait')
        extended_share_size = default_share_size + 1
        self.shares_v2_client.extend_share(share["id"],
                                           new_size=extended_share_size)
        self.shares_v2_client.wait_for_share_status(share["id"],
                                                    constants.STATUS_AVAILABLE)
        share = self.shares_v2_client.get_share(share["id"])
        self.assertEqual(extended_share_size, int(share["size"]))

        LOG.debug('Step 8 - writing more data, should succeed')
        self.write_data_with_remount(location, remote_client, '/mnt/t3',
                                     '64M', over_one_quarter_blocks)
        ls_result = remote_client.exec_command("sudo ls -lAh /mnt/")
        LOG.debug(ls_result)

        LOG.debug('Step 9 - unmount')
        self.unmount_share(remote_client)

    def write_data_with_remount(self, mount_location,
                                remote_client,
                                output_file,
                                block_size,
                                block_count):
        """Writes data to mounted share using dd command

        Tries remounting once if encountering a stale file handle

        :param mount_location: Mount point for remounting if needed
        :param remote_client: An SSH client connection to the Nova instance
        :param block_size: The size of an individual block in bytes
        :param block_count: The number of blocks to write
        :param output_file: Path to the file to be written
        """

        try:
            self.write_data_to_mounted_share_using_dd(remote_client,
                                                      output_file,
                                                      block_size,
                                                      block_count,
                                                      '/dev/urandom')
        except exceptions.SSHExecCommandFailed as e:
            if 'stale file handle' in six.text_type(e).lower():
                LOG.warning("Client was disconnected during extend process")
                self.unmount_share(remote_client)
                self.mount_share(mount_location, remote_client)
                self.write_data_to_mounted_share_using_dd(remote_client,
                                                          output_file,
                                                          block_size,
                                                          block_count,
                                                          '/dev/urandom')
            else:
                raise


class TestShareExtendNFS(ShareExtendBase):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareExtendBase, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_auxiliary_instance(
            instance=kwargs['instance'], access_level=access_level)

    def mount_share(self, location, remote_client, target_dir=None):
        target_dir = target_dir or "/mnt"
        remote_client.exec_command(
            "sudo mount -vt nfs \"%s\" %s" % (location, target_dir)
        )


class TestShareExtendCIFS(ShareExtendBase):
    protocol = "cifs"

    @classmethod
    def skip_checks(cls):
        super(ShareExtendBase, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_auxiliary_instance(
            instance=kwargs['instance'], access_level=access_level)

    def mount_share(self, location, remote_client, target_dir=None):
        location = location.replace("\\", "/")
        target_dir = target_dir or "/mnt"
        remote_client.exec_command(
            "sudo mount.cifs \"%s\" %s -o guest" % (location, target_dir)
        )


class TestShareExtendCEPHFS(ShareExtendBase, manager.BaseShareCEPHFSTest):
    protocol = "cephfs"

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_extend_and_write_with_ceph_fuse_client(self):
        self.mount_client = 'fuse'
        super(TestShareExtendCEPHFS, self).test_create_extend_and_write()


# NOTE(u_glide): this function is required to exclude ShareExtendBase
# from executed test cases.
# See: https://docs.python.org/3/library/unittest.html#load-tests-protocol
# for details.
def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareExtendBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
