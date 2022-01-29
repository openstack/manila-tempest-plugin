# Copyright 2022 NetApp Inc.
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
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareServerMultipleSubnetTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareServerMultipleSubnetTest, cls).skip_checks()
        if not CONF.share.multitenancy_enabled:
            raise cls.skipException('Multitenancy tests are disabled.')
        if not CONF.share.run_share_server_multiple_subnet_tests and not (
                CONF.share.run_network_allocation_update_tests):
            raise cls.skipException(
                'Share server multiple subnets and network allocation '
                'update tests are disabled.')
        if CONF.share.share_network_id != "":
            raise cls.skipException(
                'These tests are not suitable for pre-existing '
                'share_network.')
        utils.check_skip_if_microversion_not_supported("2.70")

    @classmethod
    def resource_setup(cls):
        super(ShareServerMultipleSubnetTest, cls).resource_setup()
        cls.extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        if CONF.share.run_share_server_multiple_subnet_tests:
            cls.extra_specs['share_server_multiple_subnet_support'] = True
        if CONF.share.run_network_allocation_update_tests:
            cls.extra_specs['network_allocation_update_support'] = True
        share_type = cls.create_share_type(extra_specs=cls.extra_specs)
        cls.share_type_id = share_type['id']

        cls.zones = cls.get_availability_zones_matching_share_type(
            share_type)
        if len(cls.zones) == 0:
            msg = ("These tests need at least one compatible "
                   "availability zone.")
            raise cls.skipException(msg)

        cls.share_network = cls.alt_shares_v2_client.get_share_network(
            cls.alt_shares_v2_client.share_network_id)['share_network']
        cls.default_subnet = utils.share_network_get_default_subnet(
            cls.share_network)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        not CONF.share.run_share_server_multiple_subnet_tests,
        "Share network multiple subnets tests are disabled.")
    @decorators.idempotent_id('5600bd52-ecb4-47d3-a4e8-3e6565cb0b80')
    def test_create_share_on_multiple_subnets_same_az(self):
        share_network_id = self.create_share_network(
            cleanup_in_class=False)["id"]
        subnet_data = {
            'neutron_net_id': self.default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': self.default_subnet.get('neutron_subnet_id'),
            'share_network_id': share_network_id,
            'availability_zone': self.zones[0],
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)
        subnet2 = self.create_share_network_subnet(**subnet_data)

        share = self.create_share(
            share_type_id=self.share_type_id,
            share_network_id=share_network_id,
            availability_zone=self.zones[0])
        self.assertIn(share['status'], ('creating', 'available'))

        share = self.admin_shares_v2_client.get_share(share['id'])['share']
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )['share_server']
        self.assertIn(subnet1['id'],
                      share_server['share_network_subnet_ids'])
        self.assertIn(subnet2['id'],
                      share_server['share_network_subnet_ids'])

        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete the subnets
        self.shares_v2_client.delete_subnet(share_network_id, subnet1['id'])
        self.shares_v2_client.delete_subnet(share_network_id, subnet2['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        not CONF.share.run_network_allocation_update_tests,
        "Share server network allocation update are disabled.")
    @decorators.idempotent_id('2a9debd5-47a3-42cc-823b-2b9de435a5e4')
    def test_create_share_with_network_allocation_update(self):
        share_network_id = self.create_share_network(
            cleanup_in_class=False)["id"]
        subnet_data = {
            'neutron_net_id': self.default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': self.default_subnet.get('neutron_subnet_id'),
            'share_network_id': share_network_id,
            'availability_zone': self.zones[0],
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)

        share = self.create_share(
            share_type_id=self.share_type_id,
            share_network_id=share_network_id,
            availability_zone=self.zones[0])
        self.assertIn(share['status'], ('creating', 'available'))
        share = self.admin_shares_v2_client.get_share(share['id'])['share']

        waiters.wait_for_subnet_create_check(
            self.shares_v2_client, share_network_id,
            neutron_net_id=subnet_data['neutron_net_id'],
            neutron_subnet_id=subnet_data['neutron_subnet_id'],
            availability_zone=self.zones[0])
        subnet2 = self.create_share_network_subnet(**subnet_data)

        waiters.wait_for_resource_status(
            self.admin_shares_v2_client, share['share_server_id'],
            constants.SERVER_STATE_ACTIVE,
            resource_name="share_server",
            status_attr="status")
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )['share_server']

        self.assertIn(subnet1['id'],
                      share_server['share_network_subnet_ids'])
        self.assertIn(subnet2['id'],
                      share_server['share_network_subnet_ids'])

        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete subnets
        self.shares_v2_client.delete_subnet(share_network_id, subnet1['id'])
        self.shares_v2_client.delete_subnet(share_network_id, subnet2['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        not CONF.share.run_network_allocation_update_tests,
        "Share server network allocation update are disabled.")
    @decorators.idempotent_id('2624f9a7-660b-4f91-89b8-c026b3bb8d1f')
    def test_share_network_subnet_create_check(self):
        """The share network subnet create check compatibility test."""

        share_network_id = self.create_share_network(
            cleanup_in_class=False)["id"]
        subnet_data = {
            'neutron_net_id': self.default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': self.default_subnet.get('neutron_subnet_id'),
            'share_network_id': share_network_id,
            'availability_zone': self.zones[0],
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)

        share = self.create_share(
            share_type_id=self.share_type_id,
            share_network_id=share_network_id,
            availability_zone=self.zones[0]
        )
        self.assertIn(share['status'], ('creating', 'available'))
        waiters.wait_for_subnet_create_check(
            self.shares_v2_client, share_network_id,
            neutron_net_id=subnet_data['neutron_net_id'],
            neutron_subnet_id=subnet_data['neutron_subnet_id'],
            availability_zone=self.zones[0])

        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete subnets
        self.shares_v2_client.delete_subnet(share_network_id, subnet1['id'])
