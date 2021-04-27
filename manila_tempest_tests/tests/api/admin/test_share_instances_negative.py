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
from manila_tempest_tests import utils


@ddt.ddt
class ShareInstancesNegativeTest(base.BaseSharesAdminTest):

    @classmethod
    def resource_setup(cls):
        super(ShareInstancesNegativeTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)

    @decorators.idempotent_id('babe885e-a8ab-439d-8b95-e5422983a942')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.34")
    @ddt.data('path', 'id')
    def test_list_share_instances_with_export_location_and_invalid_version(
            self, export_location_type):
        # In API versions <v2.35, querying the share instance API by export
        # location path or ID should have no effect. Those filters were
        # supported from v2.35
        filters = {
            'export_location_' + export_location_type: 'fake',
        }
        share_instances = self.shares_v2_client.list_share_instances(
            params=filters, version="2.34")['share_instances']

        self.assertGreater(len(share_instances), 0)

    @decorators.idempotent_id('ce0d045c-e418-42fa-86e4-ead493fc0663')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.35")
    @ddt.data('path', 'id')
    def test_list_share_instances_with_export_location_not_exist(
            self, export_location_type):
        filters = {
            'export_location_' + export_location_type: 'fake_not_exist',
        }
        share_instances = self.shares_v2_client.list_share_instances(
            params=filters)['share_instances']

        self.assertEqual(0, len(share_instances))
