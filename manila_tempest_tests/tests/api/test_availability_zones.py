# Copyright 2015 mirantis Inc.
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
from manila_tempest_tests import utils


class AvailabilityZonesTest(base.BaseSharesTest):

    def _list_availability_zones_assertions(self, availability_zones):
        self.assertGreater(len(availability_zones), 0)
        keys = ("created_at", "updated_at", "name", "id")
        for az in availability_zones:
            self.assertEqual(len(keys), len(az))
            for key in keys:
                self.assertIn(key, az)

    @decorators.idempotent_id('202f20d3-1afa-40ea-a5e6-8b7bda40e6cf')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_availability_zones_legacy_url_api_v1(self):
        # NOTE(vponomaryov): remove this test with removal of availability zone
        # extension url support.
        azs = self.shares_client.list_availability_zones(
            )['availability_zones']
        self._list_availability_zones_assertions(azs)

    @decorators.idempotent_id('7054f2f4-bc77-4d60-82a6-2f23b93d281e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported("2.6")
    def test_list_availability_zones_legacy_url_api_v2(self):
        # NOTE(vponomaryov): remove this test with removal of availability zone
        # extension url support.
        azs = self.shares_v2_client.list_availability_zones(
            url='os-availability-zone', version='2.6')['availability_zones']
        self._list_availability_zones_assertions(azs)

    @decorators.idempotent_id('4caadb86-2988-4adb-b705-aece99235c1e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported("2.7")
    def test_list_availability_zones(self):
        azs = self.shares_v2_client.list_availability_zones(
            version='2.7')['availability_zones']
        self._list_availability_zones_assertions(azs)
