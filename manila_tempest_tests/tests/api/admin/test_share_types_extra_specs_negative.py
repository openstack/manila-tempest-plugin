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
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class ExtraSpecsAdminNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(ExtraSpecsAdminNegativeTest, cls).resource_setup()
        cls.extra_specs = cls.add_extra_specs_to_dict({"key": "value"})

    @decorators.idempotent_id('195c1cc6-249a-4f82-b420-4901d2557b3a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_extra_specs_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.create_share_type_extra_specs,
            st["id"],
            self.add_extra_specs_to_dict({"key": "new_value"}))

    @decorators.idempotent_id('dc883ec3-1bae-4ed7-8bf5-2cdc7027e37b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_extra_specs_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.get_share_type_extra_specs,
            st["id"])

    @decorators.idempotent_id('1d3e687e-b2fb-4b96-8428-324ff881eea2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_spec_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.get_share_type_extra_spec,
            st["id"], "key")

    @decorators.idempotent_id('4c9505d9-d4ef-42fa-8410-8ab88ec0c852')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_specs_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.get_share_type_extra_specs,
            st["id"])

    @decorators.idempotent_id('36c5ada4-9efd-4f6a-b58d-24f08a2433ce')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_read_extra_specs_on_share_type_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        share_type = self.shares_v2_client.get_share_type(st['id'])
        # Verify a non-admin can only read the required extra-specs
        expected_keys = ['driver_handles_share_servers', 'snapshot_support']
        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.24'):
            expected_keys.append('create_share_from_snapshot_support')
        if utils.is_microversion_ge(CONF.share.max_api_microversion,
                                    constants.REVERT_TO_SNAPSHOT_MICROVERSION):
            expected_keys.append('revert_to_snapshot_support')
        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.32'):
            expected_keys.append('mount_snapshot_support')
        actual_keys = share_type['share_type']['extra_specs'].keys()
        self.assertEqual(sorted(expected_keys), sorted(actual_keys),
                         'Incorrect extra specs visible to non-admin user; '
                         'expected %s, got %s' % (expected_keys, actual_keys))

    @decorators.idempotent_id('62a9b77a-f796-4bd9-baf9-7c24b3f55560')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_extra_spec_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.update_share_type_extra_spec,
            st["id"], "key", "new_value")

    @decorators.idempotent_id('207cec3c-8ed9-4d6d-8fc8-3aecaacdff93')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_extra_specs_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.update_share_type_extra_specs,
            st["id"], {"key": "new_value"})

    @decorators.idempotent_id('3f43c5d0-23c5-4b76-98c7-a3f9adb33c89')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_extra_specs_with_user(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.delete_share_type_extra_spec,
            st["id"], "key")

    @decorators.idempotent_id('d82a7bcc-1dc5-4ef8-87cd-f8dff1574adc')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_too_long_key(self):
        too_big_key = "k" * 256
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_type_extra_specs,
            st["id"],
            self.add_extra_specs_to_dict({too_big_key: "value"}))

    @decorators.idempotent_id('210faa88-8f2f-45f5-9bcf-54ce81d03788')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_too_long_value_with_creation(self):
        too_big_value = "v" * 256
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_type_extra_specs,
            st["id"],
            self.add_extra_specs_to_dict({"key": too_big_value}))

    @decorators.idempotent_id('890dceaa-22c4-4d2c-99ca-16ac8cdda33c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_too_long_value_with_update(self):
        too_big_value = "v" * 256
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.admin_shares_v2_client.create_share_type_extra_specs(
            st["id"],
            self.add_extra_specs_to_dict({"key": "value"}))
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.update_share_type_extra_specs,
            st["id"],
            self.add_extra_specs_to_dict({"key": too_big_value}))

    @decorators.idempotent_id('c512437e-6cfd-4545-859f-554955bd0fc9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_too_long_value_with_update_of_one_key(self):
        too_big_value = "v" * 256
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.admin_shares_v2_client.create_share_type_extra_specs(
            st["id"],
            self.add_extra_specs_to_dict({"key": "value"}))
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.update_share_type_extra_spec,
            st["id"], "key", too_big_value)

    @decorators.idempotent_id('938115f7-512e-49c3-a16a-a6498d6069bb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_es_with_empty_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_type_extra_specs, "")

    @decorators.idempotent_id('65c3c528-008f-43f5-b367-8bd77cfab4a7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_es_with_invalid_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_type_extra_specs,
            data_utils.rand_name("fake"))

    @decorators.idempotent_id('430e0bed-9073-4822-8d0b-a3c55a8dfa31')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_es_with_empty_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.create_share_type_extra_specs,
            "", {"key1": "value1", })

    @decorators.idempotent_id('7b43025d-b014-460f-9c9d-1004433fb798')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_es_with_invalid_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.create_share_type_extra_specs,
            data_utils.rand_name("fake"), {"key1": "value1", })

    @decorators.idempotent_id('7b9bee14-5ca5-4110-a56a-b3030b6b3948')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_es_with_empty_specs(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_type_extra_specs,
            st["id"], "")

    @decorators.idempotent_id('7f199925-44d2-4d92-bedc-2636c07621fb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_es_with_invalid_specs(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.create_share_type_extra_specs,
            st["id"], {"": "value_with_empty_key"})

    @decorators.idempotent_id('51241ed9-350b-4218-bfb0-c446d660d70b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_spec_with_empty_key(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_type_extra_spec,
            st["id"], "")

    @decorators.idempotent_id('271d825b-2c57-429a-8dca-2cb9dd140dd0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_spec_with_invalid_key(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_type_extra_spec,
            st["id"], data_utils.rand_name("fake"))

    @decorators.idempotent_id('cf07e7bc-cd3a-4c85-a848-786a60ba1f7d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_specs_with_empty_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_type_extra_specs,
            "")

    @decorators.idempotent_id('dfe6e34b-c86a-4cf6-9bf3-19de3a886b67')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_extra_specs_with_invalid_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.get_share_type_extra_specs,
            data_utils.rand_name("fake"))

    @decorators.idempotent_id('0b8f6b51-0583-4b59-a851-9189db657a05')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_es_key_with_empty_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            "", "key", )

    @decorators.idempotent_id('9aa8fb2a-28a5-44b7-848b-9b49e1e9d670')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_es_key_with_invalid_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            data_utils.rand_name("fake"), "key", )

    @decorators.idempotent_id('cd68d020-24d2-4f68-8691-782b4815c1b0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_with_invalid_key(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            st["id"], data_utils.rand_name("fake"))

    @decorators.idempotent_id('1ed5cbc9-21a8-45b7-8069-b7c0aaeede21')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_spec_with_empty_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.update_share_type_extra_spec,
            "", "key", "new_value")

    @decorators.idempotent_id('704087fa-0397-4d9d-98b7-f9b081f64c86')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_spec_with_invalid_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.update_share_type_extra_spec,
            data_utils.rand_name("fake"), "key", "new_value")

    @decorators.idempotent_id('eab96e92-9b95-44b0-89a2-e907a103039d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_spec_with_empty_key(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.update_share_type_extra_spec,
            st["id"], "", "new_value")

    @decorators.idempotent_id('70af1a8a-ab3e-4c8b-862d-8a36c2d47cb3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_with_invalid_shr_type_id(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_shares_v2_client.update_share_type_extra_specs,
            data_utils.rand_name("fake"), {"key": "new_value"})

    @decorators.idempotent_id('d2595594-eaad-43dc-b847-0a009a17d854')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_with_invalid_specs(self):
        st = self.create_share_type(extra_specs=self.extra_specs)
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_shares_v2_client.update_share_type_extra_specs,
            st["id"], {"": "new_value"})

    @decorators.idempotent_id('6849eada-89a8-4009-a91d-87367621f9aa')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_spec_driver_handles_share_servers(self):
        st = self.create_share_type(extra_specs=self.extra_specs)

        # Try delete extra spec 'driver_handles_share_servers'
        self.assertRaises(
            lib_exc.Forbidden,
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            st["id"],
            "driver_handles_share_servers")

    @decorators.idempotent_id('6ea50e81-2c93-4258-8358-6f8d354a339a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data('2.0', '2.23')
    def test_try_delete_required_spec_snapshot_support_version(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        st = self.create_share_type(extra_specs=self.extra_specs)
        # Try delete extra spec 'snapshot_support'
        self.assertRaises(
            lib_exc.Forbidden,
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            st["id"], "snapshot_support", version=version)
