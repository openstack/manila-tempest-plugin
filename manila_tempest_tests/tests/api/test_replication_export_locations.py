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


@ddt.ddt
class ReplicationExportLocationsTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationExportLocationsTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

    @classmethod
    def resource_setup(cls):
        super(ReplicationExportLocationsTest, cls).resource_setup()
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
        cls.sn_id = None
        if cls.multitenancy_enabled:
            cls.share_network = cls.shares_v2_client.get_share_network(
                cls.shares_v2_client.share_network_id)['share_network']
            cls.sn_id = cls.share_network['id']
        cls.zones = cls.get_availability_zones_matching_share_type(
            cls.share_type)
        cls.share_zone = cls.zones[0]
        cls.replica_zone = cls.zones[-1]

    @staticmethod
    def _remove_admin_only_exports(all_exports):
        return [e for e in all_exports if not e['is_admin_only']]

    def _create_share_and_replica_get_exports(self, cleanup_replica=True):
        share = self.create_share(share_type_id=self.share_type['id'],
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        replica = self.create_share_replica(share['id'], self.replica_zone,
                                            cleanup=cleanup_replica)
        replicas = self.shares_v2_client.list_share_replicas(
            share_id=share['id'])['share_replicas']
        primary_replica = [r for r in replicas if r['id'] != replica['id']][0]

        # Refresh share and replica
        share = self.shares_v2_client.get_share(share['id'])['share']
        replica = self.shares_v2_client.get_share_replica(
            replica['id'])['share_replica']

        # Grab export locations of the share instances using admin API
        replica_exports = self._remove_admin_only_exports(
            self.admin_client.list_share_instance_export_locations(
                replica['id'])['export_locations'])
        primary_replica_exports = self._remove_admin_only_exports(
            self.admin_client.list_share_instance_export_locations(
                primary_replica['id'])['export_locations'])

        return share, replica, primary_replica_exports, replica_exports

    def _validate_export_location_api_behavior(self, replica, replica_exports,
                                               primary_replica_exports,
                                               share_exports, version):
        share_export_paths = [e['path'] for e in share_exports]

        # Expectations
        expected_number_of_exports = len(primary_replica_exports
                                         + replica_exports)
        expected_exports = replica_exports + primary_replica_exports
        # In and beyond version 2.47, secondary "non-active" replica exports
        # are not expected to be present in the share export locations.
        # Secondary replicas can be "active" only in in "writable"
        # replication. In other types of replication, secondary replicas are
        # either "in_sync" or "out_of_sync"
        replica_is_non_active = (replica['replica_state'] !=
                                 constants.REPLICATION_STATE_ACTIVE)
        if utils.is_microversion_ge(version, '2.47') and replica_is_non_active:
            expected_number_of_exports = len(primary_replica_exports)
            expected_exports = primary_replica_exports

        # Assertions
        self.assertEqual(expected_number_of_exports, len(share_exports))
        for export in expected_exports:
            self.assertIn(export['path'], share_export_paths)

    @decorators.idempotent_id('da22cfb8-7dd8-4bf1-87fc-a1f7b51ebf8e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(*utils.deduplicate(['2.46', '2.47', LATEST_MICROVERSION]))
    def test_replicated_share_export_locations(self, version):
        """Test behavior changes in the share export locations API at 2.47"""
        utils.check_skip_if_microversion_not_supported(version)
        share, replica, primary_replica_exports, replica_exports = (
            self._create_share_and_replica_get_exports()
        )

        # Share export locations list API
        share_exports = self.shares_v2_client.list_share_export_locations(
            share['id'], version=version)['export_locations']

        self._validate_export_location_api_behavior(replica, replica_exports,
                                                    primary_replica_exports,
                                                    share_exports, version)

    @decorators.idempotent_id('58430f57-c6eb-44e2-9583-eecb1dd10594')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(*utils.deduplicate(['2.46', '2.47', LATEST_MICROVERSION]))
    @testtools.skipUnless(
        CONF.share.backend_replication_type in
        (constants.REPLICATION_STYLE_READABLE, constants.REPLICATION_STYLE_DR),
        'Promotion of secondary not supported in writable replication style.')
    def test_replicated_share_export_locations_with_promotion(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        share, replica, primary_replica_exports, replica_exports = (
            self._create_share_and_replica_get_exports(cleanup_replica=False)
        )
        primary_replica = self.shares_v2_client.get_share_replica(
            primary_replica_exports[0]['share_instance_id'])['share_replica']
        waiters.wait_for_resource_status(
            self.shares_v2_client, replica['id'],
            constants.REPLICATION_STATE_IN_SYNC, resource_name='share_replica',
            status_attr='replica_state')

        # Share export locations list API
        share_exports = self.shares_v2_client.list_share_export_locations(
            share['id'], version=version)['export_locations']

        # Validate API behavior
        self._validate_export_location_api_behavior(replica, replica_exports,
                                                    primary_replica_exports,
                                                    share_exports, version)

        # Promote share replica
        self.promote_share_replica(replica['id'])

        # Refresh for verification
        current_secondary_replica = self.shares_v2_client.get_share_replica(
            primary_replica['id'])['share_replica']
        current_primary_replica_exports = self._remove_admin_only_exports(
            self.admin_client.list_share_instance_export_locations(
                replica['id'], version=version)['export_locations'])
        current_secondary_replica_exports = self._remove_admin_only_exports(
            self.admin_client.list_share_instance_export_locations(
                primary_replica['id'], version=version)['export_locations'])
        share_exports = self.shares_v2_client.list_share_export_locations(
            share['id'], version=version)['export_locations']

        # Validate API behavior
        self._validate_export_location_api_behavior(
            current_secondary_replica, current_secondary_replica_exports,
            current_primary_replica_exports, share_exports, version)

        # Delete the secondary (the 'active' replica before promotion)
        self.delete_share_replica(primary_replica['id'])

    @decorators.idempotent_id('10ab6304-a1cd-4e60-90e3-7f9358b8808a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.47')
    def test_replica_export_locations(self):
        """Validates exports from the replica export locations APIs"""
        el_summary_keys = ['id', 'path', 'replica_state',
                           'availability_zone', 'preferred']
        el_detail_keys = el_summary_keys + ['created_at', 'updated_at']
        share, replica, expected_primary_exports, expected_replica_exports = (
            self._create_share_and_replica_get_exports()
        )
        primary_replica = self.shares_v2_client.get_share_replica(
            expected_primary_exports[0]['share_instance_id'])['share_replica']
        expected_primary_export_paths = [e['path'] for e in
                                         expected_primary_exports]
        expected_replica_export_paths = [e['path'] for e in
                                         expected_replica_exports]

        # For the primary replica
        actual_primary_exports = (
            self.shares_v2_client.list_share_replica_export_locations(
                primary_replica['id'])['export_locations']
        )

        self.assertEqual(len(expected_primary_exports),
                         len(actual_primary_exports))
        for export in actual_primary_exports:
            self.assertIn(export['path'], expected_primary_export_paths)
            self.assertEqual(constants.REPLICATION_STATE_ACTIVE,
                             export['replica_state'])
            self.assertEqual(share['availability_zone'],
                             export['availability_zone'])
            self.assertEqual(sorted(el_summary_keys), sorted(export.keys()))

            export_location_details = (
                self.shares_v2_client.get_share_replica_export_location(
                    primary_replica['id'], export['id'])['export_location']
            )
            self.assertEqual(sorted(el_detail_keys),
                             sorted(export_location_details.keys()))
            for key in el_summary_keys:
                self.assertEqual(export[key], export_location_details[key])

        # For the secondary replica
        actual_replica_exports = (
            self.shares_v2_client.list_share_replica_export_locations(
                replica['id'])['export_locations']
        )

        self.assertEqual(len(expected_replica_exports),
                         len(actual_replica_exports))
        for export in actual_replica_exports:
            self.assertIn(export['path'], expected_replica_export_paths)
            self.assertEqual(replica['replica_state'],
                             export['replica_state'])
            self.assertEqual(replica['availability_zone'],
                             export['availability_zone'])
            self.assertEqual(sorted(el_summary_keys), sorted(export.keys()))

            export_location_details = (
                self.shares_v2_client.get_share_replica_export_location(
                    replica['id'], export['id'])['export_location']
            )
            self.assertEqual(sorted(el_detail_keys),
                             sorted(export_location_details.keys()))
            for key in el_summary_keys:
                self.assertEqual(export[key], export_location_details[key])
