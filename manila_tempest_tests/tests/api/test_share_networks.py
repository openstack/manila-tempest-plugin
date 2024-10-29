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
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareNetworkListMixin(object):

    @decorators.idempotent_id('41c635b1-d9ef-4c05-9100-5e4b0034b523')
    @tc.attr("gate", "smoke", )
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_networks(self):
        listed = self.shares_client.list_share_networks()['share_networks']
        any(self.sn_with_ldap_ss["id"] in sn["id"] for sn in listed)

        # verify keys
        keys = ["name", "id"]
        [self.assertIn(key, sn.keys()) for sn in listed for key in keys]

    @decorators.idempotent_id('18fe9031-cefc-4df3-bbb0-6541f5fda12b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_try_list_share_networks_all_tenants(self):
        listed = self.shares_client.list_share_networks_with_detail(
            params={'all_tenants': 1})['share_networks']
        any(self.sn_with_ldap_ss["id"] in sn["id"] for sn in listed)

        # verify keys
        keys = ["name", "id"]
        [self.assertIn(key, sn.keys()) for sn in listed for key in keys]

    @decorators.idempotent_id('caf6635a-ecb8-4981-9776-11dcfdf3cdbc')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_try_list_share_networks_project_id(self):
        listed = self.shares_client.list_share_networks_with_detail(
            params={'project_id': 'some_project'})['share_networks']
        any(self.sn_with_ldap_ss["id"] in sn["id"] for sn in listed)

        # verify keys
        keys = ["name", "id"]
        [self.assertIn(key, sn.keys()) for sn in listed for key in keys]

    @decorators.idempotent_id('285c7a91-1703-42a5-86c8-2463edde60e2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_networks_with_detail(self):
        listed = self.shares_v2_client.list_share_networks_with_detail(
            )['share_networks']
        any(self.sn_with_ldap_ss["id"] in sn["id"] for sn in listed)

        # verify keys
        keys = [
            "name", "id", "description", "network_type",
            "project_id", "cidr", "ip_version",
            "neutron_net_id", "neutron_subnet_id",
            "created_at", "updated_at", "segmentation_id",
        ]

        # In v2.18 and beyond, we expect gateway.
        if utils.is_microversion_supported('2.18'):
            keys.append('gateway')

        # In v2.20 and beyond, we expect mtu.
        if utils.is_microversion_supported('2.20'):
            keys.append('mtu')

        # In v2.51 and beyond, share-network does not have
        # network parameters anymore.
        if utils.is_microversion_supported('2.51'):
            subnet_keys = [
                "network_type", "cidr", "ip_version", "neutron_net_id",
                "neutron_subnet_id", "segmentation_id", "gateway", "mtu"
            ]
            keys = list(set(keys) - set(subnet_keys))
            keys.append('share_network_subnets')
            for sn in listed:
                [self.assertIn(key, list(subnet.keys())) for key in subnet_keys
                 for subnet in sn['share_network_subnets']]

        [self.assertIn(key, sn.keys()) for sn in listed for key in keys]

    @decorators.idempotent_id('6d13a090-0855-40c0-85b1-424f6878c6ce')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_networks_filter_by_ss(self):
        listed = self.shares_client.list_share_networks_with_detail(
            {'security_service_id': self.ss_ldap['id']})['share_networks']
        self.assertTrue(any(self.sn_with_ldap_ss['id'] == sn['id']
                            for sn in listed))
        for sn in listed:
            ss_list = self.shares_client.list_sec_services_for_share_network(
                sn['id'])['security_services']
            self.assertTrue(any(ss['id'] == self.ss_ldap['id']
                                for ss in ss_list))

    @decorators.idempotent_id('bff1356e-70aa-4bbe-b398-cb4dadd8fcb1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_share_networks_like_filter(self):
        valid_filter_opts = {
            'name': 'sn_with_ldap_ss',
            'description': 'fake',
        }

        listed = self.shares_v2_client.list_share_networks_with_detail(
            {'name~': 'ldap_ss', 'description~': 'fa'})['share_networks']
        self.assertTrue(any(self.sn_with_ldap_ss['id'] == sn['id']
                            for sn in listed))
        for sn in listed:
            self.assertTrue(all(value in sn[key] for key, value in
                                valid_filter_opts.items()))

    @decorators.idempotent_id('27490442-60f8-4514-a10a-194a400b48bb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_networks_all_filter_opts(self):
        valid_filter_opts = {
            'created_before': '2002-10-10',
            'created_since': '2001-01-01',
            'neutron_net_id': '1111',
            'neutron_subnet_id': '2222',
            'network_type': 'vlan',
            'segmentation_id': 1000,
            'cidr': '10.0.0.0/24',
            'ip_version': 4,
            'name': 'sn_with_ldap_ss'
        }

        listed = self.shares_client.list_share_networks_with_detail(
            valid_filter_opts)['share_networks']
        self.assertTrue(any(self.sn_with_ldap_ss['id'] == sn['id']
                            for sn in listed))
        created_before = valid_filter_opts.pop('created_before')
        created_since = valid_filter_opts.pop('created_since')
        for sn in listed:
            self.assertTrue(all(sn[key] == value for key, value in
                                valid_filter_opts.items()))
            self.assertLessEqual(sn['created_at'], created_before)
            self.assertGreaterEqual(sn['created_at'], created_since)


class ShareNetworksTest(base.BaseSharesMixedTest, ShareNetworkListMixin):

    @classmethod
    def resource_setup(cls):
        super(ShareNetworksTest, cls).resource_setup()

        # create share_type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        ss_data = utils.generate_security_service_data()
        cls.ss_ldap = cls.create_security_service(**ss_data)

        cls.data_sn_with_ldap_ss = {
            'name': 'sn_with_ldap_ss',
            'neutron_net_id': '1111',
            'neutron_subnet_id': '2222',
            'created_at': '2002-02-02',
            'updated_at': None,
            'network_type': 'vlan',
            'segmentation_id': 1000,
            'cidr': '10.0.0.0/24',
            'ip_version': 4,
            'description': 'fake description',
        }
        cls.sn_with_ldap_ss = cls.create_share_network(
            cleanup_in_class=True,
            add_security_services=False,
            **cls.data_sn_with_ldap_ss)

        cls.shares_client.add_sec_service_to_share_network(
            cls.sn_with_ldap_ss["id"],
            cls.ss_ldap["id"])

        cls.data_sn_with_kerberos_ss = {
            'name': 'sn_with_kerberos_ss',
            'created_at': '2003-03-03',
            'updated_at': None,
            'neutron_net_id': 'test net id',
            'neutron_subnet_id': 'test subnet id',
            'network_type': 'local',
            'segmentation_id': 2000,
            'cidr': '10.0.0.0/13',
            'ip_version': 6,
            'description': 'fake description',
        }

        cls.ss_kerberos = cls.create_security_service(
            ss_type='kerberos',
            **cls.data_sn_with_ldap_ss)

        cls.sn_with_kerberos_ss = cls.create_share_network(
            cleanup_in_class=True,
            add_security_services=False,
            **cls.data_sn_with_kerberos_ss)

        cls.shares_client.add_sec_service_to_share_network(
            cls.sn_with_kerberos_ss["id"],
            cls.ss_kerberos["id"])

    @decorators.idempotent_id('b998a594-f630-475d-b46f-e4143caf61fb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_delete_share_network(self):
        # generate data for share network
        data = utils.generate_share_network_data()

        # create share network
        created = self.shares_client.create_share_network(
            **data)['share_network']
        self.assertLessEqual(data.items(), created.items())

        # Delete share_network
        self.shares_client.delete_share_network(created["id"])

    @decorators.idempotent_id('55990ec2-37f0-483f-9c67-76fd6f377cc1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_network(self):
        get = self.shares_client.get_share_network(
            self.sn_with_ldap_ss["id"])['share_network']
        self.assertEqual('2002-02-02T00:00:00.000000', get['created_at'])
        data = self.data_sn_with_ldap_ss.copy()
        del data['created_at']
        self.assertLessEqual(data.items(), get.items())

    @decorators.idempotent_id('1837fdd3-8068-4e88-bc50-9224498f84c0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_share_network(self):
        update_data = utils.generate_share_network_data()
        updated = self.shares_client.update_share_network(
            self.sn_with_ldap_ss["id"],
            **update_data)['share_network']
        self.assertLessEqual(update_data.items(), updated.items())

    @decorators.idempotent_id('198a5c08-3aaf-4623-9720-95d33ebe3376')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_update_valid_keys_sh_server_exists(self):
        self.create_share(share_type_id=self.share_type_id,
                          cleanup_in_class=False)
        update_dict = {
            "name": "new_name",
            "description": "new_description",
        }
        updated = self.shares_client.update_share_network(
            self.shares_client.share_network_id,
            **update_dict)['share_network']
        self.assertLessEqual(update_dict.items(), updated.items())

    @decorators.idempotent_id('7595a844-a28e-476c-89f1-4d3193ce9d5b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_recreate_share_network(self):
        # generate data for share network
        data = utils.generate_share_network_data()

        # create share network
        sn1 = self.shares_client.create_share_network(**data)['share_network']
        self.assertLessEqual(data.items(), sn1.items())

        # Delete first share network
        self.shares_client.delete_share_network(sn1["id"])

        # create second share network with same data
        sn2 = self.shares_client.create_share_network(**data)['share_network']
        self.assertLessEqual(data.items(), sn2.items())

        # Delete second share network
        self.shares_client.delete_share_network(sn2["id"])

    @decorators.idempotent_id('be5f4f60-493e-47ea-a5bd-f16dfaa98c5c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_two_share_networks_with_same_net_and_subnet(self):
        # generate data for share network
        data = utils.generate_share_network_data()

        # create first share network
        sn1 = self.create_share_network(**data)
        self.assertLessEqual(data.items(), sn1.items())

        # create second share network
        sn2 = self.create_share_network(**data)
        self.assertLessEqual(data.items(), sn2.items())

    @decorators.idempotent_id('2dbf91da-04ae-4f9f-a7b9-0299c6b2e02c')
    @testtools.skipUnless(CONF.share.create_networks_when_multitenancy_enabled,
                          "Only for setups with network creation.")
    @testtools.skipUnless(CONF.share.multitenancy_enabled,
                          "Only for multitenancy.")
    @testtools.skipUnless(CONF.service_available.neutron, "Only with neutron.")
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_gateway_mtu_neutron_net_id_with_neutron(self):
        self.create_share(share_type_id=self.share_type_id,
                          cleanup_in_class=False)
        share_net_details = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id)['share_network']
        share_net_info = (
            utils.share_network_get_default_subnet(share_net_details)
            if utils.share_network_subnets_are_supported()
            else share_net_details)

        if utils.is_microversion_supported('2.18'):
            subnet_details = self.subnets_client.show_subnet(
                share_net_info['neutron_subnet_id'])
            self.assertEqual(subnet_details['subnet']['gateway_ip'],
                             share_net_info['gateway'])

        if utils.is_microversion_supported('2.20'):
            network_details = self.networks_client.show_network(
                share_net_info['neutron_net_id'])
            self.assertEqual(network_details['network']['mtu'],
                             share_net_info['mtu'])
            self.assertEqual(network_details['network']['id'],
                             share_net_info['neutron_net_id'])
