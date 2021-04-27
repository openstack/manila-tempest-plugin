# Copyright 2016 Yogesh Kshirsagar
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

from tempest import config
from tempest.lib import decorators
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
_MIN_SUPPORTED_MICROVERSION = '2.11'


class ReplicationSnapshotTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationSnapshotTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            _MIN_SUPPORTED_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ReplicationSnapshotTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.replication_type = CONF.share.backend_replication_type
        cls.multitenancy_enabled = (
            utils.replication_with_multitenancy_support())

        if cls.replication_type not in constants.REPLICATION_TYPE_CHOICES:
            raise share_exceptions.ShareReplicationTypeException(
                replication_type=cls.replication_type
            )

        # create share type
        extra_specs = {
            "replication_type": cls.replication_type,
            "snapshot_support": True,
        }
        if CONF.share.capability_create_share_from_snapshot_support:
            extra_specs.update({
                "create_share_from_snapshot_support": True,
            })
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        cls.sn_id = None
        if cls.multitenancy_enabled:
            cls.share_network = cls.shares_v2_client.get_share_network(
                cls.shares_v2_client.share_network_id)['share_network']
            cls.sn_id = cls.share_network['id']

        cls.zones = cls.get_availability_zones_matching_share_type(
            cls.share_type, client=cls.admin_client)
        cls.share_zone = cls.zones[0]
        cls.replica_zone = cls.zones[-1]

    @decorators.idempotent_id('67fce02a-1d46-4186-8260-69e30b26195d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_snapshot_after_share_replica(self):
        """Test the snapshot for replicated share.

        Create replica first and then create a snapshot.
        Verify that the snapshot is properly created under replica by
        creating a share from that snapshot.
        """
        share = self.create_share(share_type_id=self.share_type_id,
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        original_replica = self.shares_v2_client.list_share_replicas(
            share["id"])['share_replicas'][0]

        share_replica = self.create_share_replica(share["id"],
                                                  self.replica_zone,
                                                  cleanup=False)
        self.addCleanup(self.delete_share_replica, original_replica['id'])
        waiters.wait_for_resource_status(
            self.shares_v2_client, share_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        snapshot = self.create_snapshot_wait_for_active(share["id"])
        self.promote_share_replica(share_replica['id'])
        self.delete_share_replica(original_replica['id'])

        snapshot = self.shares_v2_client.get_snapshot(
            snapshot['id'])['snapshot']
        self.assertEqual(constants.STATUS_AVAILABLE, snapshot['status'])

        if CONF.share.capability_create_share_from_snapshot_support:
            self.create_share(share_type_id=self.share_type_id,
                              snapshot_id=snapshot['id'],
                              share_network_id=self.sn_id)

    @decorators.idempotent_id('ced8920b-6e3a-4bb4-9b3d-86e54377fcb7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_snapshot_before_share_replica(self):
        """Test the snapshot for replicated share.

        Create snapshot before creating share replica for the same
        share.
        Verify snapshot by creating share from the snapshot.
        """
        share = self.create_share(share_type_id=self.share_type_id,
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        snapshot = self.create_snapshot_wait_for_active(share["id"])

        original_replica = self.shares_v2_client.list_share_replicas(
            share["id"])['share_replicas'][0]
        share_replica = self.create_share_replica(share["id"],
                                                  self.replica_zone,
                                                  cleanup=False)
        self.addCleanup(self.delete_share_replica, original_replica['id'])
        waiters.wait_for_resource_status(
            self.shares_v2_client, share_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        # Wait for snapshot1 to become available
        waiters.wait_for_resource_status(
            self.shares_v2_client, snapshot['id'], "available",
            resource_name='snapshot')

        self.promote_share_replica(share_replica['id'])
        self.delete_share_replica(original_replica['id'])

        snapshot = self.shares_v2_client.get_snapshot(
            snapshot['id'])['snapshot']
        self.assertEqual(constants.STATUS_AVAILABLE, snapshot['status'])

        if CONF.share.capability_create_share_from_snapshot_support:
            self.create_share(share_type_id=self.share_type_id,
                              snapshot_id=snapshot['id'],
                              share_network_id=self.sn_id)

    @decorators.idempotent_id('a5372844-69ad-40e1-bbf3-265eb66af123')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_snapshot_before_and_after_share_replica(self):
        """Test the snapshot for replicated share.

        Verify that snapshot can be created before and after share replica
        being created.
        Verify snapshots by creating share from the snapshots.
        """
        share = self.create_share(share_type_id=self.share_type_id,
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        snapshot1 = self.create_snapshot_wait_for_active(share["id"])

        original_replica = self.shares_v2_client.list_share_replicas(
            share["id"])['share_replicas'][0]

        share_replica = self.create_share_replica(share["id"],
                                                  self.replica_zone,
                                                  cleanup=False)
        self.addCleanup(self.delete_share_replica, original_replica['id'])
        waiters.wait_for_resource_status(
            self.shares_v2_client, share_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        snapshot2 = self.create_snapshot_wait_for_active(share["id"])

        # Wait for snapshot1 to become available
        waiters.wait_for_resource_status(
            self.shares_v2_client, snapshot1['id'], "available",
            resource_name='snapshot')

        self.promote_share_replica(share_replica['id'])
        # Remove the original active replica to ensure that snapshot is
        # still being created successfully.
        self.delete_share_replica(original_replica['id'])

        snapshot1 = self.shares_v2_client.get_snapshot(
            snapshot1['id'])['snapshot']
        self.assertEqual(constants.STATUS_AVAILABLE, snapshot1['status'])

        snapshot2 = self.shares_v2_client.get_snapshot(
            snapshot2['id'])['snapshot']
        self.assertEqual(constants.STATUS_AVAILABLE, snapshot2['status'])

        if CONF.share.capability_create_share_from_snapshot_support:
            self.create_share(share_type_id=self.share_type_id,
                              snapshot_id=snapshot1['id'],
                              share_network_id=self.sn_id)
            self.create_share(share_type_id=self.share_type_id,
                              snapshot_id=snapshot2['id'],
                              share_network_id=self.sn_id)

    @decorators.idempotent_id('b4cd376b-1eb8-4780-801a-64b0c3bee1e4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_delete_snapshot_after_adding_replica(self):
        """Verify the snapshot delete.

        Ensure that deleting the original snapshot also deletes the
        snapshot from replica.
        """

        share = self.create_share(share_type_id=self.share_type_id,
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        share_replica = self.create_share_replica(share["id"],
                                                  self.replica_zone)
        waiters.wait_for_resource_status(
            self.shares_v2_client, share_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')
        snapshot = self.create_snapshot_wait_for_active(share["id"])
        self.shares_v2_client.delete_snapshot(snapshot['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            snapshot_id=snapshot["id"])

    @decorators.idempotent_id('913056a7-d897-4a1b-a7be-b2b2cf5d9572')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_create_replica_from_snapshot_share(self):
        """Test replica for a share that was created from snapshot."""

        share = self.create_share(share_type_id=self.share_type_id,
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        orig_snapshot = self.create_snapshot_wait_for_active(share["id"])
        snap_share = self.create_share(share_type_id=self.share_type_id,
                                       snapshot_id=orig_snapshot['id'],
                                       share_network_id=self.sn_id)
        original_replica = self.shares_v2_client.list_share_replicas(
            snap_share["id"])['share_replicas'][0]
        share_replica = self.create_share_replica(snap_share["id"],
                                                  self.replica_zone,
                                                  cleanup=False)
        self.addCleanup(self.delete_share_replica, original_replica['id'])
        waiters.wait_for_resource_status(
            self.shares_v2_client, share_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')
        self.promote_share_replica(share_replica['id'])
        # Delete the demoted replica so promoted replica can be cleaned
        # during the cleanup
        self.delete_share_replica(original_replica['id'])
