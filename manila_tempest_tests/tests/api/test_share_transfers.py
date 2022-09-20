# Copyright (C) 2022 China Telecom Digital Intelligence.
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
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareTransferTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareTransferTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(
            constants.SHARE_TRANSFER_VERSION)
        if CONF.share.multitenancy_enabled:
            raise cls.skipException(
                'Only for driver_handles_share_servers = False driver mode.')

    @classmethod
    def resource_setup(cls):
        super(ShareTransferTest, cls).resource_setup()
        # create share_type with dhss=False
        extra_specs = cls.add_extra_specs_to_dict()
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

    @decorators.idempotent_id('716e71a0-8265-4410-9170-08714095d9e8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_and_delete_share_transfer(self):
        # create share
        share_name = data_utils.rand_name("tempest-share-name")
        share = self.create_share(name=share_name,
                                  share_type_id=self.share_type_id,
                                  cleanup_in_class=False)

        # create share transfer
        transfer = self.shares_v2_client.create_share_transfer(
            share['id'], name='tempest_share_transfer')['transfer']
        waiters.wait_for_resource_status(
            self.shares_client, share['id'], 'awaiting_transfer')

        # check transfer exists and show transfer
        transfer_show = self.shares_v2_client.get_share_transfer(
            transfer['id'])['transfer']
        self.assertEqual(transfer_show['name'], 'tempest_share_transfer')

        # delete share transfer
        self.shares_v2_client.delete_share_transfer(transfer['id'])
        waiters.wait_for_resource_status(
            self.shares_client, share['id'], 'available')

        # check transfer not in transfer list
        transfers = self.shares_v2_client.list_share_transfers()['transfers']
        transfer_ids = [tf['id'] for tf in transfers]
        self.assertNotIn(transfer['id'], transfer_ids)

    @decorators.idempotent_id('3c2622ab-3368-4693-afb6-e60bd27e61ef')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_and_accept_share_transfer(self):
        # create share
        share_name = data_utils.rand_name("tempest-share-name")
        share = self.create_share(name=share_name,
                                  share_type_id=self.share_type_id)

        # create share transfer
        transfer = self.shares_v2_client.create_share_transfer(
            share['id'])['transfer']
        waiters.wait_for_resource_status(
            self.shares_client, share['id'], 'awaiting_transfer')

        # accept share transfer by alt project
        self.alt_shares_v2_client.accept_share_transfer(transfer['id'],
                                                        transfer['auth_key'])
        waiters.wait_for_resource_status(
            self.alt_shares_client, share['id'], 'available')

        # check share in alt project
        shares = self.alt_shares_v2_client.list_shares(
            detailed=True)['shares']
        share_ids = [sh['id'] for sh in shares] if shares else []
        self.assertIn(share['id'], share_ids)

        # delete the share
        self.alt_shares_v2_client.delete_share(share['id'])
        self.alt_shares_v2_client.wait_for_resource_deletion(
            share_id=share["id"])
