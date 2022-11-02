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

import random

import ddt
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF

LATEST_MICROVERSION = CONF.share.max_api_microversion


def generate_long_description(des_length=256):
    random_str = ''
    base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz'
    length = len(base_str) - 1
    for i in range(des_length):
        random_str += base_str[random.randint(0, length)]
    return random_str


@ddt.ddt
class ShareTypesNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(ShareTypesNegativeTest, cls).resource_setup()
        cls.st = cls.create_share_type()
        cls.st2 = cls.create_share_type()

    @decorators.idempotent_id('d6a6ac4d-6582-408d-ba55-6f5128eb940e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.create_share_type,
                          data_utils.rand_name("used_user_creds"),
                          client=self.shares_client)

    @decorators.idempotent_id('857c664f-e634-4865-ba05-bdcd4336725d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.delete_share_type,
                          self.st["id"])

    @decorators.idempotent_id('06203276-f6a3-4a07-a014-8749763395d6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_add_access_to_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.add_access_to_share_type,
                          self.st['id'],
                          self.shares_client.tenant_id)

    @decorators.idempotent_id('08b2d093-2ad8-46aa-8112-81d50547f36d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_remove_access_from_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.remove_access_from_share_type,
                          self.st['id'],
                          self.shares_client.tenant_id)

    @utils.skip_if_microversion_not_supported("2.50")
    @decorators.idempotent_id('4a22945c-8988-43a1-88c9-eb86e6abcd8e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.named_data(
        ('2_50', '2.50', '', None, None),
        (LATEST_MICROVERSION, LATEST_MICROVERSION, '', None, None),
        ('2_50_bad_public', '2.50', None, None, 'not_bool'),
        (f'{LATEST_MICROVERSION}_bad_public', LATEST_MICROVERSION, None, None,
         'not_bool'),
        ('2_50_description', '2.50', None, generate_long_description(256),
         None),
        (f'{LATEST_MICROVERSION}_description', LATEST_MICROVERSION, None,
         generate_long_description(256), None),
    )
    def test_share_type_update_bad_request(
            self, version, st_name, st_description, st_is_public):
        st_id = self.st['id']
        # Update share type
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_shares_v2_client.update_share_type,
                          st_id, st_name, st_is_public, st_description,
                          version)

    @utils.skip_if_microversion_not_supported("2.50")
    @decorators.idempotent_id('7193465a-ed8e-44d5-9ca9-4e8a3c5958e0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data('2.50', LATEST_MICROVERSION)
    def test_share_type_update_conflict(self, version):
        name_1 = self.st['name']
        st_id_2 = self.st2['id']
        # Update share type
        self.assertRaises(lib_exc.Conflict,
                          self.admin_shares_v2_client.update_share_type,
                          st_id_2, name_1, None, None, version)
