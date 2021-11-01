# Copyright 2022 Cloudification GmbH
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
LATEST_MICROVERSION = CONF.share.max_api_microversion


class SharesSchedulerHintsAdminTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(SharesSchedulerHintsAdminTest, cls).skip_checks()
        if not CONF.share.multi_backend:
            raise cls.skipException("Manila multi-backend tests are disabled.")
        elif len(CONF.share.backend_names) < 2:
            raise cls.skipException("For running multi-backend tests, two or "
                                    "more backend names must be configured.")
        elif any(not name for name in CONF.share.backend_names):
            raise cls.skipException("Share backend names can not be empty.")
        utils.check_skip_if_microversion_not_supported('2.67')

    @classmethod
    def resource_setup(cls):
        super(SharesSchedulerHintsAdminTest, cls).resource_setup()
        # Need for requesting pools
        cls.admin_client = cls.admin_shares_v2_client
        # create share type
        share_type = cls.create_share_type()
        cls.share_type_id = share_type['id']

    @decorators.idempotent_id('54f4dea7-890e-443b-aea5-f6108da893f0')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_only_host_scheduler_hint_in_share_creation(self):
        share_a = self.create_share(share_type_id=self.share_type_id)
        share_a = self.admin_shares_v2_client.get_share(share_a['id'])['share']
        backend_a = share_a['host']
        scheduler_hint = {"only_host": "%s" % backend_a}

        # create share with hint
        share_b = self.create_share(share_type_id=self.share_type_id,
                                    scheduler_hints=scheduler_hint,
                                    cleanup_in_class=False)
        share_b = self.admin_shares_v2_client.get_share(share_b['id'])['share']
        backend_b = share_b['host']

        # verify same backends
        self.assertEqual(backend_a, backend_b)

    @decorators.idempotent_id('1dec3306-61f4-41b9-ba4a-572a9e6f5f57')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @tc.skipUnless(CONF.share.run_replication_tests,
                   'Replication tests are disabled.')
    def test_only_host_scheduler_hint_in_share_replica_creation(self):
        replication_type = CONF.share.backend_replication_type
        if replication_type not in constants.REPLICATION_TYPE_CHOICES:
            raise share_exceptions.ShareReplicationTypeException(
                replication_type=replication_type
            )
        extra_specs = self.add_extra_specs_to_dict({
            "replication_type": replication_type
        })
        replicated_share_type = self.create_share_type(
            data_utils.rand_name("replicated-shares"),
            extra_specs=extra_specs)
        share = self.create_share(
            share_type_id=replicated_share_type['id'],
            cleanup_in_class=False)
        share = self.admin_shares_v2_client.get_share(share['id'])['share']
        share_host = share['host']
        rep_domain, pools = self.get_pools_for_replication_domain(share=share)
        if len(pools) < 2:
            msg = ("Can not create valid hint due to insufficient pools.")
            raise self.skipException(msg)

        for p in pools:
            if p['name'] != share_host:
                expected_replica_host = p['name']
                scheduler_hint = {"only_host": "%s" % expected_replica_host}
                break

        # create share replica with hint
        replica = self.create_share_replica(share['id'],
                                            cleanup_in_class=False,
                                            version=LATEST_MICROVERSION,
                                            scheduler_hints=scheduler_hint)
        replica = self.admin_shares_v2_client.get_share_replica(
            replica['id'])['share_replica']
        replica_host = replica['host']

        # verify same backends
        self.assertEqual(expected_replica_host, replica_host)
