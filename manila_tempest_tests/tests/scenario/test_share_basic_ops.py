# Copyright 2015 Deutsche Telekom AG
# All Rights Reserved.
#
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

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.scenario import manager_share as manager
from manila_tempest_tests import utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


@ddt.ddt
class ShareBasicOpsBase(manager.ShareScenarioTest):

    """This smoke test case follows this basic set of operations:

     * Create share network
     * Create share
     * Launch an instance
     * Allow access
     * Perform ssh to instance
     * Mount share
     * Terminate the instance
    """

    def _ping_host_from_export_location(self, export, remote_client):
        ip, version = self.get_ip_and_version_from_export_location(export)
        if version == 6:
            remote_client.exec_command("ping6 -c 5 %s" % ip)
        else:
            remote_client.exec_command("ping -c 5 %s" % ip)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_mount_share_one_vm(self):
        instance = self.boot_instance(wait_until="BUILD")
        self.create_share()
        locations = self.get_user_export_locations(self.share)
        instance = self.wait_for_active_instance(instance["id"])
        remote_client = self.init_remote_client(instance)
        self.allow_access(instance=instance, remote_client=remote_client,
                          locations=locations)

        for location in locations:
            self.mount_share(location, remote_client)
            self.unmount_share(remote_client)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_write_with_ro_access(self):
        '''Test if an instance with ro access can write on the share.'''
        test_data = "Some test data to write"

        instance = self.boot_instance(wait_until="BUILD")
        self.create_share()
        location = self.get_user_export_locations(self.share)[0]
        instance = self.wait_for_active_instance(instance["id"])

        remote_client_inst = self.init_remote_client(instance)

        # First, check if write works RW access.
        acc_rule_id = self.allow_access(
            instance=instance, remote_client=remote_client_inst,
            locations=location)['id']

        self.mount_share(location, remote_client_inst)
        self.write_data_to_mounted_share(test_data, remote_client_inst)
        self.deny_access(self.share['id'], acc_rule_id)

        self.allow_access(instance=instance, remote_client=remote_client_inst,
                          locations=location, access_level='ro')

        self.addCleanup(self.unmount_share, remote_client_inst)

        # Test if write with RO access fails.
        self.assertRaises(exceptions.SSHExecCommandFailed,
                          self.write_data_to_mounted_share,
                          test_data, remote_client_inst)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_read_write_two_vms(self):
        """Boots two vms and writes/reads data on it."""
        test_data = "Some test data to write"

        # Boot two VMs and create share
        instance1 = self.boot_instance(wait_until="BUILD")
        instance2 = self.boot_instance(wait_until="BUILD")
        self.create_share()
        location = self.get_user_export_locations(self.share)[0]
        instance1 = self.wait_for_active_instance(instance1["id"])
        instance2 = self.wait_for_active_instance(instance2["id"])

        # Write data to first VM
        remote_client_inst1 = self.init_remote_client(instance1)
        self.allow_access(instance=instance1,
                          remote_client=remote_client_inst1,
                          locations=location)

        self.mount_share(location, remote_client_inst1)
        self.addCleanup(self.unmount_share,
                        remote_client_inst1)
        self.write_data_to_mounted_share(test_data, remote_client_inst1)

        # Read from second VM
        remote_client_inst2 = self.init_remote_client(instance2)
        if not CONF.share.override_ip_for_nfs_access or self.ipv6_enabled:
            self.allow_access(instance=instance2,
                              remote_client=remote_client_inst2,
                              locations=location)

        self.mount_share(location, remote_client_inst2)
        self.addCleanup(self.unmount_share,
                        remote_client_inst2)
        data = self.read_data_from_mounted_share(remote_client_inst2)
        self.assertEqual(test_data, data)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @base.skip_if_microversion_lt("2.29")
    @testtools.skipUnless(CONF.share.run_host_assisted_migration_tests or
                          CONF.share.run_driver_assisted_migration_tests,
                          "Share migration tests are disabled.")
    @ddt.data(True, False)
    def test_migration_files(self, force_host_assisted):

        if (force_host_assisted and
                not CONF.share.run_host_assisted_migration_tests):
            raise self.skipException("Host-assisted migration tests are "
                                     "disabled.")
        elif (not force_host_assisted and
              not CONF.share.run_driver_assisted_migration_tests):
            raise self.skipException("Driver-assisted migration tests are "
                                     "disabled.")

        if self.protocol != "nfs":
            raise self.skipException("Only NFS protocol supported "
                                     "at this moment.")

        if self.ipv6_enabled:
            raise self.skipException("Share Migration using IPv6 is not "
                                     "supported at this moment.")

        pools = self.shares_admin_v2_client.list_pools(detail=True)['pools']

        if len(pools) < 2:
            raise self.skipException("At least two different pool entries are "
                                     "needed to run share migration tests.")

        instance = self.boot_instance(wait_until="BUILD")
        self.create_share()
        exports = self.get_user_export_locations(self.share)
        instance = self.wait_for_active_instance(instance["id"])
        self.share = self.shares_admin_v2_client.get_share(self.share['id'])

        default_type = self.shares_v2_client.list_share_types(
            default=True)['share_type']

        dest_pool = utils.choose_matching_backend(
            self.share, pools, default_type)

        self.assertIsNotNone(dest_pool)
        self.assertIsNotNone(dest_pool.get('name'))

        dest_pool = dest_pool['name']

        remote_client = self.init_remote_client(instance)
        self.provide_access_to_auxiliary_instance(instance)

        self.mount_share(exports[0], remote_client)

        remote_client.exec_command("sudo mkdir -p /mnt/f1")
        remote_client.exec_command("sudo mkdir -p /mnt/f2")
        remote_client.exec_command("sudo mkdir -p /mnt/f3")
        remote_client.exec_command("sudo mkdir -p /mnt/f4")
        remote_client.exec_command("sudo mkdir -p /mnt/f1/ff1")
        remote_client.exec_command("sleep 1")
        remote_client.exec_command(
            "sudo dd if=/dev/zero of=/mnt/f1/1m1.bin bs=1M count=1")
        remote_client.exec_command(
            "sudo dd if=/dev/zero of=/mnt/f2/1m2.bin bs=1M count=1")
        remote_client.exec_command(
            "sudo dd if=/dev/zero of=/mnt/f3/1m3.bin bs=1M count=1")
        remote_client.exec_command(
            "sudo dd if=/dev/zero of=/mnt/f4/1m4.bin bs=1M count=1")
        remote_client.exec_command(
            "sudo dd if=/dev/zero of=/mnt/f1/ff1/1m5.bin bs=1M count=1")
        remote_client.exec_command("sudo chmod -R 555 /mnt/f3")
        remote_client.exec_command("sudo chmod -R 777 /mnt/f4")

        task_state = (constants.TASK_STATE_DATA_COPYING_COMPLETED
                      if force_host_assisted
                      else constants.TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE)

        self.share = self.migrate_share(
            self.share['id'], dest_pool, task_state, force_host_assisted)

        if force_host_assisted:
            self.assertRaises(
                exceptions.SSHExecCommandFailed,
                remote_client.exec_command,
                "dd if=/dev/zero of=/mnt/f1/1m6.bin bs=1M count=1")

        self.unmount_share(remote_client)

        self.share = self.migration_complete(self.share['id'], dest_pool)

        new_exports = self.get_user_export_locations(
            self.share, error_on_invalid_ip_version=True)

        self.assertEqual(dest_pool, self.share['host'])
        self.assertEqual(constants.TASK_STATE_MIGRATION_SUCCESS,
                         self.share['task_state'])

        self.mount_share(new_exports[0], remote_client)

        output = remote_client.exec_command("ls -lRA --ignore=lost+found /mnt")

        self.unmount_share(remote_client)

        self.assertIn('1m1.bin', output)
        self.assertIn('1m2.bin', output)
        self.assertIn('1m3.bin', output)
        self.assertIn('1m4.bin', output)
        self.assertIn('1m5.bin', output)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_write_data_to_share_created_from_snapshot(self):
        # 1 - Create UVM, ok, created
        instance = self.boot_instance(wait_until="BUILD")

        # 2 - Create share S1, ok, created
        parent_share = self.create_share()
        instance = self.wait_for_active_instance(instance["id"])
        self.addCleanup(self.servers_client.delete_server, instance['id'])

        # 3 - SSH to UVM, ok, connected
        remote_client = self.init_remote_client(instance)

        # 4 - Provide RW access to S1, ok, provided
        self.provide_access_to_auxiliary_instance(instance, parent_share)

        # 5 - Try mount S1 to UVM, ok, mounted
        user_export_location = self.get_user_export_locations(parent_share)[0]
        parent_share_dir = "/mnt/parent"
        remote_client.exec_command("sudo mkdir -p %s" % parent_share_dir)

        self.mount_share(user_export_location, remote_client, parent_share_dir)
        self.addCleanup(self.unmount_share, remote_client, parent_share_dir)

        # 6 - Create "file1", ok, created
        remote_client.exec_command("sudo touch %s/file1" % parent_share_dir)

        # 7 - Create snapshot SS1 from S1, ok, created
        snapshot = self._create_snapshot(parent_share['id'])

        # 8 - Create "file2" in share S1 - ok, created. We expect that
        # snapshot will not contain any data created after snapshot creation.
        remote_client.exec_command("sudo touch %s/file2" % parent_share_dir)

        # 9 - Create share S2 from SS1, ok, created
        child_share = self.create_share(snapshot_id=snapshot["id"])

        # 10 - Try mount S2 - fail, access denied. We test that child share
        #      did not get access rules from parent share.
        user_export_location = self.get_user_export_locations(child_share)[0]
        child_share_dir = "/mnt/child"
        remote_client.exec_command("sudo mkdir -p %s" % child_share_dir)

        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            self.mount_share,
            user_export_location, remote_client, child_share_dir,
        )

        # 11 - Provide RW access to S2, ok, provided
        self.provide_access_to_auxiliary_instance(instance, child_share)

        # 12 - Try mount S2, ok, mounted
        self.mount_share(user_export_location, remote_client, child_share_dir)
        self.addCleanup(self.unmount_share, remote_client, child_share_dir)

        # 13 - List files on S2, only "file1" exists
        output = remote_client.exec_command(
            "sudo ls -lRA %s" % child_share_dir)
        self.assertIn('file1', output)
        self.assertNotIn('file2', output)

        # 14 - Create file3 on S2, ok, file created
        remote_client.exec_command("sudo touch %s/file3" % child_share_dir)

        # 15 - List files on S1, two files exist - "file1" and "file2"
        output = remote_client.exec_command(
            "sudo ls -lRA %s" % parent_share_dir)
        self.assertIn('file1', output)
        self.assertIn('file2', output)
        self.assertNotIn('file3', output)

        # 16 - List files on S2, two files exist - "file1" and "file3"
        output = remote_client.exec_command(
            "sudo ls -lRA %s" % child_share_dir)
        self.assertIn('file1', output)
        self.assertNotIn('file2', output)
        self.assertIn('file3', output)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @base.skip_if_microversion_lt("2.32")
    @testtools.skipUnless(CONF.share.run_mount_snapshot_tests,
                          'Mountable snapshots tests are disabled.')
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_read_mountable_snapshot(self):
        # 1 - Create UVM, ok, created
        instance = self.boot_instance(wait_until="BUILD")

        # 2 - Create share S1, ok, created
        parent_share = self.create_share()
        instance = self.wait_for_active_instance(instance["id"])
        self.addCleanup(self.servers_client.delete_server, instance['id'])

        # 3 - SSH to UVM, ok, connected
        remote_client = self.init_remote_client(instance)

        # 4 - Provide RW access to S1, ok, provided
        self.provide_access_to_auxiliary_instance(instance, parent_share)

        # 5 - Try mount S1 to UVM, ok, mounted
        user_export_location = self.get_user_export_locations(parent_share)[0]
        parent_share_dir = "/mnt/parent"
        snapshot_dir = "/mnt/snapshot_dir"
        remote_client.exec_command("sudo mkdir -p %s" % parent_share_dir)
        remote_client.exec_command("sudo mkdir -p %s" % snapshot_dir)

        self.mount_share(user_export_location, remote_client, parent_share_dir)
        self.addCleanup(self.unmount_share, remote_client, parent_share_dir)

        # 6 - Create "file1", ok, created
        remote_client.exec_command("sudo touch %s/file1" % parent_share_dir)

        # 7 - Create snapshot SS1 from S1, ok, created
        snapshot = self._create_snapshot(parent_share['id'])

        # 8 - Create "file2" in share S1 - ok, created. We expect that
        # snapshot will not contain any data created after snapshot creation.
        remote_client.exec_command("sudo touch %s/file2" % parent_share_dir)

        # 9 - Allow access to SS1
        self.provide_access_to_auxiliary_instance(instance, snapshot=snapshot)

        # 10 - Mount SS1
        user_export_location = self.get_user_export_locations(
            snapshot=snapshot)[0]
        self.mount_share(user_export_location, remote_client, snapshot_dir)
        self.addCleanup(self.unmount_share, remote_client, snapshot_dir)

        # 11 - List files on SS1, only "file1" exists
        # NOTE(lseki): using ls without recursion to avoid permission denied
        #              error while listing lost+found directory on LVM volumes
        output = remote_client.exec_command("sudo ls -lA %s" % snapshot_dir)
        self.assertIn('file1', output)
        self.assertNotIn('file2', output)

        # 12 - Try to create a file on SS1, should fail
        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            remote_client.exec_command,
            "sudo touch %s/file3" % snapshot_dir)


class TestShareBasicOpsNFS(ShareBasicOpsBase):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(TestShareBasicOpsNFS, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_auxiliary_instance(
            instance=kwargs['instance'], access_level=access_level)

    def mount_share(self, location, remote_client, target_dir=None):

        self._ping_host_from_export_location(location, remote_client)

        target_dir = target_dir or "/mnt"
        remote_client.exec_command(
            "sudo mount -vt nfs \"%s\" %s" % (location, target_dir))


class TestShareBasicOpsCIFS(ShareBasicOpsBase):
    protocol = "cifs"

    @classmethod
    def skip_checks(cls):
        super(TestShareBasicOpsCIFS, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_ip_rules_for_protocols:
            message = ("%s tests for access rules other than IP are disabled" %
                       cls.protocol)
            raise cls.skipException(message)

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_auxiliary_instance(
            instance=kwargs['instance'], access_level=access_level)

    def mount_share(self, location, remote_client, target_dir=None):

        self._ping_host_from_export_location(location, remote_client)

        location = location.replace("\\", "/")
        target_dir = target_dir or "/mnt"
        remote_client.exec_command(
            "sudo mount.cifs \"%s\" %s -o guest" % (location, target_dir)
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_write_with_ro_access(self):
        msg = ("Skipped for CIFS protocol because RO access is not "
               "supported for shares by IP.")
        raise self.skipException(msg)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_read_mountable_snapshot(self):
        msg = "Skipped for CIFS protocol because of bug/1649573"
        raise self.skipException(msg)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_write_data_to_share_created_from_snapshot(self):
        msg = "Skipped for CIFS protocol because of bug/1649573"
        raise self.skipException(msg)


class TestShareBasicOpsCEPHFS(ShareBasicOpsBase, manager.BaseShareCEPHFSTest):
    protocol = "cephfs"

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_mount_share_one_vm_with_ceph_fuse_client(self):
        self.mount_client = 'fuse'
        super(TestShareBasicOpsCEPHFS, self).test_mount_share_one_vm()

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_write_with_ro_access_with_ceph_fuse_client(self):
        self.mount_client = 'fuse'
        super(TestShareBasicOpsCEPHFS, self).test_write_with_ro_access()

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_read_write_two_vms_with_ceph_fuse_client(self):
        self.mount_client = 'fuse'
        super(TestShareBasicOpsCEPHFS, self).test_read_write_two_vms()


class TestShareBasicOpsNFSIPv6(TestShareBasicOpsNFS):
    ip_version = 6


# NOTE(u_glide): this function is required to exclude ShareBasicOpsBase from
# executed test cases.
# See: https://docs.python.org/3/library/unittest.html#load-tests-protocol
# for details.
def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareBasicOpsBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
