# Copyright 2025 Cloudifcation GmbH.  All rights reserved.
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

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class SharesEncryptionNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(SharesEncryptionNegativeTest, cls).skip_checks()
        if not CONF.share.run_encryption_tests:
            raise cls.skipException('Encryption tests are disabled.')
        utils.check_skip_if_microversion_not_supported("2.90")

    @classmethod
    def resource_setup(cls):
        super(SharesEncryptionNegativeTest, cls).resource_setup()
        # create share_type
        cls.no_encryption_type = cls.create_share_type()
        cls.no_encryption_type_id = cls.no_encryption_type['id']
        cls.encryption_type = cls.create_share_type(
            extra_specs={
                'encryption_support': 'share_server',
            })
        cls.encryption_type_id = cls.encryption_type['id']

    @decorators.idempotent_id('b8097d56-067e-4d7c-8401-31bc7021fe81')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_invalid_share_type(self):
        # should not create share when encryption isn't supported by
        # share type
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_share,
                          share_type_id=self.no_encryption_type_id,
                          encryption_key_ref='fake_ref')

    @decorators.idempotent_id('b8097d56-067e-4d7c-8401-31bc7021fe88')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_invalid_encryption_key_ref(self):
        # should not create share when key ref is invalid UUID
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_share,
                          share_type_id=self.encryption_type_id,
                          encryption_key_ref='fake_ref')

    @decorators.idempotent_id('b8097d56-067e-4d7c-8401-31bc7021fe82')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_encryption_key_ref_absent_in_barbican(self):
        # should not create share when key ref is not present in barbican
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_share,
            share_type_id=self.encryption_type_id,
            encryption_key_ref='cfbe8ae1-7932-43f2-bf82-3fd3ddba30c3')
