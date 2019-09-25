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
import random
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base

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
        cls.st = cls._create_share_type()
        cls.st2 = cls._create_share_type()

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.create_share_type,
                          data_utils.rand_name("used_user_creds"),
                          client=self.shares_client)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.delete_share_type,
                          self.st["id"])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_add_access_to_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.add_access_to_share_type,
                          self.st['id'],
                          self.shares_client.tenant_id)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_remove_access_from_share_type_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.remove_access_from_share_type,
                          self.st['id'],
                          self.shares_client.tenant_id)

    @base.skip_if_microversion_lt("2.50")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data(
        ('2.50', '', None, None),
        (LATEST_MICROVERSION, '', None, None),
        ('2.50', None, None, 'not_bool'),
        (LATEST_MICROVERSION, None, None, 'not_bool'),
        ('2.50', None, generate_long_description(256), None),
        (LATEST_MICROVERSION, None, generate_long_description(256), None),
    )
    @ddt.unpack
    def test_share_type_update_bad_request(
            self, version, st_name, st_description, st_is_public):
        st_id = self.st['id']
        # Update share type
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_shares_v2_client.update_share_type,
                          st_id, st_name, st_is_public, st_description,
                          version)

    @base.skip_if_microversion_lt("2.50")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data('2.50', LATEST_MICROVERSION)
    def test_share_type_update_conflict(self, version):
        name_1 = self.st['name']
        st_id_2 = self.st2['id']
        # Update share type
        self.assertRaises(lib_exc.Conflict,
                          self.admin_shares_v2_client.update_share_type,
                          st_id_2, name_1, None, None, version)
