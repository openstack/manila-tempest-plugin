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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base

CONF = config.CONF


@ddt.ddt
class SharesQuotasNegativeTest(base.BaseSharesTest):

    @classmethod
    def skip_checks(cls):
        super(SharesQuotasNegativeTest, cls).skip_checks()
        if not CONF.share.run_quota_tests:
            msg = "Quota tests are disabled."
            raise cls.skipException(msg)

    @decorators.idempotent_id('d0dfe81d-8e8c-4847-a55f-95ba8a3d922c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_quotas_with_empty_tenant_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.show_quotas, "")

    @decorators.idempotent_id('e7dbc580-1857-4f88-8886-988dc2f2c7b9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_reset_quotas_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.reset_quotas,
                          self.shares_v2_client.tenant_id)

    @decorators.idempotent_id('f1c8e16f-5406-4389-a29c-547cca8a56e0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_quotas_with_user(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.update_quotas,
                          self.shares_v2_client.tenant_id,
                          shares=9)

    @ddt.data("2.6", "2.7", "2.24")
    @decorators.idempotent_id('0f0033b3-357e-42e6-9c94-cac650e1cd50')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_quotas_detail_with_wrong_version(self, microversion):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.detail_quotas,
                          self.shares_v2_client.tenant_id,
                          version=microversion)
