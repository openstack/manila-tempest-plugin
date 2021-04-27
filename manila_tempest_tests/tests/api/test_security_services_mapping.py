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

from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


class SecurityServicesMappingTest(base.BaseSharesTest):

    @classmethod
    def resource_setup(cls):
        super(SecurityServicesMappingTest, cls).resource_setup()
        cls.cl = cls.shares_client

    def setUp(self):
        super(SecurityServicesMappingTest, self).setUp()

        # create share network
        data = self.generate_share_network_data()

        self.sn = self.create_share_network(client=self.cl,
                                            add_security_services=False,
                                            **data)
        self.assertDictContainsSubset(data, self.sn)

        # create security service
        data = self.generate_security_service_data()

        self.ss = self.create_security_service(client=self.cl, **data)
        self.assertDictContainsSubset(data, self.ss)

        # Add security service to share network
        self.cl.add_sec_service_to_share_network(self.sn["id"], self.ss["id"])

    @decorators.idempotent_id('e8c5b4d5-7ad2-4aa7-bab0-b454a2e150e9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_map_ss_to_sn_and_list(self):

        # List security services for share network
        ls = self.cl.list_sec_services_for_share_network(
            self.sn["id"])['security_services']
        self.assertEqual(1, len(ls))
        for key in ["status", "id", "name"]:
            self.assertIn(self.ss[key], ls[0][key])

    @decorators.idempotent_id('9dd352b2-6d47-4cab-aa61-52d8081f67a2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_map_ss_to_sn_and_delete(self):

        # Remove security service from share network
        self.cl.remove_sec_service_from_share_network(
            self.sn["id"], self.ss["id"])

    @decorators.idempotent_id('2b0bd5cc-eb35-430f-acfd-f80a2e467667')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_remap_ss_to_sn(self):

        # Remove security service from share network
        self.cl.remove_sec_service_from_share_network(
            self.sn["id"], self.ss["id"])

        # Add security service to share network again
        self.cl.add_sec_service_to_share_network(self.sn["id"], self.ss["id"])
