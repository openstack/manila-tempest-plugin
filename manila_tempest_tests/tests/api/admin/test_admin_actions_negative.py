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
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class AdminActionsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(AdminActionsNegativeTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.member_client = cls.shares_v2_client
        # create share type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id,
                                     client=cls.admin_client)
        cls.sh_instance = (
            cls.admin_client.get_instances_of_share(
                cls.share["id"])['share_instances'][0]
        )
        if CONF.share.run_snapshot_tests:
            cls.snapshot = cls.create_snapshot_wait_for_active(
                cls.share["id"], client=cls.admin_client)

    @decorators.idempotent_id('f730c395-a501-44cf-90d9-a3273771b895')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_share_state_to_unacceptable_state(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_client.reset_state,
                          self.share["id"], status="fake")

    @decorators.idempotent_id('3bfa9555-9c7e-45a2-b5bd-384329cb6fda')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_share_instance_state_to_unacceptable_state(self):
        self.assertRaises(
            lib_exc.BadRequest,
            self.admin_client.reset_state,
            self.sh_instance["id"],
            s_type="share_instances",
            status="fake"
        )

    @decorators.idempotent_id('02e0d0d5-ac66-4d24-9aa7-568f75944a05')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_reset_snapshot_state_to_unacceptable_state(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_client.reset_state,
                          self.snapshot["id"],
                          s_type="snapshots",
                          status="fake")

    @decorators.idempotent_id('3b525c29-b657-493f-aa41-b17676a95fd2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_reset_share_state_with_member(self):
        # NOTE(gouthamr): The client used below is of a member from another
        # project. As a fix to bug #1901210, the server responds with
        # 404 instead of 403, but we'll test for one of the two codes since
        # the test could be running against a release without the fix.
        self.assertRaises((lib_exc.Forbidden, lib_exc.NotFound),
                          self.member_client.reset_state,
                          self.share["id"])

    @decorators.idempotent_id('d4abddba-1c20-49e1-85b1-5452f0faceb0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_reset_share_instance_state_with_member(self):
        # Even if member from another tenant, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.reset_state,
                          self.sh_instance["id"], s_type="share_instances")

    @decorators.idempotent_id('48dfb1ec-6db6-4022-8a41-2eb2883e0988')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_try_reset_snapshot_state_with_member(self):
        # Even if member from another tenant, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.reset_state,
                          self.snapshot["id"], s_type="snapshots")

    @decorators.idempotent_id('7cd0b48e-2815-4f8c-8718-3c071ff9701f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_force_delete_share_with_member(self):
        # If a non-admin tries to do force_delete, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.force_delete,
                          self.share["id"])

    @decorators.idempotent_id('257da3e0-9460-4d97-8a56-c86c0427cc64')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_force_delete_share_instance_with_member(self):
        # If a non-admin tries to do force_delete, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.force_delete,
                          self.sh_instance["id"], s_type="share_instances")

    @decorators.idempotent_id('c9a1894f-d58f-4885-86ba-736e9ab8428a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_try_force_delete_snapshot_with_member(self):
        # If a non-admin tries to do force_delete, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.force_delete,
                          self.snapshot["id"], s_type="snapshots")

    @decorators.idempotent_id('821da7c8-3501-44ba-9ffe-45f485a6e573')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_get_share_instance_with_member(self):
        # If a non-admin tries to get instance, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.get_share_instance,
                          self.sh_instance["id"])

    @decorators.idempotent_id('ab361521-adc9-4fe3-9699-a5ccc49b579b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_get_instances_of_share_with_member(self):
        # If a non-admin tries to list instances of given share, it should be
        # unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.get_instances_of_share,
                          self.share['id'])

    @decorators.idempotent_id('d662457c-2b84-4f13-aee7-5ffafe2552f1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_reset_task_state_invalid_state(self):
        self.assertRaises(
            lib_exc.BadRequest, self.admin_client.reset_task_state,
            self.share['id'], 'fake_state')


@ddt.ddt
class AdminActionsAPIOnlyNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(AdminActionsAPIOnlyNegativeTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.member_client = cls.shares_v2_client

    @decorators.idempotent_id('1c928920-1538-400a-ab28-c58dd75503c3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_share_instance_with_member(self):
        # If a non-admin tries to list instances, it should be unauthorized
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.list_share_instances)

    @decorators.idempotent_id('aba8638c-bfed-4c3e-994b-5309fcd912b2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_reset_task_state_share_not_found(self):
        self.assertRaises(
            lib_exc.NotFound, self.admin_client.reset_task_state,
            'fake_share', 'migration_error')

    @decorators.idempotent_id('e31d2d7b-7202-4699-9423-72f710e72181')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_force_delete_nonexistent_snapshot(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.force_delete,
                          "fake",
                          s_type="snapshots")

    @decorators.idempotent_id('dedca5c1-151d-40f7-bb7f-8913d51c05a9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_force_delete_nonexistent_share(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.force_delete, "fake")

    @decorators.idempotent_id('7cbfc035-12ea-4e2c-8da1-baf261e45f03')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_force_delete_nonexistent_share_instance(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.force_delete,
                          "fake",
                          s_type="share_instances")

    @decorators.idempotent_id('17e7eb3c-dbe6-4667-b838-663211365d44')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_reset_nonexistent_share_state(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.reset_state, "fake")

    @decorators.idempotent_id('26ce6f02-98eb-435a-9065-2e5bbcac87c5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_reset_nonexistent_share_instance_state(self):
        self.assertRaises(lib_exc.NotFound, self.admin_client.reset_state,
                          "fake", s_type="share_instances")

    @decorators.idempotent_id('7e07f684-b68f-4b0e-89cc-05d70a67dd69')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_reset_nonexistent_snapshot_state(self):
        self.assertRaises(lib_exc.NotFound, self.admin_client.reset_state,
                          "fake", s_type="snapshots")

    @decorators.idempotent_id('59b09ad2-d405-4762-a253-d7b7cf56f0a5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data('migrate_share', 'migration_complete', 'reset_task_state',
              'migration_get_progress', 'migration_cancel')
    def test_migration_API_invalid_microversion(self, method_name):
        if method_name == 'migrate_share':
            self.assertRaises(
                lib_exc.NotFound, getattr(self.shares_v2_client, method_name),
                'fake_share', 'fake_host', version='2.21')
        elif method_name == 'reset_task_state':
            self.assertRaises(
                lib_exc.NotFound, getattr(self.shares_v2_client, method_name),
                'fake_share', 'fake_task_state', version='2.21')
        else:
            self.assertRaises(
                lib_exc.NotFound, getattr(self.shares_v2_client, method_name),
                'fake_share', version='2.21')
