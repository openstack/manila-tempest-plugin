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
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


@ddt.ddt
class ServicesAdminNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(ServicesAdminNegativeTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.member_client = cls.shares_v2_client

    @decorators.idempotent_id('59ab1a7d-817d-42e5-a1b9-adfc2912e08c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_services_with_non_admin_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.list_services)

    @decorators.idempotent_id('04f59090-069d-4cae-b028-e004ff29126c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_service_by_invalid_params(self):
        # All services are expected if send the request with invalid parameter
        services = self.admin_client.list_services()['services']
        params = {'fake_param': 'fake_param_value'}
        services_fake = self.admin_client.list_services(params)['services']
        self.assertEqual(len(services), len(services_fake))

        # "update_at" field could be updated before second request,
        # so do not take it in account.
        for service in services + services_fake:
            service["updated_at"] = "removed_possible_difference"

        msg = ('Unexpected service list. Expected %s, got %s.' %
               (services, services_fake))
        self.assertEqual(sorted(services, key=lambda service: service['id']),
                         sorted(services_fake,
                                key=lambda service: service['id']),
                         msg)

    @decorators.idempotent_id('386dc131-39f9-4d5f-af87-edf76e3d0e71')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_service_by_invalid_host(self):
        params = {'host': 'fake_host'}
        services_fake = self.admin_client.list_services(params)['services']
        self.assertEqual(0, len(services_fake))

    @decorators.idempotent_id('766461b0-e89a-4113-8229-24c4d11d585a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_service_by_invalid_binary(self):
        params = {'binary': 'fake_binary'}
        services_fake = self.admin_client.list_services(params)['services']
        self.assertEqual(0, len(services_fake))

    @decorators.idempotent_id('ac570fde-690d-4448-9cce-ce35e0a14b88')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_service_by_invalid_zone(self):
        params = {'zone': 'fake_zone'}
        services_fake = self.admin_client.list_services(params)['services']
        self.assertEqual(0, len(services_fake))

    @decorators.idempotent_id('da0fef1d-c4d3-4c33-a836-5f836e85df69')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_service_by_invalid_status(self):
        params = {'status': 'fake_status'}
        services_fake = self.admin_client.list_services(params)['services']
        self.assertEqual(0, len(services_fake))

    @decorators.idempotent_id('41936575-3a96-455b-8069-7f6563abf0e2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_service_by_invalid_state(self):
        params = {'state': 'fake_state'}
        services_fake = self.admin_client.list_services(params)['services']
        self.assertEqual(0, len(services_fake))

    @decorators.idempotent_id('3c72227b-7fa1-4294-bdf4-413ec4c324e5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data(
        ('os-services', '2.7'),
        ('services', '2.6'),
        ('services', '2.0'),
    )
    @ddt.unpack
    @utils.skip_if_microversion_not_supported("2.7")
    def test_list_services_with_wrong_versions(self, url, version):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.list_services,
            version=version, url=url,
        )
