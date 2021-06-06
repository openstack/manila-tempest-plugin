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


@ddt.ddt
class SharesMetadataAPIOnlyNegativeTest(base.BaseSharesTest):

    @decorators.idempotent_id('22aecf50-0d98-4b97-82b8-599559f7692f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data(True, False)
    def test_try_set_metadata_to_unexisting_share(self, is_v2_client):
        md = {u"key1": u"value1", u"key2": u"value2", }
        client = self.shares_v2_client if is_v2_client else self.shares_client
        self.assertRaises(lib_exc.NotFound,
                          client.set_metadata,
                          "wrong_share_id", md)

    @decorators.idempotent_id('7df0acd7-03f8-45c4-8c72-eb6932af70b1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data(True, False)
    def test_try_update_all_metadata_for_unexisting_share(self, is_v2_client):
        md = {u"key1": u"value1", u"key2": u"value2", }
        client = self.shares_v2_client if is_v2_client else self.shares_client
        self.assertRaises(lib_exc.NotFound,
                          client.update_all_metadata,
                          "wrong_share_id", md)


@ddt.ddt
class SharesMetadataNegativeTest(base.BaseSharesMixedTest):
    @classmethod
    def resource_setup(cls):
        super(SharesMetadataNegativeTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)

    @decorators.idempotent_id('0cb7f160-4fa4-4d30-8a46-373ddae5844d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_set_metadata_with_empty_key(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.set_metadata,
                          self.share["id"], {"": "value"})

    @decorators.idempotent_id('759ca34d-1c87-43f3-8da2-8e1d373049ac')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_upd_metadata_with_empty_key(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.update_all_metadata,
                          self.share["id"], {"": "value"})

    @decorators.idempotent_id('94c7ebb3-14c3-4ff1-9839-ae3acb318cd0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_set_metadata_with_too_big_key(self):
        too_big_key = "x" * 256
        md = {too_big_key: "value"}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.set_metadata,
                          self.share["id"], md)

    @decorators.idempotent_id('33ef3047-6ca3-4547-a681-b52314382dcb')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_upd_metadata_with_too_big_key(self):
        too_big_key = "x" * 256
        md = {too_big_key: "value"}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.update_all_metadata,
                          self.share["id"], md)

    @decorators.idempotent_id('1114970a-1b45-4c56-b20a-e13e1764e3c4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_set_metadata_with_too_big_value(self):
        too_big_value = "x" * 1024
        md = {"key": too_big_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.set_metadata,
                          self.share["id"], md)

    @decorators.idempotent_id('c2eddcf0-cf81-4f9f-b06d-c9165ab8553e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_upd_metadata_with_too_big_value(self):
        too_big_value = "x" * 1024
        md = {"key": too_big_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.update_all_metadata,
                          self.share["id"], md)

    @decorators.idempotent_id('14df3262-5a2b-4de4-b335-422329b22b07')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_delete_unexisting_metadata(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_metadata,
                          self.share["id"], "wrong_key")

    @decorators.idempotent_id('c6c70d55-7ed0-439f-ae34-f19af55361f6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(("foo.xml", False), ("foo.json", False),
              ("foo.xml", True), ("foo.json", True))
    @ddt.unpack
    def test_try_delete_metadata_with_unsupport_format_key(
            self, key, is_v2_client):
        md = {key: u"value.test"}

        client = self.shares_v2_client if is_v2_client else self.shares_client
        # set metadata
        client.set_metadata(self.share["id"], md)

        self.assertRaises(lib_exc.NotFound,
                          client.delete_metadata,
                          self.share["id"], key)
