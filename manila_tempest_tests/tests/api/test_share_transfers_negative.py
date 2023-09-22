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

from oslo_utils import uuidutils
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareTransferNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareTransferNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(
            constants.SHARE_TRANSFER_VERSION)
        if CONF.share.multitenancy_enabled:
            raise cls.skipException(
                'Only for driver_handles_share_servers = False driver mode.')

    @classmethod
    def resource_setup(cls):
        super(ShareTransferNegativeTest, cls).resource_setup()
        # create share_type with dhss=False
        extra_specs = cls.add_extra_specs_to_dict()
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

    def _create_share_transfer(self, share):
        transfer = self.shares_v2_client.create_share_transfer(
            share['id'])['transfer']
        waiters.wait_for_resource_status(
            self.shares_client, share['id'], 'awaiting_transfer')
        self.addCleanup(waiters.wait_for_resource_status, self.shares_client,
                        share['id'], 'available')
        self.addCleanup(self.shares_v2_client.delete_share_transfer,
                        transfer['id'])
        return transfer

    @decorators.idempotent_id('baf66f62-253e-40dd-a6a9-109bc7613e52')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_show_transfer_of_other_tenants(self):
        # create share
        share_name = data_utils.rand_name("tempest-share-name")
        share = self.create_share(
            name=share_name,
            share_type_id=self.share_type_id)

        # create share transfer
        transfer = self._create_share_transfer(share)

        self.assertRaises(lib_exc.NotFound,
                          self.alt_shares_v2_client.get_share_transfer,
                          transfer['id'])

    @decorators.idempotent_id('4b9e75b1-4ac6-4111-b09e-e6dacd0ac2c3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_nonexistent_transfer(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_share_transfer,
                          str(uuidutils.generate_uuid()))

    @decorators.idempotent_id('b3e26356-5eb0-4f73-b5a7-d3594cc2f30e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_transfer_of_other_tenants(self):
        # create share
        share_name = data_utils.rand_name("tempest-share-name")
        share = self.create_share(
            name=share_name,
            share_type_id=self.share_type_id)

        # create share transfer
        transfer = self._create_share_transfer(share)

        self.assertRaises(lib_exc.NotFound,
                          self.alt_shares_v2_client.delete_share_transfer,
                          transfer['id'])

    @decorators.idempotent_id('085d5971-fe6e-4497-93cb-f1eb176a10da')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_nonexistent_transfer(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_share_transfer,
                          str(uuidutils.generate_uuid()))

    @decorators.idempotent_id('cc7af032-0504-417e-8ab9-73b37bed7f85')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_accept_transfer_without_auth_key(self):
        # create share
        share_name = data_utils.rand_name("tempest-share-name")
        share = self.create_share(
            name=share_name,
            share_type_id=self.share_type_id)

        # create share transfer
        transfer = self._create_share_transfer(share)

        self.assertRaises(lib_exc.BadRequest,
                          self.alt_shares_v2_client.accept_share_transfer,
                          transfer['id'], "")

    @decorators.idempotent_id('05a6a345-7609-421f-be21-d79041970674')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_accept_transfer_with_incorrect_auth_key(self):
        # create share
        share_name = data_utils.rand_name("tempest-share-name")
        share = self.create_share(
            name=share_name,
            share_type_id=self.share_type_id)

        # create share transfer
        transfer = self._create_share_transfer(share)

        self.assertRaises(lib_exc.BadRequest,
                          self.alt_shares_v2_client.accept_share_transfer,
                          transfer['id'], "incorrect_auth_key")
