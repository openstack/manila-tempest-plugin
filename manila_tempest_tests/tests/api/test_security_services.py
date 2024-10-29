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

import ddt
from oslo_log import log
from tempest import config
from tempest.lib import decorators
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion
LOG = log.getLogger(__name__)


@ddt.ddt
class SecurityServiceListMixin(object):

    @decorators.idempotent_id('f6f5657c-a93c-49ed-86e3-b351a92734d5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_security_services(self):
        listed = self.shares_client.list_security_services(
            )['security_services']
        self.assertTrue(any(self.ss_ldap['id'] == ss['id'] for ss in listed))
        self.assertTrue(any(self.ss_kerberos['id'] == ss['id']
                            for ss in listed))

        # verify keys
        keys = ["name", "id", "status", "type", ]
        [self.assertIn(key, s_s.keys()) for s_s in listed for key in keys]

    @decorators.idempotent_id('22b22937-7436-458c-ac22-8ff19feab253')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(*utils.deduplicate(['1.0', '2.42', '2.44', LATEST_MICROVERSION]))
    def test_list_security_services_with_detail(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        with_ou = True if utils.is_microversion_ge(version, '2.44') else False
        if utils.is_microversion_ge(version, '2.0'):
            listed = self.shares_v2_client.list_security_services(
                detailed=True, version=version)['security_services']
        else:
            listed = self.shares_client.list_security_services(
                detailed=True)['security_services']

        self.assertTrue(any(self.ss_ldap['id'] == ss['id'] for ss in listed))
        self.assertTrue(any(self.ss_kerberos['id'] == ss['id']
                            for ss in listed))

        # verify keys
        keys = [
            "name", "id", "status", "description",
            "domain", "server", "dns_ip", "user", "password", "type",
            "created_at", "updated_at", "project_id",
        ]
        [self.assertIn(key, s_s.keys()) for s_s in listed for key in keys]

        for ss in listed:
            self.assertEqual(with_ou, 'ou' in ss.keys())

    @decorators.idempotent_id('88f62835-0aee-4bed-a37f-ffd99430da8a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_list_security_services_filter_by_share_network(self):
        sn = self.shares_client.get_share_network(
            self.shares_client.share_network_id)['share_network']
        fresh_sn = []
        for i in range(2):
            sn = self.create_share_network(
                add_security_services=False,
                neutron_net_id=sn["neutron_net_id"],
                neutron_subnet_id=sn["neutron_subnet_id"])
            fresh_sn.append(sn)

        self.shares_client.add_sec_service_to_share_network(
            fresh_sn[0]["id"], self.ss_ldap["id"])
        self.shares_client.add_sec_service_to_share_network(
            fresh_sn[1]["id"], self.ss_kerberos["id"])

        listed = self.shares_client.list_security_services(
            params={
                'share_network_id': fresh_sn[0]['id']
            })['security_services']
        self.assertEqual(1, len(listed))
        self.assertEqual(self.ss_ldap['id'], listed[0]['id'])

        keys = ["name", "id", "status", "type", ]
        [self.assertIn(key, s_s.keys()) for s_s in listed for key in keys]

    @decorators.idempotent_id('f055faad-dd36-4eed-9b50-61280931dea2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_security_services_detailed_filter_by_ss_attributes(self):
        search_opts = {
            'name': 'ss_ldap',
            'type': 'ldap',
            'user': 'fake_user',
            'server': 'fake_server_1',
            'dns_ip': '1.1.1.1',
            'domain': 'fake_domain_1',
        }
        listed = self.shares_client.list_security_services(
            detailed=True,
            params=search_opts)['security_services']
        self.assertTrue(any(self.ss_ldap['id'] == ss['id'] for ss in listed))
        for ss in listed:
            self.assertTrue(all(ss[key] == value for key, value
                                in search_opts.items()))


@ddt.ddt
class SecurityServicesTest(base.BaseSharesMixedTest,
                           SecurityServiceListMixin):

    @classmethod
    def resource_setup(cls):
        super(SecurityServicesTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

    def setUp(self):
        super(SecurityServicesTest, self).setUp()
        ss_ldap_data = {
            'name': 'ss_ldap',
            'dns_ip': '1.1.1.1',
            'server': 'fake_server_1',
            'domain': 'fake_domain_1',
            'user': 'fake_user',
            'password': 'pass',
        }
        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.44'):
            ss_ldap_data['ou'] = 'OU=fake_unit_1'
        ss_kerberos_data = {
            'name': 'ss_kerberos',
            'dns_ip': '2.2.2.2',
            'server': 'fake_server_2',
            'domain': 'fake_domain_2',
            'user': 'test_user',
            'password': 'word',
        }
        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.44'):
            ss_kerberos_data['ou'] = 'OU=fake_unit_2'
        self.ss_ldap = self.create_security_service('ldap', **ss_ldap_data)
        self.ss_kerberos = self.create_security_service(
            'kerberos', **ss_kerberos_data)

    @decorators.idempotent_id('70927e29-4a6a-431a-bbc1-76bc419e0579')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_delete_security_service(self):
        data = utils.generate_security_service_data()
        self.service_names = ["ldap", "kerberos", "active_directory"]
        for ss_name in self.service_names:
            ss = self.create_security_service(ss_name, **data)
            self.assertLessEqual(data.items(), ss.items())
            self.assertEqual(ss_name, ss["type"])
            self.shares_client.delete_security_service(ss["id"])

    @decorators.idempotent_id('bb052be4-0176-4613-b7d5-e12bef391ddb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(*utils.deduplicate(['1.0', '2.43', '2.44', LATEST_MICROVERSION]))
    def test_get_security_service(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        with_ou = True if utils.is_microversion_ge(version, '2.44') else False
        data = utils.generate_security_service_data(set_ou=with_ou)

        if utils.is_microversion_ge(version, '2.0'):
            ss = self.create_security_service(
                client=self.shares_v2_client, version=version, **data)
            get = self.shares_v2_client.get_security_service(
                ss["id"], version=version)['security_service']
        else:
            ss = self.create_security_service(**data)
            get = self.shares_client.get_security_service(
                ss["id"])['security_service']

        self.assertLessEqual(data.items(), ss.items())
        self.assertEqual(with_ou, 'ou' in ss)
        self.assertLessEqual(data.items(), get.items())
        self.assertEqual(with_ou, 'ou' in get)

    @decorators.idempotent_id('84d47747-13c8-4ab9-9fc4-a43fbb29ad18')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_security_service(self):
        data = utils.generate_security_service_data()
        ss = self.create_security_service(**data)
        self.assertLessEqual(data.items(), ss.items())

        upd_data = utils.generate_security_service_data()
        updated = self.shares_client.update_security_service(
            ss["id"], **upd_data)['security_service']

        get = self.shares_client.get_security_service(
            ss["id"])['security_service']
        self.assertLessEqual(upd_data.items(), updated.items())
        self.assertLessEqual(upd_data.items(), get.items())

        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.44'):
            # update again with ou
            upd_data_ou = utils.generate_security_service_data(set_ou=True)
            updated_ou = self.shares_v2_client.update_security_service(
                ss["id"], **upd_data_ou)['security_service']

            get_ou = self.shares_v2_client.get_security_service(
                ss["id"])['security_service']
            self.assertLessEqual(upd_data_ou.items(), updated_ou.items())
            self.assertLessEqual(upd_data_ou.items(), get_ou.items())

    @decorators.idempotent_id('c3c04992-da11-4677-9098-eff3f4231a4b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_try_update_valid_keys_sh_server_exists(self):
        ss_data = utils.generate_security_service_data()
        ss = self.create_security_service(**ss_data)

        sn = self.shares_client.get_share_network(
            self.shares_client.share_network_id)['share_network']
        fresh_sn = self.create_share_network(
            add_security_services=False,
            neutron_net_id=sn["neutron_net_id"],
            neutron_subnet_id=sn["neutron_subnet_id"])

        self.shares_client.add_sec_service_to_share_network(
            fresh_sn["id"], ss["id"])

        # Security service with fake data is used, so if we use backend driver
        # that fails on wrong data, we expect error here.
        # We require any share that uses our share-network.
        try:
            self.create_share(share_type_id=self.share_type_id,
                              share_network_id=fresh_sn["id"],
                              cleanup_in_class=False)
        except Exception as e:
            # we do wait for either 'error' or 'available' status because
            # it is the only available statuses for proper deletion.
            LOG.warning("Caught exception. It is expected in case backend "
                        "fails having security-service with improper data "
                        "that leads to share-server creation error. "
                        "%s", str(e))

        update_data = {
            "name": "name",
            "description": "new_description",
        }
        updated = self.shares_client.update_security_service(
            ss["id"], **update_data)['security_service']
        self.assertLessEqual(update_data.items(), updated.items())

    @decorators.idempotent_id('8d9af272-df89-470d-9ff8-92ba774c9fff')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_security_services_filter_by_invalid_opt(self):
        listed = self.shares_client.list_security_services(
            params={'fake_opt': 'some_value'})['security_services']
        self.assertTrue(any(self.ss_ldap['id'] == ss['id'] for ss in listed))
        self.assertTrue(any(self.ss_kerberos['id'] == ss['id']
                            for ss in listed))

    @decorators.idempotent_id('d501710e-4710-4c13-a373-75ed6ababb13')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_try_list_security_services_all_tenants_ignored(self):
        alt_security_service = self.create_security_service(
            **utils.generate_security_service_data(),
            client=self.alt_shares_v2_client)
        alt_security_service_id = alt_security_service['id']
        sec_service_list = self.shares_client.list_security_services(
            params={'all_tenants': 1})['security_services']
        sec_service_ids = [ss['id'] for ss in sec_service_list]
        self.assertTrue(
            any(self.ss_ldap['id'] == ss['id'] for ss in sec_service_list))
        self.assertTrue(
            any(self.ss_kerberos['id'] == ss['id'] for ss in sec_service_list))
        self.assertNotIn(alt_security_service_id, sec_service_ids)
