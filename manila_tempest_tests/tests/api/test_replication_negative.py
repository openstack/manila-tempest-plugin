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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
_MIN_SUPPORTED_MICROVERSION = '2.11'


class ReplicationNegativeBase(base.BaseSharesMixedTest):
    @classmethod
    def skip_checks(cls):
        super(ReplicationNegativeBase, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

        utils.check_skip_if_microversion_lt(_MIN_SUPPORTED_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ReplicationNegativeBase, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.replication_type = CONF.share.backend_replication_type
        cls.multitenancy_enabled = (
            utils.replication_with_multitenancy_support())

        if cls.replication_type not in constants.REPLICATION_TYPE_CHOICES:
            raise share_exceptions.ShareReplicationTypeException(
                replication_type=cls.replication_type
            )

        # create share type
        extra_specs = {"replication_type": cls.replication_type}
        cls.share_type = cls._create_share_type(specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        cls.sn_id = None
        if cls.multitenancy_enabled:
            cls.share_network = cls.shares_v2_client.get_share_network(
                cls.shares_v2_client.share_network_id)
            cls.sn_id = cls.share_network['id']
        cls.zones = cls.get_availability_zones_matching_share_type(
            cls.share_type, client=cls.admin_client)
        cls.share_zone = cls.zones[0]
        cls.replica_zone = cls.zones[-1]

        # create share with above share_type
        cls.share1, cls.instance_id1 = cls._create_share_get_instance()

    @classmethod
    def _create_share_get_instance(cls, share_network_id=None):
        sn_id = share_network_id if share_network_id else cls.sn_id
        share = cls.create_share(share_type_id=cls.share_type_id,
                                 availability_zone=cls.share_zone,
                                 share_network_id=sn_id)
        share_instances = cls.admin_client.get_instances_of_share(
            share["id"], version=_MIN_SUPPORTED_MICROVERSION
        )
        instance_id = share_instances[0]["id"]
        return share, instance_id


class ReplicationNegativeTest(ReplicationNegativeBase):

    def _is_replication_type_promotable(self):
        if (self.replication_type
                not in constants.REPLICATION_PROMOTION_CHOICES):
            msg = "Option backend_replication_type should be one of (%s)!"
            raise self.skipException(
                msg % ','.join(constants.REPLICATION_PROMOTION_CHOICES))

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_add_replica_to_share_with_no_replication_share_type(self):
        # Create share without replication type
        share_type = self.create_share_type(
            data_utils.rand_name(constants.TEMPEST_MANILA_PREFIX),
            extra_specs=self.add_extra_specs_to_dict(),
            client=self.admin_client)["share_type"]
        share = self.create_share(share_type_id=share_type["id"],
                                  share_network_id=self.sn_id)
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share_replica,
                          share['id'],
                          self.replica_zone)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_add_replica_to_share_with_error_state(self):
        # Set "error" state
        self.admin_client.reset_state(
            self.share1['id'], constants.STATUS_ERROR)
        self.addCleanup(self.admin_client.reset_state,
                        self.share1['id'],
                        constants.STATUS_AVAILABLE)
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share_replica,
                          self.share1['id'],
                          self.replica_zone)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_delete_last_active_replica(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.delete_share_replica,
                          self.instance_id1)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_delete_share_having_replica(self):
        self.create_share_replica(self.share1["id"], self.replica_zone,
                                  cleanup_in_class=False)
        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.delete_share,
                          self.share1["id"])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_promote_out_of_sync_share_replica(self):
        # Test promoting an out_of_sync share_replica to active state
        self._is_replication_type_promotable()
        share, instance_id = self._create_share_get_instance()
        replica = self.create_share_replica(share["id"], self.replica_zone,
                                            cleanup_in_class=False)
        # Set replica state to out of sync
        self.admin_client.reset_share_replica_state(
            replica['id'], constants.REPLICATION_STATE_OUT_OF_SYNC)
        self.shares_v2_client.wait_for_share_replica_status(
            replica['id'], constants.REPLICATION_STATE_OUT_OF_SYNC,
            status_attr='replica_state')
        # Try promoting the first out_of_sync replica to active state
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.promote_share_replica,
                          replica['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_promote_active_share_replica(self):
        # Test promote active share_replica
        self._is_replication_type_promotable()

        # Try promoting the active replica
        self.shares_v2_client.promote_share_replica(self.instance_id1,
                                                    expected_status=200)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_promote_share_replica_for_writable_share_type(self):
        # Test promote active share_replica for writable share
        if self.replication_type != "writable":
            raise self.skipException("Option backend_replication_type "
                                     "should be writable!")
        share, instance_id = self._create_share_get_instance()
        replica = self.create_share_replica(share["id"], self.replica_zone,
                                            cleanup_in_class=False)
        # By default, 'writable' replica is expected to be in active state
        self.shares_v2_client.wait_for_share_replica_status(
            replica["id"], constants.REPLICATION_STATE_ACTIVE,
            status_attr='replica_state')

        # Try promoting the replica
        self.shares_v2_client.promote_share_replica(replica['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_add_access_rule_share_replica_error_status(self):
        access_type, access_to = self._get_access_rule_data_from_config()
        # Create the replica
        share_replica = self.create_share_replica(self.share1["id"],
                                                  self.replica_zone,
                                                  cleanup_in_class=False)
        # Reset the replica status to error
        self.admin_client.reset_share_replica_status(
            share_replica['id'], constants.STATUS_ERROR)

        # Verify access rule cannot be added
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_client.create_access_rule,
                          self.share1["id"], access_type, access_to, 'ro')

    @testtools.skipUnless(CONF.share.run_host_assisted_migration_tests or
                          CONF.share.run_driver_assisted_migration_tests,
                          "Share migration tests are disabled.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @base.skip_if_microversion_lt("2.29")
    def test_migration_of_replicated_share(self):
        pools = self.admin_client.list_pools(detail=True)['pools']
        hosts = [p['name'] for p in pools]
        self.create_share_replica(self.share1["id"], self.replica_zone,
                                  cleanup_in_class=False)
        share_host = self.admin_client.get_share(self.share1['id'])['host']

        for host in hosts:
            if host != share_host:
                dest_host = host
                break

        self.assertRaises(
            lib_exc.Conflict, self.admin_client.migrate_share,
            self.share1['id'], dest_host)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @base.skip_if_microversion_lt("2.48")
    def test_try_add_replica_share_type_azs_unsupported_az(self):
        self.admin_shares_v2_client.update_share_type_extra_spec(
            self.share_type['id'], 'availability_zones', 'non-existent az')
        self.addCleanup(
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            self.share_type['id'], 'availability_zones')
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share_replica,
                          self.share1['id'],
                          self.replica_zone)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @base.skip_if_microversion_lt("2.51")
    def test_try_add_replica_nonexistent_subnet(self):
        # Create a new share network only for a specific az
        data = self.generate_share_network_data()
        subnet = utils.share_network_get_default_subnet(self.share_network)
        data['neutron_net_id'] = subnet['neutron_net_id']
        data['neutron_subnet_id'] = subnet['neutron_subnet_id']
        data['availability_zone'] = self.share_zone
        share_net = self.shares_v2_client.create_share_network(**data)
        share, instance_id = self._create_share_get_instance(
            share_network_id=share_net['id'])

        self.assertRaises(lib_exc.BadRequest,
                          self.create_share_replica,
                          share['id'],
                          self.replica_zone)


class ReplicationAPIOnlyNegativeTest(base.BaseSharesTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationAPIOnlyNegativeTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

        utils.check_skip_if_microversion_lt(_MIN_SUPPORTED_MICROVERSION)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_replica_by_nonexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_share_replica,
                          data_utils.rand_uuid())

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_replica_by_nonexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_share_replica,
                          data_utils.rand_uuid())
