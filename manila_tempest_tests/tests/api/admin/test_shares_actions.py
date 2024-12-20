# Copyright 2014 Mirantis Inc.  All Rights Reserved.
# Copyright (c) 2015 Yogesh Kshirsagar.  All rights reserved.
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

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class SharesActionsAdminTest(base.BaseSharesAdminTest):
    """Covers share functionality, that doesn't related to share type."""

    @classmethod
    def resource_setup(cls):
        super(SharesActionsAdminTest, cls).resource_setup()

        cls.shares = []

        # create share type for share filtering purposes
        specs = {"storage_protocol": CONF.share.capability_storage_protocol}
        if CONF.share.capability_snapshot_support:
            specs.update({'snapshot_support': True})
        if CONF.share.capability_create_share_from_snapshot_support:
            specs.update({'create_share_from_snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=specs)
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
                    share_type_id=cls.share_type_id,
                ))

    @decorators.idempotent_id('5f61f5dd-891e-478f-b102-803096820882')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share(self):

        # get share
        share = self.shares_client.get_share(self.shares[0]['id'])['share']

        # verify keys
        expected_keys = ["status", "description", "links", "availability_zone",
                         "created_at", "export_location", "share_proto",
                         "name", "snapshot_id", "id", "size"]
        actual_keys = share.keys()
        [self.assertIn(key, actual_keys) for key in expected_keys]

        # verify values
        msg = "Expected name: '%s', actual name: '%s'" % (self.share_name,
                                                          share["name"])
        self.assertEqual(self.share_name, str(share["name"]), msg)

        msg = ("Expected description: '%s', "
               "actual description: '%s'" % (self.share_desc,
                                             share["description"]))
        self.assertEqual(self.share_desc, str(share["description"]), msg)

        msg = "Expected size: '%s', actual size: '%s'" % (
            CONF.share.share_size, share["size"])
        self.assertEqual(CONF.share.share_size, int(share["size"]), msg)

    @decorators.idempotent_id('60d34573-8452-47ab-9455-0067bdd3ed9c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares(self):

        # list shares
        shares = self.shares_client.list_shares()['shares']

        # verify keys
        keys = ["name", "id", "links"]
        [self.assertIn(key, sh.keys()) for sh in shares for key in keys]

        # our share id in list and have no duplicates
        for share in self.shares:
            gen = [sid["id"] for sid in shares if sid["id"] in share["id"]]
            msg = "expected id lists %s times in share list" % (len(gen))
            self.assertEqual(1, len(gen), msg)

    @decorators.idempotent_id('85f9438d-d3f6-4f3a-8134-e89915373df3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail(self):

        # list shares
        shares = self.shares_client.list_shares_with_detail()['shares']

        # verify keys
        keys = [
            "status", "description", "links", "availability_zone",
            "created_at", "export_location", "share_proto", "host",
            "name", "snapshot_id", "id", "size", "project_id",
        ]
        [self.assertIn(key, sh.keys()) for sh in shares for key in keys]

        # our shares in list and have no duplicates
        for share in self.shares:
            gen = [sid["id"] for sid in shares if sid["id"] in share["id"]]
            msg = "expected id lists %s times in share list" % (len(gen))
            self.assertEqual(1, len(gen), msg)

    @decorators.idempotent_id('47dad08b-0c36-428f-8ab9-5eba92ffc995')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_metadata(self):
        filters = {'metadata': self.metadata}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertLessEqual(filters['metadata'].items(),
                                 share['metadata'].items())
        if CONF.share.capability_create_share_from_snapshot_support:
            self.assertFalse(self.shares[1]['id'] in [s['id'] for s in shares])

    @decorators.idempotent_id('d884c91e-88f5-4e42-83d9-ec3b440af893')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_extra_specs(self):
        filters = {
            "extra_specs": {
                "storage_protocol": CONF.share.capability_storage_protocol,
            }
        }
        share_type_list = self.shares_client.list_share_types()["share_types"]

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        shares_ids = [s["id"] for s in shares]
        for share in self.shares:
            self.assertIn(share["id"], shares_ids)
        for share in shares:
            # find its name or id, get id
            st_id = None
            for st in share_type_list:
                if share["share_type"] in (st["id"], st["name"]):
                    st_id = st["id"]
                    break
            if st_id is None:
                raise ValueError(
                    "Share '%(s_id)s' listed with extra_specs filter has "
                    "nonexistent share type '%(st)s'." % {
                        "s_id": share["id"], "st": share["share_type"]}
                )
            extra_specs = self.shares_client.get_share_type_extra_specs(
                st_id)['extra_specs']
            self.assertLessEqual(filters["extra_specs"].items(),
                                 extra_specs.items())

    @decorators.idempotent_id('76fbe8ba-f1d3-4446-b9b8-55617762a2c7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_share_type_id(self):
        filters = {'share_type_id': self.share_type_id}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        for share in shares:
            st_list = self.shares_client.list_share_types()
            # find its name or id, get id
            sts = st_list["share_types"]
            st_id = None
            for st in sts:
                if share["share_type"] in [st["id"], st["name"]]:
                    st_id = st["id"]
                    break
            if st_id is None:
                raise ValueError(
                    "Share '%(s_id)s' listed with share_type_id filter has "
                    "nonexistent share type '%(st)s'." % {
                        "s_id": share["id"], "st": share["share_type"]}
                )
            self.assertEqual(
                filters['share_type_id'], st_id)
        share_ids = [share['id'] for share in shares]
        for share in self.shares:
            self.assertIn(share['id'], share_ids)

    @decorators.idempotent_id('04afc330-78ee-494f-a660-7670c877a440')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_host(self):
        base_share = self.shares_client.get_share(
            self.shares[0]['id'])['share']
        filters = {'host': base_share['host']}

        # list shares
        shares = self.shares_client.list_shares_with_detail(
            params=filters)['shares']

        # verify response
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertEqual(filters['host'], share['host'])

    @utils.skip_if_microversion_not_supported("2.35")
    @ddt.data(('path', True), ('id', True), ('path', False), ('id', False))
    @ddt.unpack
    @decorators.idempotent_id('a27e5e3f-451f-4200-af38-99a562ccbe86')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_or_with_detail_filter_by_export_location(
            self, export_location_type, enable_detail):
        export_locations = self.shares_v2_client.list_share_export_locations(
            self.shares[0]['id'])['export_locations']
        if not isinstance(export_locations, (list, tuple, set)):
            export_locations = (export_locations, )

        filters = {
            'export_location_' + export_location_type:
                export_locations[0][export_location_type],
        }
        # list shares
        if enable_detail:
            shares = self.shares_v2_client.list_shares_with_detail(
                params=filters)['shares']
        else:
            shares = self.shares_v2_client.list_shares(
                params=filters)['shares']

        # verify response
        self.assertEqual(1, len(shares))
        self.assertEqual(self.shares[0]['id'], shares[0]['id'])

    @decorators.idempotent_id('4582de51-1dcd-4c44-b550-eca9a9685038')
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

    @decorators.idempotent_id('645aebc4-55ac-406d-b7ab-5614c4fc12e6')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
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

    @decorators.idempotent_id('87659cee-4692-412a-9bfe-06fc97d30ba0')
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

    @decorators.idempotent_id('631f4226-f1ea-47b1-a472-8f12da2d05c4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_existed_name(self):
        # list shares by name, at least one share is expected
        params = {"name": self.share_name}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertEqual(self.share_name, shares[0]["name"])

    @decorators.idempotent_id('d0dae9e5-a826-48e4-b7b7-24b08ad5a7cb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_fake_name(self):
        # list shares by fake name, no shares are expected
        params = {"name": data_utils.rand_name("fake-nonexistent-name")}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('8eac9b63-666f-4c52-8c5f-58b1fdf201e2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_active_status(self):
        # list shares by active status, at least one share is expected
        params = {"status": "available"}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertGreater(len(shares), 0)
        for share in shares:
            self.assertEqual(params["status"], share["status"])

    @decorators.idempotent_id('e94f41c0-f6c4-4d77-b4f9-2c796c27e348')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_shares_with_detail_filter_by_fake_status(self):
        # list shares by fake status, no shares are expected
        params = {"status": 'fake'}
        shares = self.shares_client.list_shares_with_detail(params)['shares']
        self.assertEqual(0, len(shares))

    @decorators.idempotent_id('d24a438e-4622-48ac-993e-a30d04746745')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_get_snapshot(self):

        # get snapshot
        get = self.shares_client.get_snapshot(self.snap["id"])['snapshot']

        # verify keys
        expected_keys = ["status", "links", "share_id", "name",
                         "share_proto", "created_at",
                         "description", "id", "share_size"]
        actual_keys = get.keys()
        [self.assertIn(key, actual_keys) for key in expected_keys]

        # verify data
        msg = "Expected name: '%s', actual name: '%s'" % (self.snap_name,
                                                          get["name"])
        self.assertEqual(self.snap_name, get["name"], msg)

        msg = ("Expected description: '%s', "
               "actual description: '%s'" % (self.snap_desc,
                                             get["description"]))
        self.assertEqual(self.snap_desc, get["description"], msg)

        msg = ("Expected share_id: '%s', "
               "actual share_id: '%s'" % (self.shares[0]["id"],
                                          get["share_id"]))
        self.assertEqual(self.shares[0]["id"], get["share_id"], msg)

    @decorators.idempotent_id('9fae88a5-dd95-40ba-96e2-ac3694cf455f')
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

    @decorators.idempotent_id('84013334-5985-4067-8b54-4c633f6022f3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_list_snapshots_with_detail(self):

        # list share snapshots
        snaps = self.shares_client.list_snapshots_with_detail()['snapshots']

        # verify keys
        keys = ["status", "links", "share_id", "name",
                "share_proto", "created_at",
                "description", "id", "share_size"]
        [self.assertIn(key, sn.keys()) for sn in snaps for key in keys]

        # our share id in list and have no duplicates
        gen = [sid["id"] for sid in snaps if sid["id"] in self.snap["id"]]
        msg = "expected id lists %s times in share list" % (len(gen))
        self.assertEqual(1, len(gen), msg)
