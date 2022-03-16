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
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareServerMultipleSubNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareServerMultipleSubNegativeTest, cls).skip_checks()
        if not CONF.share.multitenancy_enabled:
            raise cls.skipException('Multitenancy tests are disabled.')
        utils.check_skip_if_microversion_not_supported("2.70")

    @classmethod
    def resource_setup(cls):
        super(ShareServerMultipleSubNegativeTest, cls).resource_setup()
        cls.share_network = cls.alt_shares_v2_client.get_share_network(
            cls.alt_shares_v2_client.share_network_id)['share_network']

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @decorators.idempotent_id('1e2a9415-b02f-4c02-812d-bedc361f92ce')
    def test_create_share_multiple_subnets_to_unsupported_backend(self):
        extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
            'share_server_multiple_subnet_support': False
        }
        share_type = self.create_share_type(extra_specs=extra_specs)
        pools = self.get_pools_matching_share_type(
            share_type, client=self.admin_shares_v2_client)
        zones = self.get_availability_zones_matching_share_type(
            share_type)
        if not pools or not zones:
            raise self.skipException("At least one backend that supports "
                                     "adding multiple subnets into a share "
                                     "network is needed for this test.")
        extra_specs = {'pool_name': pools[0]['pool'],
                       'availability_zone': zones[0]}
        self.admin_shares_v2_client.update_share_type_extra_specs(
            share_type['id'], extra_specs)

        share_network_id = self.create_share_network(
            cleanup_in_class=True)["id"]
        default_subnet = utils.share_network_get_default_subnet(
            self.share_network)
        subnet_data = {
            'neutron_net_id': default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': default_subnet.get('neutron_subnet_id'),
            'share_network_id': share_network_id,
            'availability_zone': zones[0],
            'cleanup_in_class': False
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.shares_v2_client.delete_subnet,
                        share_network_id, subnet1['id'])
        subnet2 = self.create_share_network_subnet(**subnet_data)
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.shares_v2_client.delete_subnet,
                        share_network_id, subnet2['id'])
        self.assertRaises(
            share_exceptions.ShareBuildErrorException,
            self.create_share,
            share_type_id=share_type['id'],
            share_network_id=share_network_id,
            availability_zone=zones[0],
            cleanup_in_class=False
        )
