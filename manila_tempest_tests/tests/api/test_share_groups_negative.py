# Copyright 2016 Andrew Kerr
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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF


class ShareGroupsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareGroupsNegativeTest, cls).skip_checks()
        if not CONF.share.run_share_group_tests:
            raise cls.skipException('Share Group tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            constants.MIN_SHARE_GROUP_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ShareGroupsNegativeTest, cls).resource_setup()
        # Create a share type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

        # Create a share group type
        cls.share_group_type = cls._create_share_group_type()
        cls.share_group_type_id = cls.share_group_type['id']

        # Create a share group
        cls.share_group_name = data_utils.rand_name("tempest-sg-name")
        cls.share_group_desc = data_utils.rand_name("tempest-sg-description")
        cls.share_group = cls.create_share_group(
            name=cls.share_group_name,
            description=cls.share_group_desc,
            share_group_type_id=cls.share_group_type_id,
            share_type_ids=[cls.share_type_id],
        )
        # Create a share in the share group
        cls.share_name = data_utils.rand_name("tempest-share-name")
        cls.share_desc = data_utils.rand_name("tempest-share-description")
        cls.share_size = CONF.share.share_size
        cls.share = cls.create_share(
            name=cls.share_name,
            description=cls.share_desc,
            size=cls.share_size,
            share_type_id=cls.share_type_id,
            share_group_id=cls.share_group['id'],
        )
        if CONF.share.run_snapshot_tests:
            # Create a share group snapshot of the share group
            cls.sg_snap_name = data_utils.rand_name("tempest-sg-snap-name")
            cls.sg_snap_desc = data_utils.rand_name(
                "tempest-group-snap-description")
            cls.sg_snapshot = cls.create_share_group_snapshot_wait_for_active(
                cls.share_group['id'],
                name=cls.sg_snap_name,
                description=cls.sg_snap_desc
            )

    @decorators.idempotent_id('7ce3fb52-1bec-42b1-9b4f-671c8465764b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_with_invalid_source_sg_snapshot_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group,
            source_share_group_snapshot_id='foobar',
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('43c7a454-06b4-4c6e-8aaf-34709db64e28')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_with_nonexistent_source_sg_snapshot_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group,
            source_share_group_snapshot_id=self.share['id'],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('aae1b1db-ea04-4a53-88ad-e5ee648fe938')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_with_invalid_share_network_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group,
            share_network_id='foobar',
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('ea817e28-08b9-40c1-bbab-a8820ec564ac')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_group_with_nonexistent_share_network_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group,
            share_network_id=self.share['id'],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('8bc89858-61de-49f3-868c-394841a93503')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_with_invalid_share_type_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group,
            share_type_ids=['foobar'],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('97183b15-d150-4c6b-b812-734c2500afe7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_with_nonexistent_share_type_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group,
            share_type_ids=[self.share['id']],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('25a829e2-be7d-4a4d-881e-bc0634515985')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_snapshot_with_invalid_sg_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group_snapshot_wait_for_active,
            'foobar',
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('16ad5a77-0ef7-4906-8e14-56703c2c9d71')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_snapshot_with_nonexistent_sg_id_value_min(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share_group_snapshot_wait_for_active,
            self.share['id'],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('d486a184-1160-4664-ad9b-6f8974685343')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_sg_with_invalid_id_min(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.get_share_group,
            "invalid_share_group_id",
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('7a5dcec1-27cc-4bfe-a166-d8c1832a4dc7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_sg_without_passing_group_id_min(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.get_share_group,
            '', version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('9127933a-1960-415e-bf21-8bcb5720e371')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_sg_with_invalid_id_min(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.update_share_group,
            'invalid_share_group_id',
            name='new_name',
            description='new_description',
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('bf8f9865-a906-4d55-b233-fec57cf43b66')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_sg_with_invalid_id_min(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.delete_share_group,
            "invalid_share_group_id",
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('16431501-800f-4695-bae6-6a4c715c2fbf')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_sg_without_passing_sg_id_min(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.delete_share_group,
            '', version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('18fe2dee-4a07-484e-8f0f-bbc238500dc3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_delete_sg_in_use_by_sg_snapshot_min(self):
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.delete_share_group,
            self.share_group['id'],
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('d2a58f10-cc86-498d-a5e0-1468d4345852')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_delete_share_in_use_by_sg_snapshot_min(self):
        params = {'share_group_id': self.share['share_group_id']}
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.delete_share,
            self.share['id'],
            params=params,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('c2225b19-d5f5-4d15-bb9a-de63bfce6760')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_sg_containing_a_share_min(self):
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.delete_share_group,
            self.share_group['id'],
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        # Verify share group is not put into error state from conflict
        sg = self.shares_v2_client.get_share_group(
            self.share_group['id'],
            version=constants.MIN_SHARE_GROUP_MICROVERSION)['share_group']
        self.assertEqual('available', sg['status'])

    @decorators.idempotent_id('edd329b8-7188-481f-9445-8f6d913538fa')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_filter_shares_on_invalid_group_id_min(self):
        shares = self.shares_v2_client.list_shares(
            detailed=True,
            params={'share_group_id': 'foobar'},
            version=constants.MIN_SHARE_GROUP_MICROVERSION,
        )['shares']
        self.assertEqual(0, len(shares), 'Incorrect number of shares returned')

    @decorators.idempotent_id('5dc10968-cbff-46d9-a1aa-bafccc7a1905')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_filter_shares_on_nonexistent_group_id_min(self):
        shares = self.shares_v2_client.list_shares(
            detailed=True,
            params={'share_group_id': self.share['id']},
            version=constants.MIN_SHARE_GROUP_MICROVERSION,
        )['shares']
        self.assertEqual(0, len(shares), 'Incorrect number of shares returned')

    @decorators.idempotent_id('f805f683-fe05-4534-9f40-a74be42ff82b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_filter_shares_on_empty_share_group_id_min(self):
        share_group = self.create_share_group(
            name='tempest_sg',
            description='tempest_sg_desc',
            share_group_type_id=self.share_group_type_id,
            share_type_ids=[self.share_type_id],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION,
        )
        shares = self.shares_v2_client.list_shares(
            detailed=True,
            params={'share_group_id': share_group['id']},
            version=constants.MIN_SHARE_GROUP_MICROVERSION,
        )['shares']
        self.assertEqual(0, len(shares), 'Incorrect number of shares returned')

    @decorators.idempotent_id('8fc20c22-082f-4851-bcc3-d2f3af57f027')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_with_nonexistent_az_min(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.create_share_group,
            name='tempest_sg',
            description='tempest_sg_desc',
            availability_zone='fake_nonexistent_az',
            share_group_type_id=self.share_group_type_id,
            share_type_ids=[self.share_type_id],
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @utils.skip_if_microversion_not_supported("2.34")
    @decorators.idempotent_id('64527564-9cd6-42db-8897-910f4fc1a151')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_sg_and_share_with_different_azs(self):
        azs = self.shares_v2_client.list_availability_zones(
            )['availability_zones']

        if len(azs) < 2:
            raise self.skipException(
                'Test requires presence of at least 2 availability zones.')
        else:
            share_group = self.shares_v2_client.get_share_group(
                self.share_group['id'], '2.34')['share_group']
            different_az = [
                az['name']
                for az in azs
                if az['name'] != share_group['availability_zone']
            ][0]

        self.assertRaises(
            lib_exc.BadRequest,
            self.create_share,
            share_type_id=self.share_type_id,
            share_group_id=self.share_group['id'],
            availability_zone=different_az,
            version='2.34')
