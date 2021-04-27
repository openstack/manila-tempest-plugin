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

from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


class SharesMetadataTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SharesMetadataTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)

    @decorators.idempotent_id('9070249f-6e94-4a38-a036-08debee547c3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_in_share_creation(self):

        md = {u"key1": u"value1", u"key2": u"value2", }

        # create share with metadata
        share = self.create_share(share_type_id=self.share_type_id,
                                  metadata=md,
                                  cleanup_in_class=False)

        # get metadata of share
        metadata = self.shares_client.get_metadata(share["id"])['metadata']

        # verify metadata
        self.assertEqual(md, metadata)

    @decorators.idempotent_id('2725ab8e-cc04-4032-9393-74726ba43eb7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_get_delete_metadata(self):

        md = {u"key3": u"value3", u"key4": u"value4", u"key.5.1": u"value.5"}

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set metadata
        self.shares_client.set_metadata(share["id"], md)

        # read metadata
        get_md = self.shares_client.get_metadata(share["id"])['metadata']

        # verify metadata
        self.assertEqual(md, get_md)

        # verify metadata items
        for key in md:
            get_value = self.shares_client.get_metadata_item(share["id"], key)
            self.assertEqual(md[key], get_value[key])

        # delete metadata
        for key in md.keys():
            self.shares_client.delete_metadata(share["id"], key)

        # verify deletion of metadata
        get_metadata = self.shares_client.get_metadata(share["id"])['metadata']
        self.assertEqual({}, get_metadata)

    @decorators.idempotent_id('c94851f4-2559-4712-9297-9912db1da7ff')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_and_update_metadata_by_key(self):

        md1 = {u"key5": u"value5", u"key6": u"value6", }
        md2 = {u"key7": u"value7", u"key8": u"value8", }

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set metadata
        self.shares_client.set_metadata(share["id"], md1)

        # update metadata
        self.shares_client.update_all_metadata(share["id"], md2)

        # get metadata
        get_md = self.shares_client.get_metadata(share["id"])['metadata']

        # verify metadata
        self.assertEqual(md2, get_md)

    @decorators.idempotent_id('698ba406-493f-4c69-a093-273676fed438')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_client.set_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data['k'], body_get.get('k'))

    @decorators.idempotent_id('34c5bd96-ced7-42ef-a114-570cc63cf81d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_client.set_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertIn(max_key, body_get)
        self.assertEqual(data[max_key], body_get.get(max_key))

    @decorators.idempotent_id('c776ab40-f75e-4d9f-abcf-a8f628a25991')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_client.set_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('759ec4ab-2537-44ad-852b-1af85c6ca933')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_client.set_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('c5ca19ba-3595-414a-8ff9-fbc88cd801ba')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data, body_get)

    @decorators.idempotent_id('5eff5619-b7cd-42f1-85e0-47d3d47098dd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data, body_get)

    @decorators.idempotent_id('44a572f1-6b5c-49d0-8f2e-1583ec3428d8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data, body_get)

    @decorators.idempotent_id('694d95e1-ba8c-49fc-a888-6f9f0d51d77d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data, body_get)
