# Copyright 2014 Mirantis Inc.
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
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareNetworksNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(ShareNetworksNegativeTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

    @decorators.idempotent_id('66289664-bf01-40dd-a76d-fd2c953bbceb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_share_network_without_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_share_network, "")

    @decorators.idempotent_id('80397850-2f64-48b3-b19b-79c4ac0bd58f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_share_network_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_share_network, "wrong_id")

    @decorators.idempotent_id('fe6ac194-5003-404c-b372-7515a58ff969')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_share_network_without_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_share_network, "")

    @decorators.idempotent_id('7e22e8b9-a1ce-480c-89b3-b4edd807285a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_share_network_with_wrong_type(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_share_network, "wrong_id")

    @decorators.idempotent_id('a7c55dbe-c23e-403f-b8aa-4aa1128f32a4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_nonexistant_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.update_share_network,
                          "wrong_id", name="name")

    @decorators.idempotent_id('984349ca-df7d-4f85-a45f-948189debb65')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_share_network_with_empty_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.update_share_network,
                          "", name="name")

    @decorators.idempotent_id('211b64b4-4c2b-4b6b-b011-725f40a37b03')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_try_update_invalid_keys_sh_server_exists(self):
        self.create_share(share_type_id=self.share_type_id,
                          cleanup_in_class=False)

        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.update_share_network,
                          self.shares_client.share_network_id,
                          neutron_net_id="new_net_id")

    @decorators.idempotent_id('9166b81c-d6ab-4592-bcf7-9410250e30dd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_deleted_share_network(self):
        data = self.generate_share_network_data()
        sn = self.create_share_network(**data)
        self.assertDictContainsSubset(data, sn)

        self.shares_client.delete_share_network(sn["id"])

        # try get deleted share network entity
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_security_service,
                          sn["id"])

    @decorators.idempotent_id('0d104b72-aab5-48b5-87f8-847d2155faa9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_share_networks_wrong_created_since_value(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_client.list_share_networks_with_detail,
            params={'created_since': '2014-10-23T08:31:58.000000'})

    @decorators.idempotent_id('c96dacaf-4cea-4fe9-bbd7-c9b1001f5495')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_share_networks_wrong_created_before_value(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_client.list_share_networks_with_detail,
            params={'created_before': '2014-10-23T08:31:58.000000'})

    @decorators.idempotent_id('6e4912fd-ae85-4a43-81e8-e5b340099b64')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(not CONF.share.multitenancy_enabled,
                      'Can run only with drivers that do handle share servers '
                      'creation. Skipping.')
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    def test_try_delete_share_network_with_existing_shares(self):
        # Get valid network data for successful share creation
        share_network = self.shares_client.get_share_network(
            self.shares_client.share_network_id)['share_network']
        new_sn = self.create_share_network(
            neutron_net_id=share_network['neutron_net_id'],
            neutron_subnet_id=share_network['neutron_subnet_id'],
            cleanup_in_class=False)

        # Create share with share network
        self.create_share(share_type_id=self.share_type_id,
                          share_network_id=new_sn['id'],
                          cleanup_in_class=False)

        # Try delete share network
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_client.delete_share_network, new_sn['id'])

    @decorators.idempotent_id('4e71de31-1064-40da-948d-a72063fbd647')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.35")
    def test_list_shares_with_like_filter_not_exist(self):
        filters = {
            'name~': 'fake_not_exist',
            'description~': 'fake_not_exist',
        }
        share_networks = (
            self.shares_v2_client.list_share_networks_with_detail(
                params=filters)['share_networks'])

        self.assertEqual(0, len(share_networks))

    @utils.skip_if_microversion_not_supported("2.51")
    @decorators.idempotent_id('8a995305-ede9-4002-a9cd-f24ff4d71f63')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share_network_contains_more_than_one_subnet(self):
        share_network = self.create_share_network()
        az = self.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        az_name = az['name']

        # Generate subnet data
        data = self.generate_subnet_data()
        data['share_network_id'] = share_network['id']
        data['availability_zone'] = az_name

        # create share network
        subnet = self.create_share_network_subnet(**data)

        # Try to delete the share network
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_client.delete_share_network,
            share_network['id']
        )

        self.shares_v2_client.delete_subnet(share_network['id'], subnet['id'])
        share_network = self.shares_v2_client.get_share_network(
            share_network['id'])['share_network']
        default_subnet = share_network['share_network_subnets'][0]
        self.assertIsNone(default_subnet['availability_zone'])

    @utils.skip_if_microversion_not_supported("2.51")
    @decorators.idempotent_id('d84c3c5c-5913-42d4-9a66-0d5a78295adb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_share_network_inexistent_az(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_share_network,
            availability_zone='inexistent-availability-zone',
        )

    @utils.skip_if_microversion_not_supported("2.70")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @decorators.idempotent_id('f6f47c64-6821-4d4a-aa7d-3b0244158197')
    def test_check_add_share_network_subnet_share_network_not_found(self):
        data = self.generate_subnet_data()
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.subnet_create_check,
                          'fake_inexistent_id',
                          **data)

    @utils.skip_if_microversion_not_supported("2.70")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @decorators.idempotent_id('d9a487fb-6638-4f93-8b69-3e1a85bfbc7d')
    def test_check_add_share_network_subnet_az_not_found(self):
        share_network = self.create_share_network()
        data = {'availability_zone': 'non-existent-az'}

        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.subnet_create_check,
                          share_network['id'], **data)
