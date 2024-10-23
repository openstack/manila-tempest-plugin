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
from tempest.lib import decorators
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
        utils.check_skip_if_microversion_not_supported("2.51")

    @classmethod
    def resource_setup(cls):
        super(ShareNetworkSubnetsTest, cls).resource_setup()
        # create share_type
        cls.extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        cls.share_type = cls.create_share_type(extra_specs=cls.extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share_network
        cls.share_network = cls.create_share_network()
        cls.share_network_id = cls.share_network['id']

    @decorators.idempotent_id('3e1e4da7-049f-404e-8673-142695a9a785')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_delete_subnet(self):
        share_network = self.shares_v2_client.create_share_network(
            )['share_network']
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )['share_network']
        default_subnet = share_network['share_network_subnets'][0]

        az = self.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        az_name = az['name']

        # Generate subnet data
        data = utils.generate_subnet_data()
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
        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.78'):
            keys.extend(['metadata'])

        # Default subnet was created during share network creation
        self.assertIsNone(default_subnet['availability_zone'])
        # Match new subnet content
        self.assertLessEqual(data.items(), created.items())

        self.assertEqual(sorted(keys), sorted(list(created.keys())))

        # Delete the subnets
        self.shares_v2_client.delete_subnet(share_network['id'], created['id'])

    @decorators.idempotent_id('51c6836a-c6d2-4b80-a992-cf91f9a4332b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_share_network_subnet(self):
        share_network = self.create_share_network()
        az = self.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        az_name = az['name']

        # Generate subnet data
        data = utils.generate_subnet_data()
        data['share_network_id'] = share_network['id']
        data['availability_zone'] = az_name

        # Create the share network subnet
        created = self.create_share_network_subnet(**data)

        # Shows the share network subnet
        shown = self.shares_v2_client.get_subnet(
            created['id'], share_network['id'])['share_network_subnet']

        # Asserts
        self.assertLessEqual(data.items(), shown.items())

        # Deletes the created subnet
        self.shares_v2_client.delete_subnet(share_network['id'],
                                            created['id'])

    @decorators.idempotent_id('89ed6115-eb1d-4a7e-a0a3-9b4a239fadc1')
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
        check_multiple_subnet = utils.is_microversion_ge(
            CONF.share.max_api_microversion, '2.70')

        original_share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id
        )['share_network']
        share_net_info = (
            utils.share_network_get_default_subnet(original_share_network))
        share_network = self.create_share_network(
            neutron_net_id=share_net_info['neutron_net_id'],
            neutron_subnet_id=share_net_info['neutron_subnet_id'],
        )
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )['share_network']
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

        share = self.admin_shares_v2_client.get_share(share['id'])['share']
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )['share_server']

        # Default subnet was created during share network creation
        self.assertIsNone(default_subnet['availability_zone'])
        # Match new subnet content
        self.assertDictContainsSubset(data, subnet)
        # Match share server subnet
        if check_multiple_subnet:
            self.assertIn(subnet['id'],
                          share_server['share_network_subnet_ids'])
        else:
            self.assertIn(subnet['id'],
                          share_server['share_network_subnet_id'])
        # Delete share
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete the subnets
        self.shares_v2_client.delete_subnet(share_network['id'], subnet['id'])

    @decorators.idempotent_id('043fbe02-466d-4344-8e2f-f02cb65132cb')
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
        check_multiple_subnet = utils.is_microversion_ge(
            CONF.share.max_api_microversion, '2.70')

        original_share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id)['share_network']
        share_net_info = (
            utils.share_network_get_default_subnet(original_share_network))
        share_network = self.create_share_network(
            neutron_net_id=share_net_info['neutron_net_id'],
            neutron_subnet_id=share_net_info['neutron_subnet_id'],
        )
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )['share_network']
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

        share = self.admin_shares_v2_client.get_share(share['id'])['share']
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )['share_server']
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
        if not check_multiple_subnet:
            self.assertEqual(
                expected_subnet_id, share_server['share_network_subnet_id'])
        else:
            self.assertIn(
                expected_subnet_id, share_server['share_network_subnet_ids'])
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
