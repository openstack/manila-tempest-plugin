# Copyright (c) 2017 Hitachi Data Systems, Inc.
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
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class SnapshotExportLocationsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(SnapshotExportLocationsNegativeTest, cls).skip_checks()
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')
        if not CONF.share.run_mount_snapshot_tests:
            raise cls.skipException('Mountable snapshots tests are disabled.')

        utils.check_skip_if_microversion_lt("2.32")

    @classmethod
    def setup_clients(cls):
        super(SnapshotExportLocationsNegativeTest, cls).setup_clients()
        cls.admin_client = cls.admin_shares_v2_client
        cls.different_project_client = cls.alt_shares_v2_client

    @classmethod
    def resource_setup(cls):
        super(SnapshotExportLocationsNegativeTest, cls).resource_setup()
        # create share type
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id,
                                     client=cls.admin_client)
        cls.snapshot = cls.create_snapshot_wait_for_active(
            cls.share['id'], client=cls.admin_client)
        cls.snapshot = cls.admin_client.get_snapshot(cls.snapshot['id'])
        cls.snapshot_instances = cls.admin_client.list_snapshot_instances(
            snapshot_id=cls.snapshot['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_snapshot_export_location(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.get_snapshot_export_location,
            self.snapshot['id'],
            "fake-inexistent-snapshot-export-location-id",
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshot_export_locations_by_different_project_user(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.different_project_client.list_snapshot_export_locations,
            self.snapshot['id']
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot_export_location_by_different_project_user(self):
        export_locations = (
            self.admin_client.list_snapshot_export_locations(
                self.snapshot['id']))

        for export_location in export_locations:
            if export_location['is_admin_only']:
                continue
            self.assertRaises(
                lib_exc.NotFound,
                self.different_project_client.get_snapshot_export_location,
                self.snapshot['id'],
                export_location['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_snapshot_instance_export_location(self):
        for snapshot_instance in self.snapshot_instances:
            self.assertRaises(
                lib_exc.NotFound,
                self.admin_client.get_snapshot_instance_export_location,
                snapshot_instance['id'],
                "fake-inexistent-snapshot-export-location-id",
            )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot_instance_export_location_by_member(self):
        for snapshot_instance in self.snapshot_instances:
            export_locations = (
                self.admin_client.list_snapshot_instance_export_locations(
                    snapshot_instance['id']))
            for el in export_locations:
                self.assertRaises(
                    lib_exc.Forbidden,
                    (self.different_project_client.
                     get_snapshot_instance_export_location),
                    snapshot_instance['id'], el['id'],
                )


class SnapshotExportLocationsAPIOnlyNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(SnapshotExportLocationsAPIOnlyNegativeTest, cls).skip_checks()
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')
        if not CONF.share.run_mount_snapshot_tests:
            raise cls.skipException('Mountable snapshots tests are disabled.')

        utils.check_skip_if_microversion_lt('2.32')

    @classmethod
    def setup_clients(cls):
        super(SnapshotExportLocationsAPIOnlyNegativeTest, cls).setup_clients()
        cls.admin_client = cls.admin_shares_v2_client
        # admin_member_client is a regular user in admin's project
        cls.admin_member_client = (
            cls.admin_project_member_client.shares_v2_client)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_export_locations_by_nonexistent_snapshot(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.list_snapshot_export_locations,
            "fake-inexistent-snapshot-id",
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_export_locations_by_nonexistent_snapshot_instance(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.list_snapshot_instance_export_locations,
            "fake-inexistent-snapshot-instance-id",
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_inexistent_snapshot_instance_export_locations_by_member(
            self):
        self.assertRaises(
            lib_exc.Forbidden,
            self.admin_member_client.list_snapshot_instance_export_locations,
            "fake-inexistent-snapshot-instance-id"
        )
