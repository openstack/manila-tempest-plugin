# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.api import test_share_networks
from manila_tempest_tests import utils


class ShareNetworkAdminTest(base.BaseSharesMixedTest,
                            test_share_networks.ShareNetworkListMixin):

    @classmethod
    def resource_setup(cls):
        super(ShareNetworkAdminTest, cls).resource_setup()
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

        cls.ss_kerberos = cls.alt_shares_v2_client.create_security_service(
            ss_type='kerberos',
            **cls.data_sn_with_ldap_ss)['security_service']

        cls.sn_with_kerberos_ss = (
            cls.alt_shares_v2_client.create_share_network(
                cleanup_in_class=True,
                add_security_services=False,
                **cls.data_sn_with_kerberos_ss)['share_network']
        )

        cls.alt_shares_v2_client.add_sec_service_to_share_network(
            cls.sn_with_kerberos_ss["id"],
            cls.ss_kerberos["id"])

    @decorators.idempotent_id('983fb22d-3057-402f-8988-62ce41a557fb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_networks_all_tenants(self):
        listed = self.admin_shares_v2_client.list_share_networks_with_detail(
            {'all_tenants': 1})['share_networks']
        self.assertTrue(any(self.sn_with_ldap_ss['id'] == sn['id']
                            for sn in listed))
        self.assertTrue(any(self.sn_with_kerberos_ss['id'] == sn['id']
                            for sn in listed))

    @decorators.idempotent_id('36c26b6b-8984-4255-959b-74f6ef46c37b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_networks_filter_by_project_id(self):
        listed = self.admin_shares_v2_client.list_share_networks_with_detail(
            {
                'project_id': self.sn_with_kerberos_ss['project_id']
            })['share_networks']
        self.assertTrue(any(self.sn_with_kerberos_ss['id'] == sn['id']
                            for sn in listed))
        self.assertTrue(all(self.sn_with_kerberos_ss['project_id'] ==
                            sn['project_id'] for sn in listed))
