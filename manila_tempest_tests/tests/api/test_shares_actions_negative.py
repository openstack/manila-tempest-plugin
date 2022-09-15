# Copyright 2015 Mirantis Inc.
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
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class SharesActionsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SharesActionsNegativeTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.share_name = data_utils.rand_name("tempest-share-name")
        cls.share_desc = data_utils.rand_name("tempest-share-description")
        # create share_type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(
            name=cls.share_name,
            description=cls.share_desc,
            share_type_id=cls.share_type_id)
        if CONF.share.run_snapshot_tests:
            # create snapshot
            cls.snap_name = data_utils.rand_name("tempest-snapshot-name")
            cls.snap_desc = data_utils.rand_name(
                "tempest-snapshot-description")
            cls.snap = cls.create_snapshot_wait_for_active(
                cls.share["id"], cls.snap_name, cls.snap_desc)

    @decorators.idempotent_id('c4481ba3-0cff-448b-a728-69a9a34e3aa6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    @testtools.skipUnless(
        CONF.share.run_quota_tests,
        "Quota tests are disabled.")
    def test_share_extend_over_quota(self):
        tenant_quotas = self.shares_client.show_quotas(
            self.shares_client.tenant_id)['quota_set']
        new_size = int(tenant_quotas["gigabytes"]) + 1

        # extend share with over quota and check result
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.extend_share,
                          self.share['id'],
                          new_size)

    @decorators.idempotent_id('3448cd2b-34eb-453f-b72f-39fbea778e42')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    def test_share_extend_with_less_size(self):
        new_size = int(self.share['size']) - 1

        # extend share with invalid size and check result
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.extend_share,
                          self.share['id'],
                          new_size)

    @decorators.idempotent_id('79f2304a-7959-4169-8a76-b67814e0733a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    def test_share_extend_with_same_size(self):
        new_size = int(self.share['size'])

        # extend share with invalid size and check result
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.extend_share,
                          self.share['id'],
                          new_size)

    @decorators.idempotent_id('067c4b10-4324-45ac-8365-5d446b66c18a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    def test_share_extend_with_invalid_share_state(self):
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)
        new_size = int(share['size']) + 1

        # set "error" state
        self.admin_client.reset_state(share['id'])

        # run extend operation on same share and check result
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.extend_share,
                          share['id'],
                          new_size)

    @decorators.idempotent_id('f9d2ba94-4032-d17a-b4ab-a2b67f650a39')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.64")
    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    def test_share_force_extend_non_admin_user(self):
        # only admin cloud force extend share with micversion >= 2.64
        # non-admin will get unauthorized error.
        new_size = int(self.share['size']) + 1
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.extend_share, self.share['id'],
                          new_size, force=True)

    @decorators.idempotent_id('99d42f94-8da1-4c04-ad5b-9738d6acc139')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_shrink_tests,
        "Share shrink tests are disabled.")
    def test_share_shrink_with_greater_size(self):
        new_size = int(self.share['size']) + 1

        # shrink share with invalid size and check result
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.shrink_share,
                          self.share['id'],
                          new_size)

    @decorators.idempotent_id('3d4c8f34-49b8-4628-b1cb-652ae67473a5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_shrink_tests,
        "Share shrink tests are disabled.")
    def test_share_shrink_with_same_size(self):
        new_size = int(self.share['size'])

        # shrink share with invalid size and check result
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.shrink_share,
                          self.share['id'],
                          new_size)

    @decorators.idempotent_id('d53ece5c-70e4-4953-a1d7-7d4384510519')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_shrink_tests,
        "Share shrink tests are disabled.")
    def test_share_shrink_with_invalid_share_state(self):
        size = CONF.share.share_size + 1
        share = self.create_share(share_type_id=self.share_type_id,
                                  size=size,
                                  cleanup_in_class=False)
        new_size = int(share['size']) - 1

        # set "error" state
        self.admin_client.reset_state(share['id'])

        # run shrink operation on same share and check result
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.shrink_share,
                          share['id'],
                          new_size)

    @decorators.idempotent_id('ff307c91-3bb9-48b5-926c-5a2747320151')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.34")
    @ddt.data('path', 'id')
    def test_list_shares_with_export_location_and_invalid_version(
            self, export_location_type):
        # In API versions <v2.35, querying the share API by export
        # location path or ID should have no effect. Those filters were
        # supported from v2.35
        filters = {
            'export_location_' + export_location_type: 'fake',
        }
        shares = self.shares_v2_client.list_shares(
            params=filters, version="2.34")['shares']

        self.assertGreater(len(shares), 0)

    @decorators.idempotent_id('ffc3dc76-2f92-4308-a125-1d3905ed72ba')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.35")
    @ddt.data('path', 'id')
    def test_list_shares_with_export_location_not_exist(
            self, export_location_type):
        filters = {
            'export_location_' + export_location_type: 'fake_not_exist',
        }
        shares = self.shares_v2_client.list_shares(
            params=filters)['shares']

        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('3dbcf17b-cc63-43ea-b45f-eae12300729e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_shares_with_like_filter_and_invalid_version(self):
        # In API versions < v2.36, querying the share API by inexact
        # filter (name or description) should have no effect. Those
        # filters were supported from v2.36
        filters = {
            'name~': 'fake',
            'description~': 'fake',
        }
        shares = self.shares_v2_client.list_shares(
            params=filters, version="2.35")['shares']

        self.assertGreater(len(shares), 0)

    @decorators.idempotent_id('f41c6cd2-62cf-4bba-a26e-21a6e86eae15')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_shares_with_like_filter_not_exist(self):
        filters = {
            'name~': 'fake_not_exist',
            'description~': 'fake_not_exist',
        }
        shares = self.shares_v2_client.list_shares(params=filters)['shares']

        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('31e33495-5ec3-4658-bdef-d9d1e034705a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_name_not_exist(self):
        filters = {
            'name': "tempest-share",
        }
        shares = self.shares_v2_client.list_shares(params=filters)['shares']

        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('5b0ceae1-357f-4b51-81a6-88973ea20c16')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_shares_with_description_not_exist(self):
        filters = {
            'description': "tempest-share",
        }
        shares = self.shares_v2_client.list_shares(params=filters)['shares']

        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('061ee37a-96b2-4b4f-9cfe-2c8c80ed4370')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_snapshots_with_description_not_exist(self):
        filters = {
            'description': "tempest-snapshot",
        }
        shares = self.shares_v2_client.list_snapshots_with_detail(
            params=filters)['snapshots']

        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('9d3c3158-1a92-4e37-b00f-a4a40b813109')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshots_with_name_not_exist(self):
        filters = {
            'name': "tempest-snapshot",
        }
        shares = self.shares_v2_client.list_snapshots_with_detail(
            params=filters)['snapshots']

        self.assertEqual(0, len(shares))

    @decorators.skip_because(bug='1914363')
    @decorators.idempotent_id('e8f857f1-ec32-4f81-9e09-26065891dc93')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_from_other_project(self):
        self.assertRaises(lib_exc.NotFound,
                          self.alt_shares_v2_client.get_share,
                          self.share['id'])

    @utils.skip_if_microversion_not_supported("2.69")
    @decorators.idempotent_id('36cbe23b-08d2-49d9-bb42-f9eb2a804cb1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_soft_delete_share_has_been_soft_deleted(self):
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # soft delete the share
        self.shares_v2_client.soft_delete_share(share['id'])

        # try soft delete the share again
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.soft_delete_share,
                          share['id'])

        # restore the share for resource_cleanup
        self.shares_v2_client.restore_share(share['id'])
        waiters.wait_for_restore(self.shares_v2_client, share['id'])

    @utils.skip_if_microversion_not_supported("2.69")
    @decorators.idempotent_id('cf675ac9-0970-49fc-a051-8a94555c73b5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_soft_delete_share_with_invalid_share_state(self):
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # set "error_deleting" state
        self.admin_client.reset_state(share['id'], status="error_deleting")

        # try soft delete the share
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.soft_delete_share,
                          share['id'])

        # rollback to available status
        self.admin_client.reset_state(share['id'], status="available")

    @utils.skip_if_microversion_not_supported("2.69")
    @decorators.idempotent_id('f6106ee4-1a01-444f-b623-912a5e751d49')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_soft_delete_share_from_other_project(self):
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # NOTE(gouthamr): The client used below is of a member from alt
        # project. As a fix to bug #1901210, the server responds with
        # 404 instead of 403, but we'll test for one of the two codes since
        # the test could be running against a release without the fix.
        self.assertRaises((lib_exc.Forbidden, lib_exc.NotFound),
                          self.alt_shares_v2_client.soft_delete_share,
                          share['id'])

    @utils.skip_if_microversion_not_supported("2.69")
    @decorators.idempotent_id('0ccd44dd-2fda-403e-bc23-7ce428550f36')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_soft_delete_share_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.soft_delete_share,
                          "wrong_share_id")

    @utils.skip_if_microversion_not_supported("2.69")
    @decorators.idempotent_id('87345725-f187-4d7d-86b1-62284e8c75ae')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_restore_share_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.restore_share,
                          "wrong_share_id")
