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
import testtools

from manila_tempest_tests.tests.api import base
from tempest import config
from testtools import testcase as tc

CONF = config.CONF


@ddt.ddt
class AdminActionsTest(base.BaseSharesAdminTest):

    @classmethod
    def resource_setup(cls):
        super(AdminActionsTest, cls).resource_setup()
        cls.task_states = ["migration_starting", "data_copying_in_progress",
                           "migration_success", None]
        cls.bad_status = "error_deleting"
        # create share type
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.sh = cls.create_share(share_type_id=cls.share_type_id)

    def _wait_for_resource_status(self, resource_id, resource_type):
        wait_for_resource_status = getattr(
            self.shares_v2_client, "wait_for_{}_status".format(resource_type))
        wait_for_resource_status(resource_id, "available")

    def _reset_resource_available(self, resource_id, resource_type="shares"):
        self.shares_v2_client.reset_state(
            resource_id, s_type=resource_type, status="available")
        self._wait_for_resource_status(resource_id, resource_type[:-1])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data("error", "available", "error_deleting", "deleting", "creating")
    def test_reset_share_state(self, status):
        self.shares_v2_client.reset_state(self.sh["id"], status=status)
        self.shares_v2_client.wait_for_share_status(self.sh["id"], status)
        self.addCleanup(self._reset_resource_available, self.sh["id"])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data("error", "available", "error_deleting", "deleting", "creating")
    def test_reset_share_instance_state(self, status):
        sh_instance = self.shares_v2_client.get_instances_of_share(
            self.sh["id"])[0]
        share_instance_id = sh_instance["id"]
        self.shares_v2_client.reset_state(
            share_instance_id, s_type="share_instances", status=status)
        self.shares_v2_client.wait_for_share_instance_status(
            share_instance_id, status)
        self.addCleanup(self._reset_resource_available,
                        share_instance_id, "share_instances")

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @ddt.data("error", "available", "error_deleting", "deleting", "creating")
    def test_reset_snapshot_state(self, status):
        snapshot = self.create_snapshot_wait_for_active(self.sh["id"])
        self.shares_v2_client.reset_state(
            snapshot["id"], s_type="snapshots", status=status)
        self.shares_v2_client.wait_for_snapshot_status(
            snapshot["id"], status)
        self.addCleanup(self._reset_resource_available,
                        snapshot["id"], "snapshots")

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_share(self):
        share = self.create_share(share_type_id=self.share_type_id)

        # Change status from 'available' to 'error_deleting'
        self.shares_v2_client.reset_state(share["id"], status=self.bad_status)

        # Check that status was changed
        check_status = self.shares_v2_client.get_share(share["id"])
        self.assertEqual(self.bad_status, check_status["status"])

        # Share with status 'error_deleting' should be deleted
        self.shares_v2_client.force_delete(share["id"])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share["id"])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_share_instance(self):
        share = self.create_share(share_type_id=self.share_type_id,
                                  cleanup_in_class=False)
        instances = self.shares_v2_client.get_instances_of_share(share["id"])
        # Check that instance was created
        self.assertEqual(1, len(instances))

        instance = instances[0]

        # Change status from 'available' to 'error_deleting'
        self.shares_v2_client.reset_state(
            instance["id"], s_type="share_instances", status=self.bad_status)

        # Check that status was changed
        check_status = self.shares_v2_client.get_share_instance(instance["id"])
        self.assertEqual(self.bad_status, check_status["status"])

        # Share with status 'error_deleting' should be deleted
        self.shares_v2_client.force_delete(
            instance["id"], s_type="share_instances")
        self.shares_v2_client.wait_for_resource_deletion(
            share_instance_id=instance["id"])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_force_delete_snapshot(self):
        sn = self.create_snapshot_wait_for_active(self.sh["id"])

        # Change status from 'available' to 'error_deleting'
        self.shares_v2_client.reset_state(
            sn["id"], s_type="snapshots", status=self.bad_status)

        # Check that status was changed
        check_status = self.shares_v2_client.get_snapshot(sn["id"])
        self.assertEqual(self.bad_status, check_status["status"])

        # Snapshot with status 'error_deleting' should be deleted
        self.shares_v2_client.force_delete(sn["id"], s_type="snapshots")
        self.shares_v2_client.wait_for_resource_deletion(snapshot_id=sn["id"])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @base.skip_if_microversion_lt("2.22")
    def test_reset_share_task_state(self):
        for task_state in self.task_states:
            self.shares_v2_client.reset_task_state(self.sh["id"], task_state)
            self.shares_v2_client.wait_for_share_status(
                self.sh["id"], task_state, 'task_state')
