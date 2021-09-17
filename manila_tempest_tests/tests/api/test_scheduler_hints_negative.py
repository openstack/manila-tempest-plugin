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
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

FAKE_SHARE_ID = "2d316e9f-39fc-468e-b2d9-634b25ae85f6"
CONF = config.CONF


class SharesSchedulerHintsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(SharesSchedulerHintsNegativeTest, cls).skip_checks()
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
        super(SharesSchedulerHintsNegativeTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share_a = cls.create_share(share_type_id=cls.share_type_id)

    @decorators.idempotent_id('2228a187-4f03-4195-9e23-fa1a42110fdc')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_scheduler_hint_with_invalid_share_id(self):
        scheduler_hint = {"same_host": FAKE_SHARE_ID}
        self.assertRaises(lib_exc.NotFound,
                          self.create_share,
                          share_type_id=self.share_type_id,
                          scheduler_hints=scheduler_hint,
                          cleanup_in_class=False)

    @decorators.idempotent_id('6f0c5561-8a6a-4cfb-bbe7-84ffc39bf78d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_scheduler_hint_with_invalid_hint(self):
        scheduler_hint = {"same_host": "%s" % self.share_a["id"],
                          "different_host": "%s" % self.share_a["id"]}
        self.assertRaises(share_exceptions.ShareBuildErrorException,
                          self.create_share,
                          share_type_id=self.share_type_id,
                          scheduler_hints=scheduler_hint,
                          cleanup_in_class=False)
