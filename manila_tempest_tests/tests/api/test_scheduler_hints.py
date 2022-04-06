# Copyright 2021 Cloudification GmbH
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
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class SharesSchedulerHintsTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(SharesSchedulerHintsTest, cls).skip_checks()
        if not CONF.share.multi_backend:
            raise cls.skipException("Manila multi-backend is disabled.")
        elif len(CONF.share.backend_names) < 2:
            raise cls.skipException("For running multi-backend tests required"
                                    " two names in config. Skipping.")
        elif any(not name for name in CONF.share.backend_names):
            raise cls.skipException("Share backend names can not be empty. "
                                    "Skipping.")
        utils.check_skip_if_microversion_not_supported('2.65')

    @classmethod
    def resource_setup(cls):
        super(SharesSchedulerHintsTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share_a = cls.create_share(share_type_id=cls.share_type_id)

    @decorators.idempotent_id('f96d5836-bfc9-4c22-888e-3f62d731573c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_same_host_scheduler_hint_in_share_creation(self):
        scheduler_hint = {"same_host": "%s" % self.share_a["id"]}

        # create share with metadata
        share_b = self.create_share(share_type_id=self.share_type_id,
                                    scheduler_hints=scheduler_hint,
                                    cleanup_in_class=False)

        # get backend of shares
        share_a = self.admin_shares_v2_client.get_share(
            self.share_a['id'])['share']
        backend_a = share_a['host']
        share_b = self.admin_shares_v2_client.get_share(
            share_b['id'])['share']
        backend_b = share_b['host']

        # verify same backends
        self.assertEqual(backend_a, backend_b)

        # get metadata of share
        metadata_a = self.shares_v2_client.get_metadata(
            self.share_a["id"])['metadata']
        md_a = {"__affinity_same_host": "%s" % share_b["id"]}
        metadata_b = self.shares_v2_client.get_metadata(
            share_b["id"])['metadata']
        md_b = {"__affinity_same_host": "%s" % self.share_a["id"]}

        # verify metadata
        self.assertEqual(md_a, metadata_a)
        self.assertEqual(md_b, metadata_b)

    @decorators.idempotent_id('6569e0c3-43c9-4ee2-84ff-ea7fa8da8110')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_different_host_scheduler_hint_in_share_creation(self):
        scheduler_hint = {"different_host": "%s" % self.share_a["id"]}

        # create share with metadata
        share_c = self.create_share(share_type_id=self.share_type_id,
                                    scheduler_hints=scheduler_hint,
                                    cleanup_in_class=False)

        # get backend of shares
        share_a = self.admin_shares_v2_client.get_share(
            self.share_a['id'])['share']
        backend_a = share_a['host']
        share_c = self.admin_shares_v2_client.get_share(share_c['id'])['share']
        backend_c = share_c['host']

        # verify different backends
        self.assertNotEqual(backend_a, backend_c)
