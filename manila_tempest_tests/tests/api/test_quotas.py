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
import itertools
from manila_tempest_tests import utils
from tempest import config
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base

CONF = config.CONF
PRE_SHARE_REPLICAS_MICROVERSION = "2.52"
SHARE_REPLICAS_MICROVERSION = "2.53"


@ddt.ddt
class SharesQuotasTest(base.BaseSharesTest):

    @classmethod
    def resource_setup(cls):
        if not CONF.share.run_quota_tests:
            msg = "Quota tests are disabled."
            raise cls.skipException(msg)
        super(SharesQuotasTest, cls).resource_setup()
        cls.user_id = cls.shares_v2_client.user_id
        cls.tenant_id = cls.shares_v2_client.tenant_id

    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_default_quotas(self, client_name):
        quotas = getattr(self, client_name).default_quotas(self.tenant_id)
        uses_v2_client = client_name == 'shares_v2_client'
        self.assertGreater(int(quotas["gigabytes"]), -2)
        self.assertGreater(int(quotas["snapshot_gigabytes"]), -2)
        self.assertGreater(int(quotas["shares"]), -2)
        self.assertGreater(int(quotas["snapshots"]), -2)
        self.assertGreater(int(quotas["share_networks"]), -2)
        if utils.share_replica_quotas_are_supported() and uses_v2_client:
            self.assertGreater(int(quotas["share_replicas"]), -2)
            self.assertGreater(int(quotas["replica_gigabytes"]), -2)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_show_quotas(self, client_name):
        quotas = getattr(self, client_name).show_quotas(self.tenant_id)
        uses_v2_client = client_name == 'shares_v2_client'
        self.assertGreater(int(quotas["gigabytes"]), -2)
        self.assertGreater(int(quotas["snapshot_gigabytes"]), -2)
        self.assertGreater(int(quotas["shares"]), -2)
        self.assertGreater(int(quotas["snapshots"]), -2)
        self.assertGreater(int(quotas["share_networks"]), -2)
        if utils.share_replica_quotas_are_supported() and uses_v2_client:
            self.assertGreater(int(quotas["share_replicas"]), -2)
            self.assertGreater(int(quotas["replica_gigabytes"]), -2)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_show_quotas_for_user(self, client_name):
        quotas = getattr(self, client_name).show_quotas(
            self.tenant_id, self.user_id)
        uses_v2_client = client_name == 'shares_v2_client'
        self.assertGreater(int(quotas["gigabytes"]), -2)
        self.assertGreater(int(quotas["snapshot_gigabytes"]), -2)
        self.assertGreater(int(quotas["shares"]), -2)
        self.assertGreater(int(quotas["snapshots"]), -2)
        self.assertGreater(int(quotas["share_networks"]), -2)
        if utils.share_replica_quotas_are_supported() and uses_v2_client:
            self.assertGreater(int(quotas["share_replicas"]), -2)
            self.assertGreater(int(quotas["replica_gigabytes"]), -2)

    @ddt.data(
        *itertools.product(set(
            ["2.25", "2.53", CONF.share.max_api_microversion]), (True, False))
    )
    @ddt.unpack
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_show_quotas_detail(self, microversion, with_user):
        self.skip_if_microversion_not_supported(microversion)
        quota_args = {"tenant_id": self.tenant_id, "version": microversion, }
        keys = ['gigabytes', 'snapshot_gigabytes', 'shares',
                'snapshots', 'share_networks']
        if utils.is_microversion_ge(microversion, SHARE_REPLICAS_MICROVERSION):
            keys.append('share_replicas')
            keys.append('replica_gigabytes')
        if with_user:
            quota_args.update({"user_id": self.user_id})
        quotas = self.shares_v2_client.detail_quotas(**quota_args)
        quota_keys = list(quotas.keys())
        for outer in keys:
            self.assertIn(outer, quota_keys)
            outer_keys = list(quotas[outer].keys())
            for inner in ('in_use', 'limit', 'reserved'):
                self.assertIn(inner, outer_keys)
                self.assertGreater(int(quotas[outer][inner]), -2)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @base.skip_if_microversion_not_supported(PRE_SHARE_REPLICAS_MICROVERSION)
    def test_quota_detail_2_52_no_share_replica_quotas(self):
        quota_args = {"tenant_id": self.tenant_id,
                      "version": PRE_SHARE_REPLICAS_MICROVERSION}
        quotas = self.shares_v2_client.detail_quotas(**quota_args)
        self.assertNotIn('share_replicas', quotas.keys())
        self.assertNotIn('replica_gigabytes', quotas.keys())
