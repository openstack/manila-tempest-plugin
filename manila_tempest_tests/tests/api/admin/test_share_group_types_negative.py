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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareGroupTypesAdminNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareGroupTypesAdminNegativeTest, cls).skip_checks()
        if not CONF.share.run_share_group_tests:
            raise cls.skipException('Share Group tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            constants.MIN_SHARE_GROUP_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ShareGroupTypesAdminNegativeTest, cls).resource_setup()
        cls.share_type = cls.create_share_type(
            data_utils.rand_name("unique_st_name"),
            extra_specs=cls.add_extra_specs_to_dict({"key": "value"}),
            client=cls.admin_shares_v2_client)
        cls.share_group_type = cls.create_share_group_type(
            data_utils.rand_name("unique_sgt_name"),
            share_types=[cls.share_type['id']],
            group_specs={"key": "value"},
            client=cls.admin_shares_v2_client)

    @decorators.idempotent_id('1f8e3f98-4df7-4383-94d6-4ad058ef79c1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_without_name(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_group_type,
            name=None,
            share_types=data_utils.rand_name("fake"))

    @decorators.idempotent_id('6c95f5b7-6e30-4e1e-b0fc-a0f05cf2982d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_with_nonexistent_share_type(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.create_share_group_type,
            name=data_utils.rand_name("sgt_name_should_have_not_been_created"),
            share_types=data_utils.rand_name("fake"))

    @decorators.idempotent_id('ce6ba41b-4207-4866-8f70-7a89f64b4cd4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_with_empty_name(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group_type, '',
            client=self.admin_shares_v2_client)

    @decorators.idempotent_id('77159ec6-adb7-4d35-9d4b-039d322f7852')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_with_too_big_name(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group_type,
            "x" * 256, client=self.admin_shares_v2_client)

    @decorators.idempotent_id('43ac388d-05e8-45d5-b633-631cc1f290af')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_with_wrong_value_for_group_specs(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_group_type,
            name=data_utils.rand_name("tempest_manila"),
            share_types=[self.share_type['id']],
            group_specs="expecting_error_code_400")

    @decorators.idempotent_id('8fb8bd73-0219-460d-993e-bff7ddec29e8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_share_group_type_using_nonexistent_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_group_type,
            data_utils.rand_name("fake"))

    @decorators.idempotent_id('76b5c302-f492-45b4-b464-7be6efd373be')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_share_group_type_using_nonexistent_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.delete_share_group_type,
            data_utils.rand_name("fake"))

    @decorators.idempotent_id('081183cb-0f1c-4b67-8552-909935dc0be2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_duplicate_of_share_group_type(self):
        unique_name = data_utils.rand_name("unique_sgt_name")
        list_of_ids = set()
        for _ in (1, 2):
            sg_type = self.create_share_group_type(
                unique_name,
                share_types=[self.share_type['id']],
                client=self.admin_shares_v2_client,
                cleanup_in_class=False)
            self.assertRaises(
                lib_exc.Conflict,
                self.create_share_group_type,
                unique_name,
                share_types=[self.share_type['id']],
                client=self.admin_shares_v2_client)
            list_of_ids.add(sg_type['id'])
            self.assertEqual(unique_name, sg_type['name'])
            self.admin_shares_v2_client.delete_share_group_type(sg_type['id'])
        self.assertEqual(2, len(list_of_ids))

    @decorators.idempotent_id('6c30989d-2e8a-48d3-809a-556dddae51bd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_project_access_to_public_share_group_type(self):
        self.assertRaises(
            lib_exc.Conflict,
            self.admin_shares_v2_client.add_access_to_share_group_type,
            self.share_group_type["id"],
            self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('3375a1f8-7828-4cbe-89d7-fe11fcf30b21')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_remove_project_access_from_public_share_group_type(self):
        self.assertRaises(
            lib_exc.Conflict,
            self.admin_shares_v2_client.remove_access_from_share_group_type,
            self.share_group_type["id"],
            self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('68e3d7f9-fdc0-44a2-ae84-a72eba314e19')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_project_access_to_nonexistent_share_group_type(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.add_access_to_share_group_type,
            data_utils.rand_name("fake"),
            self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('94f0c902-ab12-435e-abd5-e09a892db82a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_remove_project_access_from_nonexistent_share_group_type(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.remove_access_from_share_group_type,
            data_utils.rand_name("fake"),
            self.admin_shares_v2_client.tenant_id)

    @decorators.idempotent_id('3e763f5b-6663-4620-9471-ed3050da6201')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_share_group_type_extra_specs_with_user(self):
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.get_share_group_type_specs,
            self.share_group_type['id'])

    @decorators.idempotent_id('2264f7eb-3ff0-47e9-8ab0-54694113db3d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_specs_from_nonexistent_share_group_type(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_group_type_specs,
            data_utils.rand_name('fake'))

    @decorators.idempotent_id('2be79455-0ce7-4ca6-818f-40651ba79c6e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_spec_with_nonexistent_key(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_group_type_spec,
            self.share_group_type['id'], 'fake_key')
