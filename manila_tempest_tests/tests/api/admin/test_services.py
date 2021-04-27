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
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


@ddt.ddt
class ServicesAdminTest(base.BaseSharesAdminTest):

    def setUp(self):
        super(ServicesAdminTest, self).setUp()
        self.services = self.shares_client.list_services()['services']

    @decorators.idempotent_id('74cd12ab-a1f5-40fb-9110-d9035b4b20c5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_list_services(self, client_name):
        services = getattr(self, client_name).list_services()['services']
        self.assertNotEqual(0, len(services))

        for service in services:
            self.assertIsNotNone(service['id'])

    @decorators.idempotent_id('e80f4b89-7280-47eb-9cbf-01a09e04c2d8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_get_services_by_host_name(self, client_name):
        host = self.services[0]["host"]
        params = {"host": host}
        services = getattr(self, client_name).list_services(params)['services']
        self.assertNotEqual(0, len(services))
        for service in services:
            self.assertEqual(host, service["host"])

    @decorators.idempotent_id('1dd4d799-b900-4476-9e51-ad9db6ee4435')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_get_services_by_binary_name(self, client_name):
        binary = self.services[0]["binary"]
        params = {"binary": binary, }
        services = getattr(self, client_name).list_services(params)['services']
        self.assertNotEqual(0, len(services))
        for service in services:
            self.assertEqual(binary, service["binary"])

    @decorators.idempotent_id('d12ea678-025f-46b4-95c5-3a03b3e440d7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_get_services_by_availability_zone(self, client_name):
        zone = self.services[0]["zone"]
        params = {"zone": zone, }
        services = getattr(self, client_name).list_services(params)['services']
        self.assertNotEqual(0, len(services))
        for service in services:
            self.assertEqual(zone, service["zone"])

    @decorators.idempotent_id('e82921a7-6c98-4c9c-a47b-34a0badc3b59')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_get_services_by_status(self, client_name):
        status = self.services[0]["status"]
        params = {"status": status, }
        services = getattr(self, client_name).list_services(params)['services']
        self.assertNotEqual(0, len(services))
        for service in services:
            self.assertEqual(status, service["status"])

    @decorators.idempotent_id('c30234f0-1331-4560-93a7-cbda7d00eb53')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_get_services_by_state(self, client_name):
        state = self.services[0]["state"]
        params = {"state": state, }
        services = getattr(self, client_name).list_services(params)['services']
        self.assertNotEqual(0, len(services))
        for service in services:
            self.assertEqual(state, service["state"])

    @decorators.idempotent_id('b77c4bc4-57d5-4181-9e95-e230ab682b32')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_get_services_by_all_filters(self, client_name):
        params = {
            "host": self.services[0]["host"],
            "binary": self.services[0]["binary"],
            "zone": self.services[0]["zone"],
            "status": self.services[0]["status"],
            "state": self.services[0]["state"],
        }
        services = getattr(self, client_name).list_services(params)['services']
        self.assertNotEqual(0, len(services))
        for service in services:
            self.assertEqual(params["host"], service["host"])
            self.assertEqual(params["binary"], service["binary"])
            self.assertEqual(params["zone"], service["zone"])
            self.assertEqual(params["status"], service["status"])
            self.assertEqual(params["state"], service["state"])
