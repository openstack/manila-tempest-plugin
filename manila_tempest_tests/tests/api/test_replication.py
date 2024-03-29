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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion
_MIN_SUPPORTED_MICROVERSION = '2.11'
SUMMARY_KEYS = ['share_id', 'id', 'replica_state', 'status']
DETAIL_KEYS = SUMMARY_KEYS + ['availability_zone', 'updated_at',
                              'share_network_id', 'created_at']


@ddt.ddt
class ReplicationTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

        utils.check_skip_if_microversion_not_supported(
            _MIN_SUPPORTED_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ReplicationTest, cls).resource_setup()
        # Create share_type
        name = data_utils.rand_name(constants.TEMPEST_MANILA_PREFIX)
        cls.admin_client = cls.admin_shares_v2_client
        cls.replication_type = CONF.share.backend_replication_type
        cls.multitenancy_enabled = (
            utils.replication_with_multitenancy_support())

        if cls.replication_type not in constants.REPLICATION_TYPE_CHOICES:
            raise share_exceptions.ShareReplicationTypeException(
                replication_type=cls.replication_type
            )
        cls.extra_specs = cls.add_extra_specs_to_dict(
            {"replication_type": cls.replication_type})
        cls.share_type = cls.create_share_type(
            name,
            extra_specs=cls.extra_specs,
            client=cls.admin_client)

        cls.zones = cls.get_availability_zones_matching_share_type(
            cls.share_type, client=cls.admin_client)
        cls.share_zone = cls.zones[0]
        cls.replica_zone = cls.zones[-1]

        # Create share with above share_type
        cls.creation_data = {'kwargs': {
            'share_type_id': cls.share_type['id'],
            'availability_zone': cls.share_zone,
        }}
        cls.sn_id = None
        if cls.multitenancy_enabled:
            cls.share_network = cls.shares_v2_client.get_share_network(
                cls.shares_v2_client.share_network_id)['share_network']
            cls.creation_data['kwargs'].update({
                'share_network_id': cls.share_network['id']})
            cls.sn_id = cls.share_network['id']

        # Data for creating shares in parallel
        data = [cls.creation_data, cls.creation_data]
        cls.shares = cls.create_shares(data)
        cls.shares = [cls.shares_v2_client.get_share(s['id'])['share'] for s in
                      cls.shares]
        cls.instance_id1 = cls._get_instance(cls.shares[0])
        cls.instance_id2 = cls._get_instance(cls.shares[1])

    @classmethod
    def _get_instance(cls, share):
        share_instances = cls.admin_client.get_instances_of_share(
            share["id"])['share_instances']
        return share_instances[0]["id"]

    def _verify_create_replica(self, version=LATEST_MICROVERSION):
        # Create the replica
        share_net_id = None
        if utils.is_microversion_ge(version, (
                constants.SHARE_REPLICA_SHARE_NET_PARAM_VERSION)):
            share_net_id = self.sn_id
        share_replica = self.create_share_replica(
            self.shares[0]["id"], self.replica_zone,
            share_network_id=share_net_id, cleanup_in_class=False)
        share_replicas = self.shares_v2_client.list_share_replicas(
            share_id=self.shares[0]["id"])['share_replicas']
        # Ensure replica is created successfully.
        replica_ids = [replica["id"] for replica in share_replicas]
        self.assertIn(share_replica["id"], replica_ids)
        return share_replica

    def _verify_active_replica_count(self, share_id):
        # List replicas
        replica_list = self.shares_v2_client.list_share_replicas(
            share_id=share_id)['share_replicas']

        # Check if there is only 1 'active' replica before promotion.
        active_replicas = self._filter_replica_list(
            replica_list, constants.REPLICATION_STATE_ACTIVE)
        self.assertEqual(1, len(active_replicas))

    def _filter_replica_list(self, replica_list, r_state):
        # Iterate through replica list to filter based on replica_state
        return [replica for replica in replica_list
                if replica['replica_state'] == r_state]

    def _verify_in_sync_replica_promotion(self, share, original_replica):
        # Verify that 'in-sync' replica has been promoted successfully

        # NOTE(Yogi1): Cleanup needs to be disabled for replica that is
        # being promoted since it will become the 'primary'/'active' replica.
        replica = self.create_share_replica(share["id"], self.replica_zone,
                                            cleanup=False)
        # Wait for replica state to update after creation
        waiters.wait_for_resource_status(
            self.shares_v2_client, replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')
        # Promote the first in_sync replica to active state
        promoted_replica = self.promote_share_replica(replica['id'])
        # Delete the demoted replica so promoted replica can be cleaned
        # during the cleanup of the share.
        self.addCleanup(self.delete_share_replica, original_replica['id'])
        self._verify_active_replica_count(share["id"])
        # Verify the replica_state for promoted replica
        promoted_replica = self.shares_v2_client.get_share_replica(
            promoted_replica["id"])['share_replica']
        self.assertEqual(constants.REPLICATION_STATE_ACTIVE,
                         promoted_replica["replica_state"])

    def _check_skip_promotion_tests(self):
        # Check if the replication type is right for replica promotion tests
        if (self.replication_type
                not in constants.REPLICATION_PROMOTION_CHOICES):
            msg = "Option backend_replication_type should be one of (%s)!"
            raise self.skipException(
                msg % ','.join(constants.REPLICATION_PROMOTION_CHOICES))

    @decorators.idempotent_id('c59e3198-062b-4284-8a3b-189a62213573')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @ddt.data(
        *utils.deduplicate([constants.SHARE_REPLICA_SHARE_NET_PARAM_VERSION,
                            LATEST_MICROVERSION]))
    def test_create_share_replica_with_provided_network(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        share_replica = self._verify_create_replica(version)
        self.assertIsNotNone(share_replica)

    @decorators.idempotent_id('8858617f-292d-4e5c-9e15-794b7f1b2e3c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_add_delete_share_replica(self):
        # Create the replica
        share_replica = self._verify_create_replica()

        # Delete the replica
        self.delete_share_replica(share_replica["id"])

    @decorators.idempotent_id('58c3faf4-6c97-4fec-9a9b-7cff0d2035cd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @utils.skip_if_microversion_not_supported("2.51")
    def test_add_delete_share_replica_different_subnet(self):
        # Create new subnet in replica az
        subnet = utils.share_network_get_default_subnet(self.share_network)
        data = {
            'neutron_net_id': subnet.get('neutron_net_id'),
            'neutron_subnet_id': subnet.get('neutron_subnet_id'),
            'share_network_id': self.sn_id,
            'availability_zone': self.replica_zone,
        }
        subnet = self.create_share_network_subnet(**data)
        # Create the replica
        share_replica = self._verify_create_replica()

        # Delete the replica
        self.delete_share_replica(share_replica["id"])
        # Delete subnet
        self.shares_v2_client.delete_subnet(self.sn_id, subnet['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @testtools.skipIf(
        not CONF.share.run_share_server_multiple_subnet_tests,
        "Share server multiple subnet tests are disabled.")
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share networks.")
    @utils.skip_if_microversion_not_supported("2.70")
    @decorators.idempotent_id('4235e789-dbd6-47a8-8f2e-d70edf78e532')
    def test_add_delete_share_replica_multiple_subnets(self):
        extra_specs = {
            "replication_type": self.replication_type,
            "driver_handles_share_servers": CONF.share.multitenancy_enabled,
            "share_server_multiple_subnet_support": True,
        }
        share_type = self.create_share_type(
            extra_specs=extra_specs, client=self.admin_client)
        default_subnet = utils.share_network_get_default_subnet(
            self.share_network)
        new_share_network_id = self.create_share_network(
            cleanup_in_class=False)['id']
        subnet_data = {
            'neutron_net_id': default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': default_subnet.get('neutron_subnet_id'),
            'share_network_id': new_share_network_id,
            'availability_zone': self.replica_zone,
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)
        subnet2 = self.create_share_network_subnet(**subnet_data)
        # Creating a third subnet in share replica az
        subnet_data.update({'availability_zone': self.share_zone})
        subnet3 = self.create_share_network_subnet(**subnet_data)
        # Create the share and share replica
        share = self.create_share(
            share_type_id=share_type['id'], cleanup_in_class=False,
            availability_zone=self.share_zone,
            share_network_id=new_share_network_id)
        share = self.admin_client.get_share(share['id'])['share']
        replica = self.create_share_replica(share['id'], self.replica_zone)
        replica = self.admin_client.get_share_replica(
            replica['id'])['share_replica']
        share_server = self.admin_client.show_share_server(
            replica['share_server_id'])['share_server']
        self.assertIn(subnet1['id'],
                      share_server['share_network_subnet_ids'])
        self.assertIn(subnet2['id'],
                      share_server['share_network_subnet_ids'])
        # Delete the replica
        self.delete_share_replica(replica['id'])
        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete subnets
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet1['id'])
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet2['id'])
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet3['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @testtools.skipIf(
        not CONF.share.run_network_allocation_update_tests,
        "Share server network allocation update tests are disabled.")
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    @utils.skip_if_microversion_not_supported("2.70")
    @decorators.idempotent_id('26694947-d4a0-46c8-99e8-2e0eca1b6a08')
    def test_add_delete_share_replica_network_allocation_update(self):
        extra_specs = {
            "replication_type": self.replication_type,
            "driver_handles_share_servers": CONF.share.multitenancy_enabled,
            "network_allocation_update_support": True,
        }
        share_type = self.create_share_type(extra_specs=extra_specs)

        default_subnet = utils.share_network_get_default_subnet(
            self.share_network)
        new_share_network_id = self.create_share_network(
            cleanup_in_class=False)['id']
        subnet_data = {
            'neutron_net_id': default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': default_subnet.get('neutron_subnet_id'),
            'share_network_id': new_share_network_id,
            'availability_zone': self.share_zone,
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)
        subnet_data.update({'availability_zone': self.replica_zone})
        subnet2 = self.create_share_network_subnet(**subnet_data)
        # Create the share and share replica
        share = self.create_share(
            share_type_id=share_type['id'], cleanup_in_class=False,
            availability_zone=self.share_zone,
            share_network_id=new_share_network_id)
        share = self.admin_client.get_share(share['id'])['share']

        replica = self.create_share_replica(share['id'], self.replica_zone)
        replica = self.admin_client.get_share_replica(
            replica['id'])['share_replica']

        # Waits until the check is completed and positive
        waiters.wait_for_subnet_create_check(
            self.shares_v2_client, new_share_network_id,
            neutron_net_id=subnet_data['neutron_net_id'],
            neutron_subnet_id=subnet_data['neutron_subnet_id'],
            availability_zone=self.replica_zone)
        # Creating a third subnet in replica zone to trigger the network
        # allocation update
        subnet3 = self.create_share_network_subnet(**subnet_data)
        waiters.wait_for_resource_status(
            self.admin_client, replica['share_server_id'],
            constants.SERVER_STATE_ACTIVE,
            resource_name="share_server",
            status_attr="status")
        share_server = self.admin_client.show_share_server(
            replica['share_server_id']
        )['share_server']
        self.assertIn(subnet2['id'],
                      share_server['share_network_subnet_ids'])
        self.assertIn(subnet3['id'],
                      share_server['share_network_subnet_ids'])
        # Delete the replica
        self.delete_share_replica(replica['id'])
        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete subnets
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet1['id'])
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet2['id'])
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet3['id'])

    @decorators.idempotent_id('00e12b41-b95d-494a-99be-e584aae10f5c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_add_access_rule_create_replica_delete_rule(self):
        # Add access rule to the share
        access_type, access_to = utils.get_access_rule_data_from_config(
            self.shares_v2_client.share_protocol)
        self.allow_access(
            self.shares[0]["id"], access_type=access_type, access_to=access_to,
            access_level='ro')

        # Create the replica
        self._verify_create_replica()

        # Verify access_rules_status transitions to 'active' state.
        waiters.wait_for_resource_status(
            self.shares_v2_client, self.shares[0]["id"],
            constants.RULE_STATE_ACTIVE, status_attr='access_rules_status')

    @decorators.idempotent_id('3af3f19a-1195-464e-870b-1a3918914f1b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_replica_add_access_rule_delete_replica(self):
        access_type, access_to = utils.get_access_rule_data_from_config(
            self.shares_v2_client.share_protocol)
        # Create the replica
        share_replica = self._verify_create_replica()

        # Add access rule
        self.allow_access(
            self.shares[0]["id"], access_type=access_type, access_to=access_to,
            access_level='ro')

        # Delete the replica
        self.delete_share_replica(share_replica["id"])

    @decorators.idempotent_id('600a13d2-5cf0-482e-97af-9f598b55a406')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.74")
    def test_add_access_rule_share_replica_error_status(self):
        '''From 2.74, we can add rules even if replicas are in error state.'''
        access_type, access_to = utils.get_access_rule_data_from_config(
            self.shares_v2_client.share_protocol)
        # Create the replica
        share_replica = self._verify_create_replica()

        # Reset the replica status to error
        self.admin_client.reset_share_replica_status(
            share_replica['id'], constants.STATUS_ERROR)

        # Verify access rule will be added in error state
        self.shares_v2_client.create_access_rule(
            self.shares[0]["id"], access_type=access_type, access_to=access_to,
            access_level='ro')

        # Verify access_rules_status transitions to 'active' state.
        waiters.wait_for_resource_status(
            self.shares_v2_client, self.shares[0]["id"],
            constants.RULE_STATE_ACTIVE, status_attr='access_rules_status')

    @decorators.idempotent_id('a542c179-ea41-4bc0-bd80-e06eaddf5253')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(CONF.share.run_multiple_share_replicas_tests,
                          'Multiple share replicas tests are disabled.')
    def test_add_multiple_share_replicas(self):
        rep_domain, pools = self.get_pools_for_replication_domain()
        if len(pools) < 3:
            msg = ("Replication domain %(domain)s has only %(count)s pools. "
                   "Need at least 3 pools to run this test." %
                   {"domain": rep_domain, "count": len(pools)})
            raise self.skipException(msg)
        # Add the replicas
        share_replica1 = self.create_share_replica(self.shares[0]["id"],
                                                   self.replica_zone,
                                                   cleanup_in_class=False)
        share_replica2 = self.create_share_replica(self.shares[0]["id"],
                                                   self.replica_zone,
                                                   cleanup_in_class=False)
        self.shares_v2_client.get_share_replica(share_replica2['id'])

        share_replicas = self.admin_client.list_share_replicas(
            share_id=self.shares[0]["id"])['share_replicas']
        replica_host_set = {r['host'] for r in share_replicas}

        # Assert that replicas are created on different pools.
        msg = "More than one replica is created on the same pool."
        self.assertEqual(3, len(replica_host_set), msg)
        # Verify replicas are in the replica list
        replica_ids = [replica["id"] for replica in share_replicas]
        self.assertIn(share_replica1["id"], replica_ids)
        self.assertIn(share_replica2["id"], replica_ids)

    @decorators.idempotent_id('98b7c1d6-02e8-425a-b697-db2d2671fa11')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_promote_in_sync_share_replica(self):
        # Test promote 'in_sync' share_replica to 'active' state
        self._check_skip_promotion_tests()
        share = self.create_shares([self.creation_data])[0]
        original_replica = self.shares_v2_client.list_share_replicas(
            share["id"])['share_replicas'][0]
        self._verify_in_sync_replica_promotion(share, original_replica)

    @decorators.idempotent_id('3af912f4-b5d7-4241-b2b3-bdf12ff398a4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_add_rule_promote_share_replica_verify_rule(self):
        # Verify the access rule stays intact after share replica promotion
        self._check_skip_promotion_tests()

        share = self.create_shares([self.creation_data])[0]
        # Add access rule
        access_type, access_to = utils.get_access_rule_data_from_config(
            self.shares_v2_client.share_protocol)
        self.allow_access(
            share["id"], access_type=access_type, access_to=access_to,
            access_level='ro')

        original_replica = self.shares_v2_client.list_share_replicas(
            share["id"])['share_replicas'][0]
        self._verify_in_sync_replica_promotion(share, original_replica)

        # verify rule's values
        rules_list = self.shares_v2_client.list_access_rules(
            share["id"])['access_list']
        self.assertEqual(1, len(rules_list))
        self.assertEqual(access_type, rules_list[0]["access_type"])
        self.assertEqual(access_to, rules_list[0]["access_to"])
        self.assertEqual('ro', rules_list[0]["access_level"])

    @decorators.idempotent_id('7904e3c7-e6d0-472d-b9c9-c0772b4f9f1b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.48")
    def test_share_type_azs_share_replicas(self):
        az_spec = ', '.join(self.zones)
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type['id'], 'availability_zones', az_spec)
        self.addCleanup(
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            self.share_type['id'], 'availability_zones')

        share = self.create_share(
            share_type_id=self.share_type['id'], cleanup_in_class=False,
            availability_zone=self.share_zone, share_network_id=self.sn_id)
        share = self.shares_v2_client.get_share(share['id'])['share']
        replica = self.create_share_replica(share['id'], self.replica_zone)
        replica = self.shares_v2_client.get_share_replica(
            replica['id'])['share_replica']

        self.assertEqual(self.share_zone, share['availability_zone'])
        self.assertEqual(self.replica_zone, replica['availability_zone'])
        self.assertIn(share['availability_zone'], self.zones)
        self.assertIn(replica['availability_zone'], self.zones)

    @decorators.idempotent_id('b5ade58b-cb81-47eb-966b-28e6d85b5568')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_promote_and_promote_back(self):
        # Test promote back and forth between 2 share replicas
        self._check_skip_promotion_tests()

        # Create a new share
        share = self.create_shares([self.creation_data])[0]

        # Discover the original replica
        initial_replicas = self.shares_v2_client.list_share_replicas(
            share_id=share['id'])['share_replicas']
        self.assertEqual(1, len(initial_replicas),
                         '%s replicas initially created for share %s' %
                         (len(initial_replicas), share['id']))
        original_replica = initial_replicas[0]

        # Create a new replica
        new_replica = self.create_share_replica(share["id"],
                                                self.replica_zone,
                                                cleanup_in_class=False)
        waiters.wait_for_resource_status(
            self.shares_v2_client, new_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        # Promote the new replica to active and verify the replica states
        self.promote_share_replica(new_replica['id'])
        self._verify_active_replica_count(share["id"])
        waiters.wait_for_resource_status(
            self.shares_v2_client, original_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        # Promote the original replica back to active
        self.promote_share_replica(original_replica['id'])
        self._verify_active_replica_count(share["id"])
        waiters.wait_for_resource_status(
            self.shares_v2_client, new_replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

    @decorators.idempotent_id('1452156b-75a5-4f3c-a921-834732a03b0a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_active_replication_state(self):
        # Verify the replica_state of first instance is set to active.
        replica = self.shares_v2_client.get_share_replica(
            self.instance_id1)['share_replica']
        self.assertEqual(
            constants.REPLICATION_STATE_ACTIVE, replica['replica_state'])


class ReplicationActionsTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationActionsTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

        utils.check_skip_if_microversion_not_supported(
            _MIN_SUPPORTED_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ReplicationActionsTest, cls).resource_setup()
        # Create share_type
        name = data_utils.rand_name(constants.TEMPEST_MANILA_PREFIX)
        cls.admin_client = cls.admin_shares_v2_client
        cls.replication_type = CONF.share.backend_replication_type
        cls.multitenancy_enabled = (
            utils.replication_with_multitenancy_support())

        if cls.replication_type not in constants.REPLICATION_TYPE_CHOICES:
            raise share_exceptions.ShareReplicationTypeException(
                replication_type=cls.replication_type
            )
        cls.extra_specs = cls.add_extra_specs_to_dict(
            {"replication_type": cls.replication_type})
        cls.share_type = cls.create_share_type(
            name,
            extra_specs=cls.extra_specs,
            client=cls.admin_client)

        cls.zones = cls.get_availability_zones_matching_share_type(
            cls.share_type, client=cls.admin_client)
        cls.share_zone = cls.zones[0]
        cls.replica_zone = cls.zones[-1]

        # Create share with above share_type
        cls.creation_data = {'kwargs': {
            'share_type_id': cls.share_type['id'],
            'availability_zone': cls.share_zone,
        }}

        if cls.multitenancy_enabled:
            cls.share_network = cls.shares_v2_client.get_share_network(
                cls.shares_v2_client.share_network_id)['share_network']
            cls.creation_data['kwargs'].update({
                'share_network_id': cls.share_network['id']})
        cls.sn_id = (
            cls.share_network['id'] if cls.multitenancy_enabled else None)
        # Data for creating shares in parallel
        data = [cls.creation_data, cls.creation_data]
        cls.shares = cls.create_shares(data)
        cls.shares = [cls.shares_v2_client.get_share(s['id'])['share'] for s in
                      cls.shares]
        cls.instance_id1 = cls._get_instance(cls.shares[0])
        cls.instance_id2 = cls._get_instance(cls.shares[1])

        # Create replicas to 2 shares
        cls.replica1 = cls.create_share_replica(cls.shares[0]["id"],
                                                cls.replica_zone,
                                                cleanup_in_class=True)
        cls.replica2 = cls.create_share_replica(cls.shares[1]["id"],
                                                cls.replica_zone,
                                                cleanup_in_class=True)

    @classmethod
    def _get_instance(cls, share):
        share_instances = cls.admin_client.get_instances_of_share(
            share["id"])['share_instances']
        return share_instances[0]["id"]

    def _validate_replica_list(self, replica_list, detail=True):
        # Verify keys
        if detail:
            keys = DETAIL_KEYS
        else:
            keys = SUMMARY_KEYS
        for replica in replica_list:
            self.assertEqual(sorted(keys), sorted(replica.keys()))
            # Check for duplicates
            replica_id_list = [sr["id"] for sr in replica_list
                               if sr["id"] == replica["id"]]
            msg = "Replica %s appears %s times in replica list." % (
                replica['id'], len(replica_id_list))
            self.assertEqual(1, len(replica_id_list), msg)

    @decorators.idempotent_id('abe0e49d-0b94-4b81-a220-ab047712492d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_show_share_replica(self):
        replica = self.shares_v2_client.get_share_replica(
            self.replica1["id"])['share_replica']

        actual_keys = sorted(list(replica.keys()))
        detail_keys = sorted(DETAIL_KEYS)
        self.assertEqual(detail_keys, actual_keys,
                         'Share Replica %s has incorrect keys; '
                         'expected %s, got %s.' % (replica["id"],
                                                   detail_keys, actual_keys))

    @decorators.idempotent_id('f5225fb7-fcbe-4825-bf5b-0e11c2d26e03')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_detail_list_share_replicas_for_share(self):
        # List replicas for share
        replica_list = self.shares_v2_client.list_share_replicas(
            share_id=self.shares[0]["id"])['share_replicas']
        replica_ids_list = [rep['id'] for rep in replica_list]
        self.assertIn(self.replica1['id'], replica_ids_list,
                      'Replica %s was not returned in the list of replicas: %s'
                      % (self.replica1['id'], replica_list))
        # Verify keys
        self._validate_replica_list(replica_list)

    @decorators.idempotent_id('e39aeb5d-fe4b-4896-8615-e6e7290bcb56')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_detail_list_share_replicas_for_all_shares(self):
        # List replicas for all available shares
        replica_list = self.shares_v2_client.list_share_replicas(
            )['share_replicas']
        replica_ids_list = [rep['id'] for rep in replica_list]
        for replica in [self.replica1, self.replica2]:
            self.assertIn(replica['id'], replica_ids_list,
                          'Replica %s was not returned in the list of '
                          'replicas: %s' % (replica['id'], replica_list))
        # Verify keys
        self._validate_replica_list(replica_list)

    @decorators.idempotent_id('8d11848a-7766-41e5-af09-6121e5bad447')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_summary_list_share_replicas_for_all_shares(self):
        # List replicas
        replica_list = self.shares_v2_client.list_share_replicas_summary(
            )['share_replicas']

        # Verify keys
        self._validate_replica_list(replica_list, detail=False)
