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

from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


class ShareLimitsTest(base.BaseSharesTest):

    @decorators.idempotent_id('239903d2-f1cb-4bec-b456-d57456308244')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_limits_keys(self):

        # list limits
        limits = self.shares_client.get_limits()['limits']

        # verify response
        keys = ["rate", "absolute"]
        [self.assertIn(key, limits.keys()) for key in keys]

        abs_keys = [
            "maxTotalShareGigabytes",
            "maxTotalShares",
            "maxTotalShareSnapshots",
            "maxTotalShareNetworks",
            "maxTotalSnapshotGigabytes",
            "totalSharesUsed",
            "totalShareSnapshotsUsed",
            "totalShareNetworksUsed",
            "totalShareGigabytesUsed",
            "totalSnapshotGigabytesUsed",
        ]
        [self.assertIn(key, limits["absolute"].keys()) for key in abs_keys]

    @decorators.idempotent_id('fea1a10e-6bcb-46eb-bbba-f6f0a8d4f377')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_limits_values(self):

        # list limits
        limits = self.shares_client.get_limits()['limits']

        # verify integer values for absolute limits
        abs_l = limits["absolute"]
        self.assertGreater(int(abs_l["maxTotalShareGigabytes"]), -2)
        self.assertGreater(int(abs_l["maxTotalShares"]), -2)
        self.assertGreater(int(abs_l["maxTotalShareSnapshots"]), -2)
        self.assertGreater(int(abs_l["maxTotalShareNetworks"]), -2)
        self.assertGreater(int(abs_l["maxTotalSnapshotGigabytes"]), -2)
        self.assertGreater(int(abs_l["totalSharesUsed"]), -2)
        self.assertGreater(int(abs_l["totalShareSnapshotsUsed"]), -2)
        self.assertGreater(int(abs_l["totalShareNetworksUsed"]), -2)
        self.assertGreater(int(abs_l["totalShareGigabytesUsed"]), -2)
        self.assertGreater(int(abs_l["totalSnapshotGigabytesUsed"]), -2)
