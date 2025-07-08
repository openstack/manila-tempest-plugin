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

from tempest import config
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base

CONF = config.CONF


class SharesMetadataTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SharesMetadataTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)

    def _verify_share_metadata(self, share, md):

        # verify metadata items
        for key in md:
            get_value = self.shares_v2_client.get_metadata_item(
                share["id"], key)['meta']
            self.assertEqual(md[key], get_value[key])

    @decorators.idempotent_id('9070249f-6e94-4a38-a036-08debee547c3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_in_share_creation(self):

        md = {"key1": "value1", "key2": "value2", }

        # create share with metadata
        share = self.create_share(share_type_id=self.share_type_id,
                                  metadata=md,
                                  cleanup_in_class=False)

        # verify metadata
        self._verify_share_metadata(share, md)

    @decorators.idempotent_id('2725ab8e-cc04-4032-9393-74726ba43eb7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_get_delete_metadata(self):

        md = {"key3": "value3", "key4": "value4", "key.5.1": "value.5"}

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(share["id"], md)

        # verify metadata
        self._verify_share_metadata(share, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(share["id"], key)

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(share["id"])[
            'metadata']
        for key in md.keys():
            self.assertNotIn(key, list(get_metadata.keys()))

    @decorators.idempotent_id('4e5f8159-62b6-4d5c-f729-d8b1f029d7de')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_not_delete_pre_metadata(self):
        md1 = {"key9": "value9", "key10": "value10", }
        md2 = {"key11": "value11", "key12": "value12", }

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(share["id"], md1)

        # verify metadata
        self._verify_share_metadata(share, md1)

        # set metadata again
        self.shares_v2_client.set_metadata(share["id"], md2)

        # verify metadata
        md1.update(md2)
        md = md1

        # verify metadata
        self._verify_share_metadata(share, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(share["id"], key)

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            share["id"])['metadata']
        for key in md.keys():
            self.assertNotIn(key, list(get_metadata.keys()))

    @decorators.idempotent_id('2ec70ba5-050b-3b17-c862-c149e53543c0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_key_already_exist(self):
        md1 = {"key9": "value9", "key10": "value10", }
        md2 = {"key9": "value13", "key11": "value11", }

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(share["id"], md1)

        # verify metadata
        self._verify_share_metadata(share, md1)

        # set metadata again
        self.shares_v2_client.set_metadata(share["id"], md2)

        # verify metadata
        md = {"key9": "value13", "key10": "value10",
              "key11": "value11"}
        self._verify_share_metadata(share, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(share["id"], key)

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            share["id"])['metadata']
        for key in md.keys():
            self.assertNotIn(key, list(get_metadata.keys()))

    @decorators.idempotent_id('c94851f4-2559-4712-9297-9912db1da7ff')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_and_update_metadata_by_key(self):

        md1 = {"key5": "value5", "key6": "value6", }
        md2 = {"key7": "value7", "key8": "value8", }

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(share["id"], md1)

        # update metadata
        self.shares_v2_client.update_all_metadata(share["id"], md2)

        # verify metadata
        self._verify_share_metadata(share, md2)

    @decorators.idempotent_id('698ba406-493f-4c69-a093-273676fed438')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_v2_client.set_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data['k'], body_get.get('k'))

    @decorators.idempotent_id('34c5bd96-ced7-42ef-a114-570cc63cf81d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_v2_client.set_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertIn(max_key, body_get)
        self.assertEqual(data[max_key], body_get.get(max_key))

    @decorators.idempotent_id('c776ab40-f75e-4d9f-abcf-a8f628a25991')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_v2_client.set_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('759ec4ab-2537-44ad-852b-1af85c6ca933')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_v2_client.set_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('c5ca19ba-3595-414a-8ff9-fbc88cd801ba')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_v2_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data["k"], body_get["k"])

    @decorators.idempotent_id('5eff5619-b7cd-42f1-85e0-47d3d47098dd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_v2_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        body_get_keys = list(body_get.keys())
        self.assertIn(max_key, body_get_keys)
        self.assertEqual(data[max_key], body_get[max_key])

    @decorators.idempotent_id('44a572f1-6b5c-49d0-8f2e-1583ec3428d8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_v2_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(data["key"], body_get["key"])

    @decorators.idempotent_id('694d95e1-ba8c-49fc-a888-6f9f0d51d77d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_v2_client.update_all_metadata(self.share["id"], data)

        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']
        self.assertEqual(max_value, body_get["key"])


class SharesMetadataCEPHFSTest(base.BaseSharesMixedTest):

    protocol = "cephfs"

    @classmethod
    def resource_setup(cls):
        super(SharesMetadataCEPHFSTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)

    @classmethod
    def skip_checks(cls):
        super(SharesMetadataCEPHFSTest, cls).skip_checks()
        if not (cls.protocol in CONF.share.enable_protocols):
            msg = (
                "CEPHFS filesystem metadata tests are disabled "
                "for the %s protocol." % cls.protocol)
            raise cls.skipException(msg)

    @decorators.idempotent_id('58edc9c8-8b85-49aa-80aa-209fc8f40a13')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_cephfs_share_contains_mount_option(self):
        body_get = self.shares_v2_client.get_metadata(
            self.share["id"])['metadata']

        self.assertIn("__mount_options", body_get)
        self.assertIn("fs", body_get["__mount_options"])
