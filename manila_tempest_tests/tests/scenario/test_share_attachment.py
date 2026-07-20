# Copyright 2026 Red Hat Inc.
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

from oslo_log import log as logging
from tempest.common import waiters as tempest_waiters
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.scenario import manager_share as manager


CONF = config.CONF
LOG = logging.getLogger(__name__)


class ShareAttachmentBase(manager.ShareScenarioTest):
    """Base class for share attachment scenario tests using virtiofs

    These tests validate Manila share attachment via Nova's virtiofs
    integration introduced in the Epoxy release.
    """

    protocol = "nfs"
    credentials = ('admin', 'primary', 'alt')
    # Minimum compute API microversion required for share attachments
    compute_min_microversion = '2.97'

    @classmethod
    def setup_clients(cls):
        super(ShareAttachmentBase, cls).setup_clients()
        # Set up clients for non-admin (alt) user
        cls.shares_v2_client_alt = cls.os_alt.share_v2.SharesV2Client()
        # Set compute API microversion 2.97 for share attachment support
        cls.servers_client.api_microversion = '2.97'

    @classmethod
    def skip_checks(cls):
        super(ShareAttachmentBase, cls).skip_checks()
        if not CONF.compute_feature_enabled.share_attachments:
            raise cls.skipException("Share attachment tests are disabled")

    def attach_share_to_running_server(self, server_id, share_id, tag,
                                       cleanup=True):
        """Attach a share to a running server via virtiofs

        This method handles the full workflow: stop server, attach share,
        wait for access rules to become active, start server, and wait for
        attachment to become active.

        :param server_id: ID of the server/instance
        :param share_id: ID of the Manila share
        :param tag: Tag for the share attachment
        :param cleanup: Whether to register cleanup handler
        :returns: Share attachment and updated server instance
        """
        # Power down server
        self.servers_client.stop_server(server_id)
        tempest_waiters.wait_for_server_status(
            self.servers_client, server_id, constants.INSTANCE_STATUS_SHUTOFF)

        # Attach share
        attachment = self.attach_share_to_server(
            server_id, share_id, tag=tag, cleanup=cleanup)
        self.wait_for_share_attachment_status(
            server_id, share_id, constants.SERVER_ATTACHMENT_STATUS_INACTIVE)

        # Wait for access rules to become active before powering on
        # Nova needs the access rule active to mount the NFS share
        waiters.wait_for_resource_status(
            self.shares_v2_client, share_id, constants.RULE_STATE_ACTIVE,
            status_attr='access_rules_status')

        # Power up server (Nova will now mount the share)
        self.servers_client.start_server(server_id)
        instance = self.wait_for_active_instance(server_id)
        self.wait_for_share_attachment_status(
            server_id, share_id, constants.SERVER_ATTACHMENT_STATUS_ACTIVE)

        return attachment, instance

    def detach_share_from_running_server(self, server_id, share_id,
                                         remote_client=None):
        """Detach a share from a running server via virtiofs

        This method handles the full workflow: unmount share, stop server,
        detach share, and start server.

        :param server_id: ID of the server/instance
        :param share_id: ID of the Manila share
        :param remote_client: Optional SSH client to unmount before detaching
        :returns: Updated server instance
        """
        # Unmount if remote client provided
        if remote_client:
            self.unmount_share_via_virtiofs(remote_client)

        # Power down server
        self.servers_client.stop_server(server_id)
        tempest_waiters.wait_for_server_status(
            self.servers_client, server_id, constants.INSTANCE_STATUS_SHUTOFF)

        # Detach share and wait for completion
        self.detach_share_from_server(server_id, share_id)
        self.wait_for_share_detachment(server_id, share_id)

        # Power up server
        self.servers_client.start_server(server_id)
        instance = self.wait_for_active_instance(server_id)

        return instance

    def verify_share_and_access_locks_exist(self, share_id):
        """Verify resource locks exist on share and its access rules

        Also verifies that non-admin users see redacted access_to and
        access_key fields.

        :param share_id: ID of the Manila share
        """
        # Verify share locks exist
        share_locks = self.shares_admin_v2_client.list_resource_locks(
            filters={'resource_id': share_id, 'all_tenants': 1}
        )['resource_locks']
        self.assertNotEqual(len(share_locks), 0)

        # Get access rules and verify their locks
        access_rules = self.shares_v2_client.list_access_rules(
            share_id)['access_list']
        if access_rules:
            access_rule_id = access_rules[0]['id']
            access_locks = self.shares_admin_v2_client.list_resource_locks(
                filters={'resource_id': access_rule_id, 'all_tenants': 1}
            )['resource_locks']
            self.assertNotEqual(len(access_locks), 0)

            # Verify field redaction for non-admin
            access_rule = self.shares_v2_client.get_access_rule(
                access_rule_id)['access']
            self.assertEqual('******', access_rule['access_to'])
            self.assertEqual('******', access_rule['access_key'])

    def verify_share_and_access_locks_removed(self, share_id):
        """Verify resource locks are removed from share and access rules

        :param share_id: ID of the Manila share
        """
        # Verify share locks removed
        share_locks = self.shares_admin_v2_client.list_resource_locks(
            filters={'resource_id': share_id, 'all_tenants': 1}
        )['resource_locks']
        self.assertEqual(len(share_locks), 0)

        # Verify access rule locks removed
        access_rules = self.shares_v2_client.list_access_rules(
            share_id)['access_list']
        if access_rules:
            access_rule_id = access_rules[0]['id']
            access_locks = self.shares_admin_v2_client.list_resource_locks(
                filters={'resource_id': access_rule_id, 'all_tenants': 1}
            )['resource_locks']
            self.assertEqual(len(access_locks), 0)

    def verify_locked_resource_deletion_forbidden(self, share_id):
        """Verify deletion is forbidden for locked share and access rules

        Tests that non-admin and admin users cannot delete locked resources.

        :param share_id: ID of the Manila share
        """
        # Verify non-admin cannot delete locked share
        self.assertRaises(
            exceptions.Forbidden,
            self.shares_v2_client.delete_share,
            share_id
        )

        # Get access rules
        access_rules = self.shares_v2_client.list_access_rules(
            share_id)['access_list']

        if access_rules:
            access_rule_id = access_rules[0]['id']

            # Verify non-admin cannot delete locked access rule
            self.assertRaises(
                exceptions.Forbidden,
                self.shares_v2_client.delete_access_rule,
                share_id,
                access_rule_id
            )

            # Verify admin cannot delete locked access rule without unrestrict
            self.assertRaises(
                exceptions.Forbidden,
                self.shares_admin_v2_client.delete_access_rule,
                share_id,
                access_rule_id
            )

    @decorators.idempotent_id('a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_mount_share_via_virtiofs(self):
        """Scenario 13: Mount Share via VirtioFS

        This test validates Manila share attachment via Nova's virtiofs
        integration, including resource locks and access restrictions.

        26 Steps validating:
        - Share attachment lifecycle
        - Resource locks on shares and access rules during attachment
        - Non-admin user restrictions while share is attached
        - File operations through virtiofs mount
        - Proper cleanup after detachment
        """
        test_data = "Test data for virtiofs scenario"
        test_file = "/mnt/testfile.txt"
        share_tag = "share-virtiofs"

        # Step 1: Create user VM (UVM) and add a cleanup
        instance = self.boot_instance(wait_until="ACTIVE")
        self.addCleanup(self.servers_client.delete_server, instance['id'])

        # Step 2: Create share (S)
        share = self.create_share()

        waiters.wait_for_resource_status(
            self.shares_v2_client, share['id'], constants.STATUS_AVAILABLE)

        # Step 3: SSH to UVM
        remote_client = self.init_remote_client(instance)

        # Step 4: Attempt mounting S to UVM - should fail (no attachment)
        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            self.mount_share_via_virtiofs,
            remote_client, share_tag
        )

        # Steps 5-7: Power down, attach, power up
        attachment, instance = self.attach_share_to_running_server(
            instance['id'], share['id'], share_tag, cleanup=True)

        # Step 8: List UVM's attachments
        attachments = self.list_server_share_attachments(instance['id'])
        share_ids = [att['share_id'] for att in attachments]
        self.assertIn(share['id'], share_ids)

        # Steps 9-11: Verify resource locks and field redaction
        self.verify_share_and_access_locks_exist(share['id'])

        # Step 12 and 13: SSH and Mount S to UVM
        self.mount_share_via_virtiofs(remote_client, share_tag)

        # Step 14: Write files to S
        self.write_data_to_mounted_share(test_data, remote_client, test_file)

        # Step 15: Read files from S
        read_data = self.read_data_from_mounted_share(
            remote_client, test_file)
        self.assertEqual(test_data, read_data)

        # Step 16: Delete files on S
        remote_client.exec_command("sudo rm -f %s" % test_file)
        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            remote_client.exec_command,
            "sudo cat %s" % test_file
        )

        # Steps 17-19: Verify locked resource deletion is forbidden
        self.verify_locked_resource_deletion_forbidden(share['id'])

        # Steps 20-22: Unmount, power down, detach, power up
        instance = self.detach_share_from_running_server(
            instance['id'], share['id'], remote_client=remote_client)

        # Steps 23-24: Verify resource locks are removed
        self.verify_share_and_access_locks_removed(share['id'])

    @decorators.idempotent_id('b2c3d4e5-f6a7-8901-b2c3-d4e5f6a78901')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_multiple_shares_via_virtiofs(self):
        """Scenario 14: Multiple Shares via VirtioFS

        This test validates concurrent access to the same Manila share by
        multiple virtual machines using virtiofs attachments and confirms
        that data modifications remain visible across all connected clients.

        Steps validating:
        - Multiple VMs attaching to the same share
        - Concurrent file operations across VMs
        - Sequential attachment and detachment workflow
        - Cross-VM data visibility
        - Resource locks on shares and access rules during attachment
        - Non-admin user restrictions while share is attached
        - Proper cleanup after detachment
        """
        test_data_vm1 = "Data written from VM1"
        test_data_vm2 = "Data written from VM2"
        test_file_vm1 = "/mnt/file_from_vm1.txt"
        test_file_vm2 = "/mnt/file_from_vm2.txt"
        share_tag_1 = "share-vm1"
        share_tag_2 = "share-vm2"

        # Step 1: Create user VM (UVM1)
        instance1 = self.boot_instance(
            wait_until=constants.INSTANCE_STATUS_ACTIVE)
        self.addCleanup(self.servers_client.delete_server, instance1['id'])

        # Step 2: Create user VM (UVM2)
        instance2 = self.boot_instance(
            wait_until=constants.INSTANCE_STATUS_ACTIVE)
        self.addCleanup(self.servers_client.delete_server, instance2['id'])

        # Step 3: Create share (S)
        share = self.create_share()

        # Steps 4-6: Power down, attach, power up UVM1
        attachment1, instance1 = self.attach_share_to_running_server(
            instance1['id'], share['id'], share_tag_1, cleanup=True)

        # Step 7: List UVM1's attachments
        attachments1 = self.list_server_share_attachments(instance1['id'])
        share_ids = [att['share_id'] for att in attachments1]
        self.assertIn(share['id'], share_ids)

        # Step 8: SSH to UVM1
        remote_client_vm1 = self.init_remote_client(instance1)

        # Step 9: Mount S to UVM1
        self.mount_share_via_virtiofs(remote_client_vm1, share_tag_1)

        # Step 10: Write files to S
        self.write_data_to_mounted_share(
            test_data_vm1, remote_client_vm1, test_file_vm1)

        # Step 11: SSH to UVM2
        remote_client_vm2 = self.init_remote_client(instance2)

        # Step 12: Mount S from UVM2 - should fail (not attached)
        self.assertRaises(
            exceptions.SSHExecCommandFailed,
            self.mount_share_via_virtiofs,
            remote_client_vm2, share_tag_2
        )

        # Steps 13-15: Power down, attach, power up UVM2
        attachment2, instance2 = self.attach_share_to_running_server(
            instance2['id'], share['id'], share_tag_2, cleanup=True)

        # Step 16: List UVM2's attachments
        attachments2 = self.list_server_share_attachments(instance2['id'])
        share_ids = [att['share_id'] for att in attachments2]
        self.assertIn(share['id'], share_ids)

        # Steps 17a-17c: Verify resource locks and field redaction
        self.verify_share_and_access_locks_exist(share['id'])

        # Steps 17d-17f: Verify locked resource deletion is forbidden
        self.verify_locked_resource_deletion_forbidden(share['id'])

        # Step 18: Write files to S on UVM2
        # First mount the share
        self.mount_share_via_virtiofs(remote_client_vm2, share_tag_2)

        # Write data from VM2
        self.write_data_to_mounted_share(
            test_data_vm2, remote_client_vm2, test_file_vm2)

        # Verify data written from VM1 is visible on VM2
        read_data_vm2 = self.read_data_from_mounted_share(
            remote_client_vm2, test_file_vm1)
        self.assertEqual(test_data_vm1, read_data_vm2)

        # Steps 19-21: Unmount, power down, detach, power up UVM1
        instance1 = self.detach_share_from_running_server(
            instance1['id'], share['id'], remote_client=remote_client_vm1)

        # Step 22: Write files to S on UVM2 (verify still accessible)
        test_file_vm2_2 = "/mnt/file_from_vm2_second.txt"
        self.write_data_to_mounted_share(
            "Second write from VM2", remote_client_vm2, test_file_vm2_2)

        # Steps 23-25: Unmount, power down, detach, power up UVM2
        instance2 = self.detach_share_from_running_server(
            instance2['id'], share['id'], remote_client=remote_client_vm2)

        # Steps 25a-25b: Verify resource locks are removed
        self.verify_share_and_access_locks_removed(share['id'])


class TestShareAttachmentNFS(ShareAttachmentBase):
    """Test share attachment operations with NFS protocol"""
    protocol = "nfs"


class TestShareAttachmentCEPHFS(ShareAttachmentBase):
    """Test share attachment operations with CephFS protocol"""
    protocol = "cephfs"


def load_tests(loader, tests, _):
    """Exclude base test class from test execution"""
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareAttachmentBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
