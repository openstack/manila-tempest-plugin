# Copyright 2019 NetApp Inc.
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
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class ShareNetworkSubnetsTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareNetworkSubnetsTest, cls).skip_checks()
        utils.check_skip_if_microversion_lt("2.51")

    @classmethod
    def resource_setup(cls):
        super(ShareNetworkSubnetsTest, cls).resource_setup()
        # create share_type
        cls.extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        cls.share_type = cls._create_share_type(specs=cls.extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share_network
        cls.share_network = cls.create_share_network()
        cls.share_network_id = cls.share_network['id']

    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_delete_subnet(self):
        share_network = self.shares_v2_client.create_share_network()
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )
        default_subnet = share_network['share_network_subnets'][0]

        az = self.shares_v2_client.list_availability_zones()[0]
        az_name = az['name']

        # Generate subnet data
        data = self.generate_subnet_data()
        data['share_network_id'] = share_network['id']
        data['availability_zone'] = az_name

        # create a new share network subnet
        created = self.create_share_network_subnet(**data)
        data['share_network_name'] = share_network['name']
        # verify keys
        keys = [
            "share_network_name", "id", "network_type", "cidr",
            "ip_version", "neutron_net_id", "neutron_subnet_id", "created_at",
            "updated_at", "segmentation_id", "availability_zone", "gateway",
            "share_network_id", "mtu"
        ]

        # Default subnet was created during share network creation
        self.assertIsNone(default_subnet['availability_zone'])
        # Match new subnet content
        self.assertDictContainsSubset(data, created)

        self.assertEqual(sorted(keys), sorted(list(created.keys())))

        # Delete the subnets
        self.shares_v2_client.delete_subnet(share_network['id'], created['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_share_network_subnet(self):
        share_network = self.create_share_network()
        az = self.shares_v2_client.list_availability_zones()[0]
        az_name = az['name']

        # Generate subnet data
        data = self.generate_subnet_data()
        data['share_network_id'] = share_network['id']
        data['availability_zone'] = az_name

        # Create the share network subnet
        created = self.create_share_network_subnet(**data)

        # Shows the share network subnet
        shown = self.shares_v2_client.get_subnet(created['id'],
                                                 share_network['id'])

        # Asserts
        self.assertDictContainsSubset(data, shown)

        # Deletes the created subnet
        self.shares_v2_client.delete_subnet(share_network['id'],
                                            created['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    def test_create_share_on_subnet_with_availability_zone(self):
        compatible_azs = self.get_availability_zones_matching_share_type(
            self.share_type)
        if len(compatible_azs) < 2:
            msg = ("This test needs at least two compatible storage "
                   "availability zones.")
            raise self.skipException(msg)

        original_share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id
        )
        share_net_info = (
            utils.share_network_get_default_subnet(original_share_network))
        share_network = self.create_share_network(
            neutron_net_id=share_net_info['neutron_net_id'],
            neutron_subnet_id=share_net_info['neutron_subnet_id'],
        )
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )
        default_subnet = share_network['share_network_subnets'][0]
        availability_zone = compatible_azs[0]

        data = {
            "neutron_net_id": share_net_info['neutron_net_id'],
            "neutron_subnet_id": share_net_info['neutron_subnet_id'],
            'share_network_id': share_network['id'],
            'availability_zone': availability_zone,
        }
        # Create a new share network subnet
        subnet = self.create_share_network_subnet(**data)

        # Create a new share in the select availability zone
        # The 'status' of the share returned by the create API must be
        share = self.create_share(
            share_type_id=self.share_type_id,
            share_network_id=share_network['id'],
            availability_zone=availability_zone)
        # Set and have value either 'creating' or
        # 'available' (if share creation is really fast as in
        # case of Dummy driver).
        self.assertIn(share['status'], ('creating', 'available'))

        share = self.admin_shares_v2_client.get_share(share['id'])
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )

        # Default subnet was created during share network creation
        self.assertIsNone(default_subnet['availability_zone'])
        # Match new subnet content
        self.assertDictContainsSubset(data, subnet)
        # Match share server subnet
        self.assertEqual(subnet['id'],
                         share_server['share_network_subnet_id'])
        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete the subnets
        self.shares_v2_client.delete_subnet(share_network['id'], subnet['id'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    @ddt.data(True, False)
    def test_create_share_on_share_network_with_multiple_subnets(
            self, create_share_with_az):
        compatible_azs = self.get_availability_zones_matching_share_type(
            self.share_type)
        if len(compatible_azs) < 2:
            msg = ("This test needs at least two compatible storage "
                   "availability zones.")
            raise self.skipException(msg)

        original_share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id
        )
        share_net_info = (
            utils.share_network_get_default_subnet(original_share_network))
        share_network = self.create_share_network(
            neutron_net_id=share_net_info['neutron_net_id'],
            neutron_subnet_id=share_net_info['neutron_subnet_id'],
        )
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )
        default_subnet = share_network['share_network_subnets'][0]
        # Save one availability zone to remain associated with default subnet
        destination_az = compatible_azs.pop()
        if not create_share_with_az:
            destination_az = None

        new_subnets = []
        data = {
            "neutron_net_id": share_net_info['neutron_net_id'],
            "neutron_subnet_id": share_net_info['neutron_subnet_id'],
            'share_network_id': share_network['id'],
        }
        for availability_zone in compatible_azs:
            # update availability zone
            data['availability_zone'] = availability_zone
            # create a new share network subnet
            subnet = self.create_share_network_subnet(**data)
            new_subnets.append(subnet)

        # Create a new share in the selected availability zone
        share = self.create_share(
            share_type_id=self.share_type_id,
            share_network_id=share_network['id'],
            availability_zone=destination_az)
        # The 'status' of the share returned by the create API must be
        # set and have value either 'creating' or 'available' (if share
        # creation is really fast as in case of Dummy driver).
        self.assertIn(share['status'], ('creating', 'available'))

        share = self.admin_shares_v2_client.get_share(share['id'])
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )
        # If no availability zone was provided during share creation, it is
        # expected that the Scheduler selects one of the compatible backends to
        # place the share. The destination availability zone may or may not
        # have an specific share network subnet.
        expected_subnet_id = (
            next((subnet['id'] for subnet in new_subnets
                 if subnet['availability_zone'] == share['availability_zone']),
                 default_subnet['id']))
        # Default subnet was created during share network creation
        self.assertIsNone(default_subnet['availability_zone'])
        # Match share server subnet
        self.assertEqual(expected_subnet_id,
                         share_server['share_network_subnet_id'])
        if create_share_with_az:
            self.assertEqual(destination_az,
                             share['availability_zone'])
        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete the subnets
        for subnet in new_subnets:
            self.shares_v2_client.delete_subnet(share_network['id'],
                                                subnet['id'])
