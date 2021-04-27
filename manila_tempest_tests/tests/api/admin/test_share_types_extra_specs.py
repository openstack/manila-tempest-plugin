# Copyright 2014 OpenStack Foundation
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

import copy

import ddt
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


class ExtraSpecsReadAdminTest(base.BaseSharesAdminTest):

    @classmethod
    def resource_setup(cls):
        super(ExtraSpecsReadAdminTest, cls).resource_setup()
        cls.share_type_name = data_utils.rand_name("share-type")
        cls.required_extra_specs = cls.add_extra_specs_to_dict()

        cls.share_type = cls.create_share_type(
            cls.share_type_name, extra_specs=cls.required_extra_specs)

        cls.st_id = cls.share_type["id"]
        cls.custom_extra_specs = {"key1": "value1", "key2": "value2"}
        cls.expected_extra_specs = copy.copy(cls.custom_extra_specs)
        cls.expected_extra_specs.update(cls.required_extra_specs)

        cls.shares_client.create_share_type_extra_specs(
            cls.st_id, cls.custom_extra_specs)

    @decorators.idempotent_id('d4cae104-838b-4248-8c9c-125165710786')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_one_share_type_extra_spec(self):
        es_get_one = self.shares_client.get_share_type_extra_spec(
            self.st_id, "key1")

        self.assertEqual({"key1": self.custom_extra_specs["key1"]}, es_get_one)

    @decorators.idempotent_id('508ceb85-5456-4db9-b33f-00620d7baea1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_all_share_type_extra_specs(self):
        es_get_all = self.shares_client.get_share_type_extra_specs(
            self.st_id)['extra_specs']

        self.assertEqual(self.expected_extra_specs, es_get_all)


@ddt.ddt
class ExtraSpecsWriteAdminTest(base.BaseSharesAdminTest):

    def setUp(self):
        super(ExtraSpecsWriteAdminTest, self).setUp()
        self.required_extra_specs = self.add_extra_specs_to_dict()
        self.custom_extra_specs = {"key1": "value1", "key2": "value2"}
        self.share_type_name = data_utils.rand_name("share-type")

        # Create share type
        self.share_type = self.create_share_type(
            self.share_type_name, extra_specs=self.required_extra_specs)

        self.st_id = self.share_type['id']

        # Create extra specs for share type
        self.shares_client.create_share_type_extra_specs(
            self.st_id, self.custom_extra_specs)

    @decorators.idempotent_id('baba776b-1b05-42ca-a002-bff1f8f14e13')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_one_share_type_extra_spec(self):
        self.custom_extra_specs["key1"] = "fake_value1_updated"

        # Update extra specs of share type
        update_one = self.shares_client.update_share_type_extra_spec(
            self.st_id, "key1", self.custom_extra_specs["key1"])
        self.assertEqual({"key1": self.custom_extra_specs["key1"]}, update_one)

        get = self.shares_client.get_share_type_extra_specs(
            self.st_id)['extra_specs']
        expected_extra_specs = self.custom_extra_specs
        expected_extra_specs.update(self.required_extra_specs)
        self.assertEqual(self.custom_extra_specs, get)

    @decorators.idempotent_id('374e7ff5-0d26-4778-bbb5-4ffd28521ad9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_all_share_type_extra_specs(self):
        self.custom_extra_specs["key2"] = "value2_updated"

        # Update extra specs of share type
        update_all = self.shares_client.update_share_type_extra_specs(
            self.st_id, self.custom_extra_specs)['extra_specs']
        self.assertEqual(self.custom_extra_specs, update_all)

        get = self.shares_client.get_share_type_extra_specs(
            self.st_id)['extra_specs']
        expected_extra_specs = self.custom_extra_specs
        expected_extra_specs.update(self.required_extra_specs)
        self.assertEqual(self.custom_extra_specs, get)

    @decorators.idempotent_id('129db0ce-9a4f-4a40-994f-e492174e0661')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_one_share_type_extra_spec(self):
        # Delete one extra spec for share type
        self.shares_client.delete_share_type_extra_spec(self.st_id, "key1")

        # Get metadata
        get = self.shares_client.get_share_type_extra_specs(
            self.st_id)['extra_specs']

        self.assertNotIn('key1', get)

    @decorators.idempotent_id('1b9f501d-8f34-46d0-b318-83bdfed571ec')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(*utils.deduplicate(['2.24', LATEST_MICROVERSION]))
    def test_delete_snapshot_support_extra_spec(self, version):
        """Is snapshot_support really an optional extra-spec if API > v2.24?"""
        utils.check_skip_if_microversion_not_supported(version)

        # set snapshot_support extra-spec
        self.shares_v2_client.update_share_type_extra_specs(
            self.st_id, {'snapshot_support': 'True'})

        # Get extra specs
        share_type_extra_specs = self.shares_client.get_share_type_extra_specs(
            self.st_id)['extra_specs']

        self.assertIn('snapshot_support', share_type_extra_specs)
        self.assertEqual('True', share_type_extra_specs['snapshot_support'])

        # Delete the 'snapshot_support' extra spec from the share type
        self.shares_v2_client.delete_share_type_extra_spec(
            self.st_id, 'snapshot_support', version=version)

        # Get extra specs
        share_type_extra_specs = self.shares_client.get_share_type_extra_specs(
            self.st_id)['extra_specs']

        self.assertNotIn('snapshot_support', share_type_extra_specs)
