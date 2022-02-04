# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


class ShareSnapshotMetadataTest(base.BaseSharesMixedTest):
    @classmethod
    def skip_checks(cls):
        super(ShareSnapshotMetadataTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.73")
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')

    @classmethod
    def resource_setup(cls):
        super(ShareSnapshotMetadataTest, cls).resource_setup()
        # create share_type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        if CONF.share.capability_create_share_from_snapshot_support:
            extra_specs.update({'create_share_from_snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share_name = data_utils.rand_name("tempest-share-name")
        cls.share_desc = data_utils.rand_name("tempest-share-description")
        cls.share = cls.create_share(
            name=cls.share_name,
            description=cls.share_desc,
            share_type_id=cls.share_type_id,
        )
        cls.share_id = cls.share["id"]

        # create snapshot
        cls.snap_name = data_utils.rand_name("tempest-snapshot-name")
        cls.snap_desc = data_utils.rand_name(
            "tempest-snapshot-description")
        cls.snap = cls.create_snapshot_wait_for_active(
            cls.share_id, cls.snap_name, cls.snap_desc)
        cls.snap_id = cls.snap['id']

    def _verify_snapshot_metadata(self, snapshot, md):

        # get metadata of snapshot
        metadata = self.shares_v2_client.get_metadata(
            snapshot['id'], resource="snapshot")['metadata']

        # verify metadata
        self.assertEqual(md, metadata)

        # verify metadata items
        for key in md:
            get_value = self.shares_v2_client.get_metadata_item(
                snapshot['id'], key, resource="snapshot")
            self.assertEqual(md[key], get_value[key])

    @decorators.idempotent_id('5d537913-ce6f-4771-beb2-84e2390b06d3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_in_snapshot_creation(self):

        md = {u"key1": u"value1", u"key2": u"value2", }

        # create snapshot with metadata
        snapshot = self.create_snapshot_wait_for_active(
            share_id=self.share_id, metadata=md,
            cleanup_in_class=False)

        # verify metadata
        self._verify_snapshot_metadata(snapshot, md)

    @decorators.idempotent_id('7cbdf3c5-fb72-4ea5-9e60-ba50bad68ee9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_get_delete_metadata(self):

        md = {u"key3": u"value3", u"key4": u"value4", u"key.5.1": u"value.5"}

        # create snapshot
        snapshot = self.create_snapshot_wait_for_active(
            share_id=self.share_id,
            cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(
            snapshot['id'], md, resource="snapshot")

        # verify metadata
        self._verify_snapshot_metadata(snapshot, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(
                snapshot['id'], key, resource="snapshot")

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            snapshot['id'], resource="snapshot")['metadata']
        self.assertEmpty(get_metadata)

    @decorators.idempotent_id('23ec837d-1b50-499c-bbb9-a7bde843c9e8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_not_delete_pre_metadata(self):
        md1 = {u"key9": u"value9", u"key10": u"value10", }
        md2 = {u"key11": u"value11", u"key12": u"value12", }

        # create snapshot
        snapshot = self.create_snapshot_wait_for_active(
            share_id=self.share_id,
            cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(
            snapshot['id'], md1, resource="snapshot")

        # verify metadata
        self._verify_snapshot_metadata(snapshot, md1)

        # set metadata again
        self.shares_v2_client.set_metadata(
            snapshot['id'], md2, resource="snapshot")

        # verify metadata
        md1.update(md2)
        md = md1

        # verify metadata
        self._verify_snapshot_metadata(snapshot, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(
                snapshot['id'], key, resource="snapshot")

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            snapshot['id'], resource="snapshot")['metadata']
        self.assertEmpty(get_metadata)

    @decorators.idempotent_id('b7a00be5-3dd1-4d25-8723-c662581c923f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_key_already_exist(self):
        md1 = {u"key9": u"value9", u"key10": u"value10", }
        md2 = {u"key9": u"value13", u"key11": u"value11", }

        # create snapshot
        snapshot = self.create_snapshot_wait_for_active(
            share_id=self.share_id,
            cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(
            snapshot['id'], md1, resource="snapshot")

        # verify metadata
        self._verify_snapshot_metadata(snapshot, md1)

        # set metadata again
        self.shares_v2_client.set_metadata(
            snapshot['id'], md2, resource="snapshot")

        # verify metadata
        md1.update(md2)
        self._verify_snapshot_metadata(snapshot, md1)

        # delete metadata
        for key in md1.keys():
            self.shares_v2_client.delete_metadata(
                snapshot['id'], key, resource="snapshot")

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            snapshot['id'], resource="snapshot")['metadata']
        self.assertEmpty(get_metadata)

    @decorators.idempotent_id('90120310-07a9-43f4-9d5e-38d0a3f2f5bb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_and_update_metadata_by_key(self):

        md1 = {u"key5": u"value5", u"key6": u"value6", }
        md2 = {u"key7": u"value7", u"key8": u"value8", }

        # create snapshot
        snapshot = self.create_snapshot_wait_for_active(
            share_id=self.share_id,
            cleanup_in_class=False)

        # set metadata
        self.shares_v2_client.set_metadata(
            snapshot['id'], md1, resource="snapshot")

        # update metadata
        self.shares_v2_client.update_all_metadata(
            snapshot['id'], md2, resource="snapshot")

        # verify metadata
        self._verify_snapshot_metadata(snapshot, md2)

    @decorators.idempotent_id('8963b7ae-db3a-476e-b0c7-29023e7aa321')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_v2_client.set_metadata(self.snap_id,
                                           data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data['k'], body_get.get('k'))

    @decorators.idempotent_id('dc226070-5820-4df2-a30a-9dfb2f037a4b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_v2_client.set_metadata(self.snap_id,
                                           data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertIn(max_key, body_get)
        self.assertEqual(data[max_key], body_get.get(max_key))

    @decorators.idempotent_id('940c283f-4f43-4122-86e8-32230da81886')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_v2_client.set_metadata(self.snap_id,
                                           data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('85c480bc-0ffa-43e1-bc0a-284c5641996d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_v2_client.set_metadata(self.snap_id,
                                           data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('c42335ae-ee90-4b73-b022-51c0a9bc301d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_v2_client.update_all_metadata(self.snap_id,
                                                  data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data, body_get)

    @decorators.idempotent_id('1b5f06b0-bbff-49d1-8a4b-6e912039e2ba')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_v2_client.update_all_metadata(self.snap_id,
                                                  data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data, body_get)

    @decorators.idempotent_id('849fdcd4-9b4c-4aea-833a-240d7d06966b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_v2_client.update_all_metadata(self.snap_id,
                                                  data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data, body_get)

    @decorators.idempotent_id('fdfbe469-6403-41de-b909-c4c13fc57407')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_upd_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_v2_client.update_all_metadata(self.snap_id,
                                                  data, resource="snapshot")

        body_get = self.shares_v2_client.get_metadata(
            self.snap_id, resource="snapshot")['metadata']
        self.assertEqual(data, body_get)
