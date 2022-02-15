# Copyright 2015 Yogesh Kshirsagar
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
from tempest import config
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
_MIN_SUPPORTED_MICROVERSION = '2.11'
LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class ReplicationAdminTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationAdminTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

        utils.check_skip_if_microversion_not_supported(
            _MIN_SUPPORTED_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ReplicationAdminTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.replication_type = CONF.share.backend_replication_type
        cls.multitenancy_enabled = (
            utils.replication_with_multitenancy_support())

        if cls.replication_type not in constants.REPLICATION_TYPE_CHOICES:
            raise share_exceptions.ShareReplicationTypeException(
                replication_type=cls.replication_type
            )

        extra_specs = {"replication_type": cls.replication_type}
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

        # Create share with above share_type
        cls.share = cls.create_share(share_type_id=cls.share_type_id,
                                     availability_zone=cls.share_zone,
                                     share_network_id=cls.sn_id,
                                     client=cls.admin_client)
        cls.replica = cls.admin_client.list_share_replicas(
            share_id=cls.share['id'])['share_replicas'][0]

    @staticmethod
    def _filter_share_replica_list(replica_list, r_state):
        # Iterate through replica list to filter based on replica_state
        return [replica['id'] for replica in replica_list
                if replica['replica_state'] == r_state]

    @decorators.unstable_test(bug='1631314')
    @decorators.idempotent_id('0213cdfd-6a0f-4f24-a154-69796888a64a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_REPLICATION_VERSION,
                            constants.SHARE_REPLICA_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_promote_out_of_sync_share_replica(self, version):
        """Test promote 'out_of_sync' share replica to active state."""
        utils.check_skip_if_microversion_not_supported(version)
        if (self.replication_type
                not in constants.REPLICATION_PROMOTION_CHOICES):
            msg = "Option backend_replication_type should be one of (%s)!"
            raise self.skipException(
                msg % ','.join(constants.REPLICATION_PROMOTION_CHOICES))
        share = self.create_share(
            share_type_id=self.share_type_id, client=self.admin_client,
            availability_zone=self.share_zone, share_network_id=self.sn_id)
        original_replica = self.admin_client.list_share_replicas(
            share_id=share['id'], version=version)['share_replicas'][0]

        # NOTE(Yogi1): Cleanup needs to be disabled for replica that is
        # being promoted since it will become the 'primary'/'active' replica.
        replica = self.create_share_replica(
            share["id"], self.replica_zone, cleanup=False,
            client=self.admin_client, version=version)
        # Wait for replica state to update after creation
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        # List replicas
        replica_list = self.admin_client.list_share_replicas(
            share_id=share['id'], version=version)['share_replicas']

        # Check if there is only 1 'active' replica before promotion.
        active_replicas = self._filter_share_replica_list(
            replica_list, constants.REPLICATION_STATE_ACTIVE)
        self.assertEqual(1, len(active_replicas))

        # Set replica_state to 'out_of_sync'
        self.admin_client.reset_share_replica_state(
            replica['id'], constants.REPLICATION_STATE_OUT_OF_SYNC,
            version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'],
            constants.REPLICATION_STATE_OUT_OF_SYNC,
            resource_name='share_replica', status_attr='replica_state')

        # Promote 'out_of_sync' replica to 'active' state.
        self.promote_share_replica(replica['id'], self.admin_client,
                                   version=version)
        # Original replica will need to be cleaned up before the promoted
        # replica can be deleted.
        self.addCleanup(self.delete_share_replica, original_replica['id'],
                        client=self.admin_client)

        # Check if there is still only 1 'active' replica after promotion.
        replica_list = self.admin_client.list_share_replicas(
            share_id=self.share["id"], version=version)['share_replicas']
        new_active_replicas = self._filter_share_replica_list(
            replica_list, constants.REPLICATION_STATE_ACTIVE)
        self.assertEqual(1, len(new_active_replicas))

    @decorators.idempotent_id('22a199b7-f4f6-4ede-b09f-8047a9d01cad')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_REPLICATION_VERSION,
                            constants.SHARE_REPLICA_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_force_delete_share_replica(self, version):
        """Test force deleting a replica that is in 'error_deleting' status."""
        utils.check_skip_if_microversion_not_supported(version)
        replica = self.create_share_replica(self.share['id'],
                                            self.replica_zone,
                                            cleanup_in_class=False,
                                            client=self.admin_client,
                                            version=version)
        self.admin_client.reset_share_replica_status(
            replica['id'], constants.STATUS_ERROR_DELETING, version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'], constants.STATUS_ERROR_DELETING,
            resource_name='share_replica')
        self.admin_client.force_delete_share_replica(replica['id'],
                                                     version=version)
        self.admin_client.wait_for_resource_deletion(replica_id=replica['id'])

    @decorators.idempotent_id('16bd90f0-c478-4a99-8633-b18703ff56fa')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_REPLICATION_VERSION,
                            constants.SHARE_REPLICA_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_reset_share_replica_status(self, version):
        """Test resetting a replica's 'status' attribute."""
        utils.check_skip_if_microversion_not_supported(version)
        replica = self.create_share_replica(self.share['id'],
                                            self.replica_zone,
                                            cleanup_in_class=False,
                                            client=self.admin_client,
                                            version=version)
        self.admin_client.reset_share_replica_status(replica['id'],
                                                     constants.STATUS_ERROR,
                                                     version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'], constants.STATUS_ERROR,
            resource_name='share_replica')

    @decorators.idempotent_id('258844da-a853-42b6-87db-b16e616018c6')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_REPLICATION_VERSION,
                            constants.SHARE_REPLICA_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_reset_share_replica_state(self, version):
        """Test resetting a replica's 'replica_state' attribute."""
        utils.check_skip_if_microversion_not_supported(version)
        replica = self.create_share_replica(self.share['id'],
                                            self.replica_zone,
                                            cleanup_in_class=False,
                                            client=self.admin_client,
                                            version=version)
        self.admin_client.reset_share_replica_state(replica['id'],
                                                    constants.STATUS_ERROR,
                                                    version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'], constants.STATUS_ERROR,
            resource_name='share_replica', status_attr='replica_state')

    @decorators.unstable_test(bug='1631314')
    @decorators.idempotent_id('2969565a-85e8-4c61-9dfb-cc7f7ca9f6dd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_REPLICATION_VERSION,
                            constants.SHARE_REPLICA_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_resync_share_replica(self, version):
        """Test resyncing a replica."""
        utils.check_skip_if_microversion_not_supported(version)
        replica = self.create_share_replica(self.share['id'],
                                            self.replica_zone,
                                            cleanup_in_class=False,
                                            client=self.admin_client,
                                            version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        # Set replica_state to 'out_of_sync'.
        self.admin_client.reset_share_replica_state(
            replica['id'], constants.REPLICATION_STATE_OUT_OF_SYNC,
            version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'],
            constants.REPLICATION_STATE_OUT_OF_SYNC,
            resource_name='share_replica', status_attr='replica_state')

        # Attempt resync
        self.admin_client.resync_share_replica(replica['id'], version=version)
        waiters.wait_for_resource_status(
            self.admin_client, replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')
