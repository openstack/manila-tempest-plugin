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
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class SharesNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SharesNegativeTest, cls).resource_setup()
        # create share_type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        if CONF.share.capability_create_share_from_snapshot_support:
            extra_specs.update({'create_share_from_snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

    @decorators.idempotent_id('b9bb8dee-0c7c-4e51-909c-028335b1a6a0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_try_delete_share_with_existing_snapshot(self):
        # share can not be deleted while snapshot exists

        # create share
        share = self.create_share(share_type_id=self.share_type_id)

        # create snapshot
        self.create_snapshot_wait_for_active(share["id"])

        # try delete share
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.delete_share, share["id"])

    @decorators.idempotent_id('3df8e2d8-9b79-428d-9d8b-30bc66b5b40e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_create_share_from_snap_with_less_size(self):
        # requires minimum 5Gb available space
        skip_msg = "Check disc space for this test"

        try:  # create share
            size = CONF.share.share_size + 1
            share = self.create_share(size=size,
                                      share_type_id=self.share_type_id,
                                      cleanup_in_class=False)
        except share_exceptions.ShareBuildErrorException:
            self.skip(skip_msg)

        try:  # create snapshot
            snap = self.create_snapshot_wait_for_active(
                share["id"], cleanup_in_class=False)
        except share_exceptions.SnapshotBuildErrorException:
            self.skip(skip_msg)

        # try create share from snapshot with less size
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share,
                          share_type_id=self.share_type_id,
                          snapshot_id=snap["id"],
                          cleanup_in_class=False)

    @decorators.idempotent_id('3047fb1c-5acc-4ef2-8796-b2d2d49829b5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(not CONF.share.multitenancy_enabled,
                      "Only for multitenancy.")
    def test_create_share_with_nonexistant_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.create_share,
                          share_type_id=self.share_type_id,
                          share_network_id="wrong_sn_id")

    @decorators.idempotent_id('e84ce567-a090-47c7-87c4-6ee427bdee7a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(not CONF.share.multitenancy_enabled,
                      "Only for multitenancy.")
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @testtools.skipUnless(
        CONF.share.capability_create_share_from_snapshot_support,
        "Create share from snapshot tests are disabled.")
    def test_create_share_from_snap_with_different_share_network(self):
        # We can't create a share from a snapshot whose base share does not
        # have 'create_share_from_snapshot_support'.

        # create share
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # get parent's share network
        parent_share = self.shares_client.get_share(share["id"])['share']
        parent_sn = self.shares_client.get_share_network(
            parent_share["share_network_id"])['share_network']

        # create new share-network - net duplicate of parent's share
        new_duplicated_sn = self.create_share_network(
            cleanup_in_class=False,
            neutron_net_id=parent_sn["neutron_net_id"],
            neutron_subnet_id=parent_sn["neutron_subnet_id"],
        )

        # create snapshot of parent share
        snap = self.create_snapshot_wait_for_active(
            share["id"], cleanup_in_class=False)

        # try create share with snapshot using another share-network
        # 400 bad request is expected
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share,
            share_type_id=self.share_type_id,
            cleanup_in_class=False,
            share_network_id=new_duplicated_sn["id"],
            snapshot_id=snap["id"],
        )


class SharesAPIOnlyNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SharesAPIOnlyNegativeTest, cls).resource_setup()
        # create share_type
        cls.share_type = cls.create_share_type()
        cls.share_type_min_2_max_5 = cls.create_share_type(
            extra_specs={
                'provisioning:max_share_size': int(CONF.share.share_size) + 4,
                'provisioning:min_share_size': int(CONF.share.share_size) + 1
            })
        cls.share_type_id = cls.share_type['id']
        cls.share_type_min_2_max_5_id = cls.share_type_min_2_max_5['id']

    @decorators.idempotent_id('75837f93-8c2c-40a4-bb9e-d76c53db07c7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_unmanage_share_by_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.unmanage_share,
                          'fake-id')

    @decorators.idempotent_id('97a4dd2f-7c90-4eb7-bf74-d698c3060833')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_manage_share_by_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.manage_share,
                          'fake-host', 'nfs', '/export/path',
                          'fake-type')

    @decorators.idempotent_id('1a438374-8a91-4566-9cef-0386f6609445')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_by_user_with_host_filter(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.list_shares,
                          params={'host': 'fake_host'})

    @decorators.idempotent_id('73f37f33-946d-4213-9d27-25cd4e9a0208')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_by_share_server_by_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.list_shares,
                          params={'share_server_id': 12345})

    @decorators.idempotent_id('2f0df934-b2fb-4ebd-96f7-183cb699dcdd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_non_existent_az(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.create_share,
                          share_type_id=self.share_type_id,
                          availability_zone='fake_az')

    @decorators.idempotent_id('5ae2ecd7-a694-4ba9-ae23-cca75580b9d8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_zero_size(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_share,
                          share_type_id=self.share_type_id,
                          size=0)

    @decorators.idempotent_id('3620a380-f9f9-4521-a468-473581637344')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_invalid_size(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_share,
                          share_type_id=self.share_type_id,
                          size="#$%")

    @decorators.idempotent_id('26ed523d-a215-4661-a038-633b74c9cad7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_out_passing_size(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_share,
                          share_type_id=self.share_type_id,
                          size="")

    @decorators.idempotent_id('bf303b29-bbcb-4a96-96e9-270e12df58d1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_delete_snapshot_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_snapshot,
                          "wrong_share_id")

    @decorators.idempotent_id('08e5a9c7-45cb-414c-b375-28c335f20ff1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_create_snapshot_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.create_snapshot,
                          "wrong_share_id")

    @decorators.idempotent_id('78e5e327-c68e-4910-82b2-27f5f4d150ac')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_invalid_protocol(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_share,
                          share_type_id=self.share_type_id,
                          share_protocol="nonexistent_protocol")

    @decorators.idempotent_id('2b7c7ea8-c0e9-446c-a8e3-add765452c04')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_wrong_public_value(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_share,
                          share_type_id=self.share_type_id,
                          is_public='truebar')

    @decorators.idempotent_id('f82d1667-ae39-43bb-b5aa-bfc9b2ec7292')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_share_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound, self.shares_client.get_share,
                          "wrong_share_id")

    @decorators.idempotent_id('d03cf44e-6e69-415f-be36-25defb86df56')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_share_without_passing_share_id(self):
        # Should not be able to get share when empty ID is passed
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_share, '')

    @decorators.idempotent_id('a9487254-606b-444f-ba6a-2f461bcaf474')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_shares_nonadmin_with_nonexistent_share_server_filter(self):
        # filtering by share server allowed only for admins by default
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.list_shares_with_detail,
                          {'share_server_id': 'fake_share_server_id'})

    @decorators.idempotent_id('9698d1a3-8ee8-46fa-a46b-1084d98e7149')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound, self.shares_client.delete_share,
                          "wrong_share_id")

    @decorators.idempotent_id('b8097d56-067e-4d7c-8401-31bc7021fd24')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_without_passing_share_id(self):
        # Should not be able to delete share when empty ID is passed
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_share, '')

    @utils.skip_if_microversion_not_supported("2.61")
    @decorators.idempotent_id('b8097d56-067e-4d7c-8401-31bc7021fe86')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_size_greater_than_specified_in_share_type(self):
        # Should not be able to create share if size too large
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share,
                          size=int(CONF.share.share_size) + 5,
                          share_type_id=self.share_type_min_2_max_5_id)

    @utils.skip_if_microversion_not_supported("2.61")
    @decorators.idempotent_id('b8097d56-067e-4d7c-8401-31bc7021fe87')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_size_less_than_specified_in_share_type(self):
        # Should not be able to create share if size too small
        self.assertRaises(lib_exc.BadRequest,
                          self.create_share,
                          size=int(CONF.share.share_size),
                          share_type_id=self.share_type_min_2_max_5_id)
