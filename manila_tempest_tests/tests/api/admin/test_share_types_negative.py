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

import ddt
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


@ddt.ddt
class ShareTypesAdminNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(ShareTypesAdminNegativeTest, cls).resource_setup()
        cls.extra_specs = cls.add_extra_specs_to_dict({"key": "value"})

    @decorators.idempotent_id('0efe4ed6-9318-4174-aef7-fca4b6aa6444')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_nonexistent_share_type(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_shares_v2_client.create_share,
                          share_type_id=data_utils.rand_name("fake"))

    @decorators.idempotent_id('a1cd6c4f-4dc4-4f45-813b-f1cd3527c614')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_type_with_empty_name(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_type, '')

    @decorators.idempotent_id('ca59430b-d1fb-4e8f-b1e3-6ab6a6b40984')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_type_with_too_big_name(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share_type,
                          "x" * 256,
                          client=self.admin_shares_v2_client)

    @decorators.idempotent_id('42f7777a-7ee4-4622-80f8-8726b467c4db')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data('2.0', '2.6', '2.40')
    def test_create_share_type_with_description_in_wrong_version(
            self, version):
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share_type,
                          data_utils.rand_name("tempest_type_name"),
                          extra_specs=self.add_extra_specs_to_dict(),
                          description="tempest_type_description",
                          version=version,
                          client=self.admin_shares_v2_client)

    @decorators.idempotent_id('43b0ef5a-3a05-4f74-a08e-57efebb7e66e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_share_type_by_nonexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_shares_v2_client.get_share_type,
                          data_utils.rand_name("fake"))

    @decorators.idempotent_id('27e00ad7-edc8-4d50-b53e-4da41dd8a5d3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_share_type_by_nonexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_shares_v2_client.delete_share_type,
                          data_utils.rand_name("fake"))

    @decorators.idempotent_id('1f481bab-5205-49ee-bf01-b1848a32f9ee')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_duplicate_of_share_type(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(lib_exc.Conflict,
                          self.create_share_type,
                          st["name"],
                          extra_specs=self.add_extra_specs_to_dict(),
                          client=self.admin_shares_v2_client)

    @decorators.idempotent_id('c13f54eb-17a4-4403-be87-f6a3ca18de6e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_type_allowed_for_public(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(lib_exc.Conflict,
                          self.admin_shares_v2_client.add_access_to_share_type,
                          st["id"],
                          self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('bf1d68fb-b954-4b3b-af54-115f3b67b3b3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_remove_share_type_allowed_for_public(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Conflict,
            self.admin_shares_v2_client.remove_access_from_share_type,
            st["id"],
            self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('3d9a7e9d-2b64-422e-b8b6-88c3088564f6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_type_by_nonexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_shares_v2_client.add_access_to_share_type,
                          data_utils.rand_name("fake"),
                          self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('13d5c3cd-15cd-4c2e-ace6-46889cf9e0e2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_remove_share_type_by_nonexistent_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.remove_access_from_share_type,
            data_utils.rand_name("fake"),
            self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('0fd53c51-e1ba-4392-9f4c-5d3bdd157163')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_create_share_with_non_allowed_share_type(self):
        # Create a private share type
        name = data_utils.rand_name('share-type')
        share_type = self.create_share_type(
            client=self.admin_shares_v2_client,
            name=name, is_public=False,
            extra_specs=self.add_extra_specs_to_dict())

        # The share type should not be listed without access
        share_type_list = (
            self.admin_shares_v2_client.list_share_types()['share_types'])
        self.assertFalse(
            any(share_type['id'] in st['id'] for st in share_type_list))

        # List projects that have access for share type - none expected
        access = self.admin_shares_v2_client.list_access_to_share_type(
            share_type['id'])['share_type_access']
        self.assertEmpty(access)

        # Although the share type should not be found on alt project,
        # try to create a share with it by using the share type name
        self.assertRaises(lib_exc.NotFound,
                          self.alt_shares_v2_client.create_share,
                          share_type_id=share_type['name'])

        # The share should not be listed
        share_list = self.alt_shares_v2_client.list_shares(
            detailed=True)['shares']
        self.assertFalse(
            any(share_type['id'] in s['share_type'] for s in share_list))
