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


@ddt.ddt
class ShareSnapshotMetadataNegativeTest(base.BaseSharesMixedTest):
    @classmethod
    def skip_checks(cls):
        super(ShareSnapshotMetadataNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.73")
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')

    @classmethod
    def resource_setup(cls):
        super(ShareSnapshotMetadataNegativeTest, cls).resource_setup()
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
        cls.metadata = {
            'foo_key_share_1': 'foo_value_share_1',
            'bar_key_share_1': 'foo_value_share_1',
        }
        cls.share = cls.create_share(
            name=cls.share_name,
            description=cls.share_desc,
            metadata=cls.metadata,
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

    @decorators.idempotent_id('8be4773b-6af9-413f-97e2-8acdb6149e7a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_metadata_to_unexisting_snapshot(self):
        md = {u"key1": u"value1", u"key2": u"value2", }
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.set_metadata,
                          "wrong_snapshot_id", md, resource="snapshot")

    @decorators.idempotent_id('03a7f6e9-de8b-4669-87e1-b179308b477d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_all_metadata_to_unexisting_snapshot(self):
        md = {u"key1": u"value1", u"key2": u"value2", }
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.update_all_metadata,
                          "wrong_snapshot_id", md, resource="snapshot")

    @decorators.idempotent_id('ef0afcc8-7b12-41bc-8aa1-4916ad4b4560')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_set_metadata_with_empty_key(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.set_metadata,
                          self.snap_id, {"": "value"}, resource="snapshot")

    @decorators.idempotent_id('9f2aee7c-ebd6-4516-87f7-bd85453d74c9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_upd_metadata_with_empty_key(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_all_metadata,
                          self.snap_id, {"": "value"}, resource="snapshot")

    @decorators.idempotent_id('ef61255e-462c-49fe-8e94-ff3afafcccb3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_set_metadata_with_too_big_key(self):
        too_big_key = "x" * 256
        md = {too_big_key: "value"}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.set_metadata,
                          self.snap_id, md, resource="snapshot")

    @decorators.idempotent_id('f896f354-6179-4abb-b0c5-7b7dc96f0870')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_upd_metadata_with_too_big_key(self):
        too_big_key = "x" * 256
        md = {too_big_key: "value"}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_all_metadata,
                          self.snap_id, md, resource="snapshot")

    @decorators.idempotent_id('1bf97c18-27df-4618-94f4-224d1a98bc0c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_set_metadata_with_too_big_value(self):
        too_big_value = "x" * 1024
        md = {"key": too_big_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.set_metadata,
                          self.snap_id, md, resource="snapshot")

    @decorators.idempotent_id('2b9e08fa-b35d-4bfe-9137-e59ab50bd9ef')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_upd_metadata_with_too_big_value(self):
        too_big_value = "x" * 1024
        md = {"key": too_big_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_all_metadata,
                          self.snap_id, md, resource="snapshot")

    @decorators.idempotent_id('9afb381d-c48c-4c2c-a5b5-42463daef5a2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_delete_unexisting_metadata(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_metadata,
                          self.snap_id, "wrong_key", resource="snapshot")
