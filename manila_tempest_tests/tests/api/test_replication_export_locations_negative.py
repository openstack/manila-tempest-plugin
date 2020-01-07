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


class ReplicationExportLocationsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ReplicationExportLocationsNegativeTest, cls).skip_checks()
        if not CONF.share.run_replication_tests:
            raise cls.skipException('Replication tests are disabled.')

    @classmethod
    def resource_setup(cls):
        super(ReplicationExportLocationsNegativeTest, cls).resource_setup()
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
        share_type = cls.create_share_type(
            name,
            extra_specs=cls.extra_specs,
            client=cls.admin_client)
        cls.share_type = share_type["share_type"]
        cls.sn_id = None
        if cls.multitenancy_enabled:
            cls.share_network = cls.shares_v2_client.get_share_network(
                cls.shares_v2_client.share_network_id)
            cls.sn_id = cls.share_network['id']
        cls.zones = cls.get_availability_zones_matching_share_type(
            cls.share_type)
        cls.share_zone = cls.zones[0]
        cls.replica_zone = cls.zones[-1]

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.47')
    @testtools.skipUnless(
        CONF.share.backend_replication_type in
        (constants.REPLICATION_STYLE_READABLE, constants.REPLICATION_STYLE_DR),
        'Test is not appropriate for writable replication style.')
    def test_get_share_export_location_for_secondary_replica(self):
        """Is NotFound raised with share el API for non-active replicas"""
        share = self.create_share(share_type_id=self.share_type['id'],
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        replica = self.create_share_replica(share['id'], self.replica_zone)
        replica_exports = (
            self.shares_v2_client.list_share_replica_export_locations(
                replica['id'])
        )

        for export in replica_exports:
            self.assertRaises(lib_exc.NotFound,
                              self.shares_v2_client.get_share_export_location,
                              share['id'], export['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.47')
    def test_get_replica_export_location_for_non_replica(self):
        """Is NotFound raised for non-replica share instances"""
        # Create a share type with no support for replication
        share_type = self._create_share_type()
        share = self.create_share(share_type_id=share_type['id'],
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        share_instances = self.admin_client.get_instances_of_share(share['id'])
        for instance in share_instances:
            self.assertRaises(
                lib_exc.NotFound,
                self.shares_v2_client.list_share_replica_export_locations,
                instance['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported('2.47')
    def test_list_replica_export_locations_for_invalid_replica(self):
        """Is NotFound raised for invalid replica ID"""
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.list_share_replica_export_locations,
            'invalid-replica-id')

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.47')
    def test_get_replica_export_location_for_invalid_export_id(self):
        """Is NotFound raised for invalid replica export location ID"""
        share = self.create_share(share_type_id=self.share_type['id'],
                                  availability_zone=self.share_zone,
                                  share_network_id=self.sn_id)
        replica = self.create_share_replica(share['id'], self.replica_zone)
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.get_share_replica_export_location,
            replica['id'], 'invalid-export-location-id')
