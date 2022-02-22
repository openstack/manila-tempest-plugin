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
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class SharesActionsTest(base.BaseSharesMixedTest):
    """Covers share functionality, that doesn't related to share type."""

    @classmethod
    def resource_setup(cls):
        super(SharesActionsTest, cls).resource_setup()

        cls.shares = []

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
        cls.shares.append(cls.create_share(
            name=cls.share_name,
            description=cls.share_desc,
            metadata=cls.metadata,
            share_type_id=cls.share_type_id,
        ))

        if CONF.share.run_snapshot_tests:
            # create snapshot
            cls.snap_name = data_utils.rand_name("tempest-snapshot-name")
            cls.snap_desc = data_utils.rand_name(
                "tempest-snapshot-description")
            cls.snap = cls.create_snapshot_wait_for_active(
                cls.shares[0]["id"], cls.snap_name, cls.snap_desc)

            if CONF.share.capability_create_share_from_snapshot_support:

                # create second share from snapshot for purposes of sorting and
                # snapshot filtering
                cls.share_name2 = data_utils.rand_name("tempest-share-name")
                cls.share_desc2 = data_utils.rand_name(
                    "tempest-share-description")
                cls.metadata2 = {
                    'foo_key_share_2': 'foo_value_share_2',
                    'bar_key_share_2': 'foo_value_share_2',
                }
                cls.shares.append(cls.create_share(
                    name=cls.share_name2,
                    description=cls.share_desc2,
                    metadata=cls.metadata2,
                    snapshot_id=cls.snap['id'],
                ))

    def _get_share(self, version):

        # get share
        share = self.shares_v2_client.get_share(
            self.shares[0]['id'], version=str(version))['share']

        # verify keys
        expected_keys = [
            "status", "description", "links", "availability_zone",
            "created_at", "project_id", "volume_type", "share_proto", "name",
            "snapshot_id", "id", "size", "share_network_id", "metadata",
            "snapshot_id", "is_public",
        ]
        if utils.is_microversion_lt(version, '2.9'):
            expected_keys.extend(["export_location", "export_locations"])
        if utils.is_microversion_ge(version, '2.2'):
            expected_keys.append("snapshot_support")
        if utils.is_microversion_ge(version, '2.5'):
            expected_keys.append("share_type_name")
        if utils.is_microversion_ge(version, '2.10'):
            expected_keys.append("access_rules_status")
        if utils.is_microversion_ge(version, '2.11'):
            expected_keys.append("replication_type")
        if utils.is_microversion_ge(version, '2.16'):
            expected_keys.append("user_id")
        if utils.is_microversion_ge(version, '2.24'):
            expected_keys.append("create_share_from_snapshot_support")
        if utils.is_microversion_ge(version,
                                    constants.REVERT_TO_SNAPSHOT_MICROVERSION):
            expected_keys.append("revert_to_snapshot_support")
        actual_keys = list(share.keys())
        [self.assertIn(key, actual_keys) for key in expected_keys]

        # verify values
        msg = "Expected name: '%s', actual name: '%s'" % (self.share_name,
                                                          share["name"])
        self.assertEqual(self.share_name, str(share["name"]), msg)

        msg = ("Expected description: '%s', "
               "actual description: '%s'" % (self.share_desc,
                                             share["description"]))
        self.assertEqual(
            self.share_desc, str(share["description"]), msg)

        msg = "Expected size: '%s', actual size: '%s'" % (
            CONF.share.share_size, share["size"])
        self.assertEqual(CONF.share.share_size, int(share["size"]), msg)

    @decorators.idempotent_id('188badb2-0ca3-44e5-abca-3029475d7f73')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_v2_1(self):
        self._get_share('2.1')

    @decorators.idempotent_id('45ec8e36-cb8a-4a03-8c41-ba5d5dc2a5c5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_with_snapshot_support_key(self):
        self._get_share('2.2')

    @decorators.idempotent_id('b803a076-593a-469d-ab75-7e67ac294dd5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.6')
    def test_get_share_with_share_type_name_key(self):
        self._get_share('2.6')

    @decorators.idempotent_id('c13c1cf5-c708-4e62-8b71-c47dbb45a7a0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.9')
    def test_get_share_export_locations_removed(self):
        self._get_share('2.9')

    @decorators.idempotent_id('2c439716-c34e-46f1-b055-41e411fb4e66')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.10')
    def test_get_share_with_access_rules_status(self):
        self._get_share('2.10')

    @decorators.idempotent_id('67c9ad27-f26d-4ff9-a528-a35b4c5a55c1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.11')
    def test_get_share_with_replication_type_key(self):
        self._get_share('2.11')

    @decorators.idempotent_id('2a61703d-5a62-49c5-b143-fea0c9125cd9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.16')
    def test_get_share_with_user_id(self):
        self._get_share('2.16')

    @decorators.idempotent_id('2899055e-607d-4423-b1b7-27eefa6ce5f0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.24')
    def test_get_share_with_create_share_from_snapshot_support(self):
        self._get_share('2.24')

    @decorators.idempotent_id('04c359b5-74b3-4a07-9f9e-f0ac1867d58d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported(
        constants.REVERT_TO_SNAPSHOT_MICROVERSION)
    def test_get_share_with_revert_to_snapshot_support(self):
        self._get_share(constants.REVERT_TO_SNAPSHOT_MICROVERSION)

    @decorators.idempotent_id('7d61311a-81b0-481c-abb9-cfb0b4f82e29')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares(self):

        # list shares
        shares = self.shares_v2_client.list_shares()['shares']

        # verify keys
        keys = ["name", "id", "links"]
        [self.assertIn(key, sh.keys()) for sh in shares for key in keys]

        # our share id in list and have no duplicates
        for share in self.shares:
            gen = [sid["id"] for sid in shares if sid["id"] in share["id"]]
            msg = "expected id lists %s times in share list" % (len(gen))
            self.assertEqual(1, len(gen), msg)

    def _list_shares_with_detail(self, version):

        # list shares
        shares = self.shares_v2_client.list_shares_with_detail(
            version=str(version))['shares']

        # verify keys
        keys = [
            "status", "description", "links", "availability_zone",
            "created_at", "project_id", "volume_type", "share_proto", "name",
            "snapshot_id", "id", "size", "share_network_id", "metadata",
            "snapshot_id", "is_public", "share_type",
        ]
        if utils.is_microversion_lt(version, '2.9'):
            keys.extend(["export_location", "export_locations"])
        if utils.is_microversion_ge(version, '2.2'):
            keys.append("snapshot_support")
        if utils.is_microversion_ge(version, '2.6'):
            keys.append("share_type_name")
        if utils.is_microversion_ge(version, '2.10'):
            keys.append("access_rules_status")
        if utils.is_microversion_ge(version, '2.11'):
            keys.append("replication_type")
        if utils.is_microversion_ge(version, '2.16'):
            keys.append("user_id")
        if utils.is_microversion_ge(version, '2.24'):
            keys.append("create_share_from_snapshot_support")
        if utils.is_microversion_ge(version,
                                    constants.REVERT_TO_SNAPSHOT_MICROVERSION):
            keys.append("revert_to_snapshot_support")
        [self.assertIn(key, sh.keys()) for sh in shares for key in keys]

        # our shares in list and have no duplicates
        for share in self.shares:
            gen = [sid["id"] for sid in shares if sid["id"] in share["id"]]
            msg = "expected id lists %s times in share list" % (len(gen))
            self.assertEqual(1, len(gen), msg)

    @decorators.idempotent_id('d88a157a-fe4d-456e-90ba-f0bd9e5d02ec')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_v2_1(self):
        self._list_shares_with_detail('2.1')

    @decorators.idempotent_id('ee57db25-0fbf-40ce-8dc1-070845d245a7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_and_snapshot_support_key(self):
        self._list_shares_with_detail('2.2')

    @decorators.idempotent_id('38a4cf70-8ed9-4a82-a338-9f20463b1147')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.6')
    def test_list_shares_with_detail_share_type_name_key(self):
        self._list_shares_with_detail('2.6')

    @decorators.idempotent_id('a313cd85-53e5-48b7-b4a7-14e9273e843d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.9')
    def test_list_shares_with_detail_export_locations_removed(self):
        self._list_shares_with_detail('2.9')

    @decorators.idempotent_id('0de4dc84-bace-4b9a-8470-a40c4a9b14b4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.10')
    def test_list_shares_with_detail_with_access_rules_status(self):
        self._list_shares_with_detail('2.10')

    @decorators.idempotent_id('70097cf3-76b8-49d2-b1c7-ad59394dd978')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.11')
    def test_list_shares_with_detail_replication_type_key(self):
        self._list_shares_with_detail('2.11')

    @decorators.idempotent_id('f8e57190-b105-4937-b96e-55725eb64739')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.16')
    def test_list_shares_with_user_id(self):
        self._list_shares_with_detail('2.16')

    @decorators.idempotent_id('21410324-e0b5-452a-8c7e-599a27267e1d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_and_create_share_from_snapshot_support(
            self):
        self._list_shares_with_detail('2.24')

    @decorators.idempotent_id('45041fc9-bb0d-4dd6-ac0d-a40a22a91f3f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported(
        constants.REVERT_TO_SNAPSHOT_MICROVERSION)
    def test_list_shares_with_detail_with_revert_to_snapshot_support(self):
        self._list_shares_with_detail(
            constants.REVERT_TO_SNAPSHOT_MICROVERSION)

    @decorators.idempotent_id('bc24dc42-050b-4105-a90a-f5649cbd8e49')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_metadata(self):
        filters = {'metadata': self.metadata}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertDictContainsSubset(
                filters['metadata'], share['metadata'])
        if CONF.share.capability_create_share_from_snapshot_support:
            self.assertFalse(self.shares[1]['id'] in [s['id'] for s in shares])

    @decorators.idempotent_id('685286c7-1df6-48c3-839d-8162737446b8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_list_shares_with_detail_filter_by_share_network_id(self):
        base_share = self.shares_client.get_share(
            self.shares[0]['id'])['share']
        filters = {'share_network_id': base_share['share_network_id']}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertEqual(
                filters['share_network_id'], share['share_network_id'])

    @decorators.idempotent_id('fd87884d-71a4-4ca8-8b2b-07b4df2de3bd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_list_shares_with_detail_filter_by_snapshot_id(self):
        filters = {'snapshot_id': self.snap['id']}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertEqual(filters['snapshot_id'], share['snapshot_id'])
        self.assertFalse(self.shares[0]['id'] in [s['id'] for s in shares])

    @decorators.idempotent_id('70a9d947-bd45-46db-b529-6c48c0ff8985')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_with_asc_sorting(self):
        filters = {'sort_key': 'created_at', 'sort_dir': 'asc'}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        sorted_list = [share['created_at'] for share in shares]
        self.assertEqual(sorted(sorted_list), sorted_list)

    @decorators.idempotent_id('866194c6-3910-409e-ad81-2cff223cfaaf')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_existed_name(self):
        # list shares by name, at least one share is expected
        params = {"name": self.share_name}
        shares = self.shares_client.list_shares_with_detail(
            params)['shares']
        self.assertEqual(self.share_name, shares[0]["name"])

    @decorators.idempotent_id('f446e8cb-5bef-45ac-8b87-f4136f44ca69')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_shares_with_detail_filter_by_existed_description(self):
        # list shares by description, at least one share is expected
        params = {"description": self.share_desc}
        shares = self.shares_v2_client.list_shares_with_detail(
            params)['shares']
        self.assertEqual(self.share_name, shares[0]["name"])

    @decorators.idempotent_id('1276b97b-cf46-4953-973f-f995985a1ce4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.36")
    def test_list_shares_with_detail_filter_by_inexact_name(self):
        # list shares by name, at least one share is expected
        params = {"name~": 'tempest-share'}
        shares = self.shares_v2_client.list_shares_with_detail(
            params)['shares']
        for share in shares:
            self.assertIn('tempest-share', share["name"])

    @decorators.idempotent_id('56416b95-949f-4b09-9a5e-377b674efd25')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_fake_name(self):
        # list shares by fake name, no shares are expected
        params = {"name": data_utils.rand_name("fake-nonexistent-name")}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('708e3e2e-8761-4d16-b18d-a834ee7ca69e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_active_status(self):
        # list shares by active status, at least one share is expected
        params = {"status": "available"}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertEqual(params["status"], share["status"])

    @decorators.idempotent_id('5ec2fcf8-18d4-4790-95de-45c8a05582c7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_fake_status(self):
        # list shares by fake status, no shares are expected
        params = {"status": 'fake'}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('7609b7bb-613e-474d-a9b3-e41584842503')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_all_tenants(self):
        # non-admin user can get shares only from his project
        params = {"all_tenants": 1}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertGreater(len(shares), 0)

        # get share with detailed info, we need its 'project_id'
        share = self.shares_client.get_share(self.shares[0]["id"])['share']
        project_id = share["project_id"]
        for share in shares:
            self.assertEqual(project_id, share["project_id"])

    @decorators.idempotent_id('0019afa2-fae2-417f-a7e0-2af665a966b0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.42")
    def test_list_shares_with_detail_with_count(self):
        # list shares by name, at least one share is expected
        params = {"with_count": 'true'}
        shares = self.shares_v2_client.list_shares_with_detail(params)
        self.assertGreater(shares["count"], 0)

    @decorators.idempotent_id('174829eb-fd3e-46ef-880b-f05c3d44d1fe')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @ddt.data(None, '2.16', LATEST_MICROVERSION)
    def test_get_snapshot(self, version):

        # get snapshot
        if version is None:
            snapshot = self.shares_client.get_snapshot(
                self.snap["id"])['snapshot']
        else:
            utils.check_skip_if_microversion_not_supported(version)
            snapshot = self.shares_v2_client.get_snapshot(
                self.snap["id"], version=version)['snapshot']

        # verify keys
        expected_keys = ["status", "links", "share_id", "name",
                         "share_proto", "created_at",
                         "description", "id", "share_size", "size"]
        if version and utils.is_microversion_ge(version, '2.17'):
            expected_keys.extend(["user_id", "project_id"])
        actual_keys = snapshot.keys()

        # strict key check
        self.assertEqual(set(expected_keys), set(actual_keys))

        # verify data
        msg = "Expected name: '%s', actual name: '%s'" % (self.snap_name,
                                                          snapshot["name"])
        self.assertEqual(self.snap_name, snapshot["name"], msg)

        msg = ("Expected description: '%s' actual description: '%s'" %
               (self.snap_desc, snapshot["description"]))
        self.assertEqual(self.snap_desc, snapshot["description"], msg)

        msg = ("Expected share_id: '%s', actual share_id: '%s'" %
               (self.shares[0]["id"], snapshot["share_id"]))
        self.assertEqual(self.shares[0]["id"], snapshot["share_id"], msg)

        # Verify that the user_id and project_id are same as the one for
        # the base share
        if version and utils.is_microversion_ge(version, '2.17'):
            msg = ("Expected %(key)s in snapshot: '%(expected)s', "
                   "actual %(key)s in snapshot: '%(actual)s'")
            self.assertEqual(self.shares[0]['user_id'],
                             snapshot['user_id'],
                             msg % {
                                 'expected': self.shares[0]['user_id'],
                                 'actual': snapshot['user_id'],
                                 'key': 'user_id'})
            self.assertEqual(self.shares[0]['project_id'],
                             snapshot['project_id'],
                             msg % {
                                 'expected': self.shares[0]['project_id'],
                                 'actual': snapshot['project_id'],
                                 'key': 'project_id'})

    @decorators.idempotent_id('3d5d85ff-6158-4af2-a765-cfa07a46adde')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_list_snapshots(self):

        # list share snapshots
        snaps = self.shares_client.list_snapshots()['snapshots']

        # verify keys
        keys = ["id", "name", "links"]
        [self.assertIn(key, sn.keys()) for sn in snaps for key in keys]

        # our share id in list and have no duplicates
        gen = [sid["id"] for sid in snaps if sid["id"] in self.snap["id"]]
        msg = "expected id lists %s times in share list" % (len(gen))
        self.assertEqual(1, len(gen), msg)

    @decorators.idempotent_id('4d717665-e4ca-47df-b4b9-f6d096159779')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @ddt.data(None, '2.16', '2.36', LATEST_MICROVERSION)
    def test_list_snapshots_with_detail(self, version):
        params = None
        if version and utils.is_microversion_ge(version, '2.36'):
            params = {'name~': 'tempest', 'description~': 'tempest'}
        # list share snapshots
        if version is None:
            snaps = self.shares_client.list_snapshots_with_detail(
                )['snapshots']
        else:
            utils.check_skip_if_microversion_not_supported(version)
            snaps = self.shares_v2_client.list_snapshots_with_detail(
                version=version, params=params)['snapshots']

        # verify keys
        expected_keys = ["status", "links", "share_id", "name",
                         "share_proto", "created_at", "description", "id",
                         "share_size", "size"]
        if version and utils.is_microversion_ge(version, '2.17'):
            expected_keys.extend(["user_id", "project_id"])

        # strict key check
        [self.assertEqual(set(expected_keys), set(s.keys())) for s in snaps]

        # our share id in list and have no duplicates
        gen = [sid["id"] for sid in snaps if sid["id"] in self.snap["id"]]
        msg = "expected id lists %s times in share list" % (len(gen))
        self.assertEqual(1, len(gen), msg)

    @decorators.idempotent_id('80497a21-7533-47b5-93aa-29e0f7924cb9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_list_snapshots_with_detail_use_limit(self):
        for limit, offset in [('1', '1'), ('0', '1')]:
            filters = {
                'limit': limit,
                'offset': offset,
                'share_id': self.shares[0]['id'],
            }

            # list snapshots
            snaps = self.shares_client.list_snapshots_with_detail(
                params=filters)['snapshots']

            # Our snapshot should not be listed
            self.assertEqual(0, len(snaps))

        # Only our one snapshot should be listed
        snaps = self.shares_client.list_snapshots_with_detail(
            params={'limit': '1', 'offset': '0',
                    'share_id': self.shares[0]['id']})['snapshots']

        self.assertEqual(1, len(snaps))
        self.assertEqual(self.snap['id'], snaps[0]['id'])

    @decorators.idempotent_id('0a94e996-c4db-4fef-b486-4004ea65c11a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_list_snapshots_with_detail_filter_by_status_and_name(self):
        filters = {'status': 'available', 'name': self.snap_name}

        # list snapshots
        snaps = self.shares_client.list_snapshots_with_detail(
            params=filters)['snapshots']

        # verify response
        self.assertGreater(len(snaps), 0)
        for snap in snaps:
            self.assertEqual(filters['status'], snap['status'])
            self.assertEqual(filters['name'], snap['name'])

    @decorators.idempotent_id('f969aba1-d293-48e3-a638-a89785bb41ef')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @utils.skip_if_microversion_not_supported("2.35")
    def test_list_snapshots_with_detail_filter_by_description(self):
        filters = {'description': self.snap_desc}

        # list snapshots
        snaps = self.shares_client.list_snapshots_with_detail(
            params=filters)['snapshots']

        # verify response
        self.assertGreater(len(snaps), 0)
        for snap in snaps:
            self.assertEqual(filters['description'], snap['description'])

    @decorators.idempotent_id('59968026-12af-4029-a3d0-42c291b7db96')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_list_snapshots_with_detail_and_asc_sorting(self):
        filters = {'sort_key': 'share_id', 'sort_dir': 'asc'}

        # list snapshots
        snaps = self.shares_client.list_snapshots_with_detail(
            params=filters)['snapshots']

        # verify response
        self.assertGreater(len(snaps), 0)
        sorted_list = [snap['share_id'] for snap in snaps]
        self.assertEqual(sorted(sorted_list), sorted_list)

    @decorators.idempotent_id('17e6f579-e0d7-4724-a639-4974e82bb5ed')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    def test_extend_share(self):
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)
        new_size = int(share['size']) + 1

        # extend share and wait for active status
        self.shares_v2_client.extend_share(share['id'], new_size)
        waiters.wait_for_resource_status(
            self.shares_client, share['id'], 'available')

        # check state and new size
        share_get = self.shares_v2_client.get_share(share['id'])['share']
        msg = (
            "Share could not be extended. "
            "Expected %(expected)s, got %(actual)s." % {
                "expected": new_size,
                "actual": share_get['size'],
            }
        )
        self.assertEqual(new_size, share_get['size'], msg)

    @decorators.idempotent_id('8f64b930-9b4e-41d7-bbd6-82d9951931f3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipUnless(
        CONF.share.run_shrink_tests,
        "Share shrink tests are disabled.")
    def test_shrink_share(self):
        size = CONF.share.share_size + 1
        share = self.create_share(size=size,
                                  share_type_id=self.share_type_id,
                                  cleanup_in_class=False)
        new_size = int(share['size']) - 1

        # shrink share and wait for active status
        self.shares_v2_client.shrink_share(share['id'], new_size)
        waiters.wait_for_resource_status(
            self.shares_client, share['id'], 'available')

        # check state and new size
        share_get = self.shares_v2_client.get_share(share['id'])['share']
        msg = (
            "Share could not be shrunk. "
            "Expected %(expected)s, got %(actual)s." % {
                "expected": new_size,
                "actual": share_get['size'],
            }
        )
        self.assertEqual(new_size, share_get['size'], msg)

    @utils.skip_if_microversion_not_supported("2.69")
    @decorators.idempotent_id('7a19fb58-b645-44cc-a6d7-b3508ff8754d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_soft_delete_and_restore_share(self):
        share = self.create_share(share_type_id=self.share_type_id)

        # list shares
        shares = self.shares_v2_client.list_shares()['shares']

        # check the share in share list
        share_ids = [sh['id'] for sh in shares]
        self.assertIn(share['id'], share_ids)

        # soft delete the share
        self.shares_v2_client.soft_delete_share(share['id'])
        waiters.wait_for_soft_delete(self.shares_v2_client, share['id'])

        # list shares again
        shares1 = self.shares_v2_client.list_shares()['shares']
        share_ids1 = [sh['id'] for sh in shares1]

        # list shares in recycle bin
        shares2 = self.shares_v2_client.list_shares_in_recycle_bin()['shares']
        share_ids2 = [sh['id'] for sh in shares2]

        # check share has been soft delete to recycle bin
        self.assertNotIn(share['id'], share_ids1)
        self.assertIn(share['id'], share_ids2)

        # restore share from recycle bin
        self.shares_v2_client.restore_share(share['id'])
        waiters.wait_for_restore(self.shares_v2_client, share['id'])

        # list shares again
        shares3 = self.shares_v2_client.list_shares()['shares']
        share_ids3 = [sh['id'] for sh in shares3]

        # list shares in recycle bin again
        shares4 = self.shares_v2_client.list_shares_in_recycle_bin()['shares']
        share_ids4 = [sh['id'] for sh in shares4]

        # check share has restored from recycle bin
        self.assertNotIn(share['id'], share_ids4)
        self.assertIn(share['id'], share_ids3)


class SharesRenameTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SharesRenameTest, cls).resource_setup()

        # create share_type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share_name = data_utils.rand_name("tempest-share-name")
        cls.share_desc = data_utils.rand_name("tempest-share-description")
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

    @decorators.idempotent_id('7661d042-8222-483c-9249-9f53931e7347')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_update_share(self):

        # get share
        share = self.shares_client.get_share(self.share['id'])['share']
        self.assertEqual(self.share_name, share["name"])
        self.assertEqual(self.share_desc, share["description"])
        self.assertFalse(share["is_public"])

        # update share
        new_name = data_utils.rand_name("tempest-new-name")
        new_desc = data_utils.rand_name("tempest-new-description")
        updated = self.shares_client.update_share(
            share["id"], name=new_name, desc=new_desc)['share']
        self.assertEqual(new_name, updated["name"])
        self.assertEqual(new_desc, updated["description"])

        # get share
        share = self.shares_client.get_share(self.share['id'])['share']
        self.assertEqual(new_name, share["name"])
        self.assertEqual(new_desc, share["description"])
        self.assertFalse(share["is_public"])

    @decorators.idempotent_id('20f299f6-2441-4629-b44e-d791d57f413c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_rename_snapshot(self):

        # get snapshot
        get = self.shares_client.get_snapshot(self.snap["id"])['snapshot']
        self.assertEqual(self.snap_name, get["name"])
        self.assertEqual(self.snap_desc, get["description"])

        # rename snapshot
        new_name = data_utils.rand_name("tempest-new-name-for-snapshot")
        new_desc = data_utils.rand_name("tempest-new-description-for-snapshot")
        renamed = self.shares_client.rename_snapshot(
            self.snap["id"], new_name, new_desc)['snapshot']
        self.assertEqual(new_name, renamed["name"])
        self.assertEqual(new_desc, renamed["description"])

        # get snapshot
        get = self.shares_client.get_snapshot(self.snap["id"])['snapshot']
        self.assertEqual(new_name, get["name"])
        self.assertEqual(new_desc, get["description"])
