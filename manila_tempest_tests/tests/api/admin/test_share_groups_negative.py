# Copyright 2017 Mirantis Inc.
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
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareGroupsNegativeTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(ShareGroupsNegativeTest, cls).skip_checks()
        if not CONF.share.run_share_group_tests:
            raise cls.skipException('Share Group tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('b90537b7-634d-4fca-b451-770fbcca7927')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_share_group_with_wrong_consistent_snapshot_spec(self):
        # Create valid share type for share group type
        share_type = self.create_share_type(cleanup_in_class=False)

        # Create share group type with wrong value for
        # 'consistent_snapshot_support' capability, we always expect
        # NoValidHostFound using this SG type.
        sg_type = self.create_share_group_type(
            name=data_utils.rand_name("tempest-manila"),
            share_types=[share_type['id']],
            group_specs={"consistent_snapshot_support": "fake"},
            cleanup_in_class=False)

        # Try create share group
        self.assertRaises(
            share_exceptions.ShareGroupBuildErrorException,
            self.create_share_group,
            share_type_ids=[share_type['id']],
            share_group_type_id=sg_type['id'],
            cleanup_in_class=False)
