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
from tempest.lib import decorators
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

        utils.check_skip_if_microversion_not_supported("2.32")

    @classmethod
    def setup_clients(cls):
        super(SnapshotExportLocationsNegativeTest, cls).setup_clients()
        cls.admin_client = cls.admin_shares_v2_client
        cls.different_project_client = cls.alt_shares_v2_client

    @classmethod
    def resource_setup(cls):
        super(SnapshotExportLocationsNegativeTest, cls).resource_setup()
        # create share type
        extra_specs = {
            'snapshot_support': True,
            'mount_snapshot_support': True,
        }
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id,
                                     client=cls.admin_client)
        cls.snapshot = cls.create_snapshot_wait_for_active(
            cls.share['id'], client=cls.admin_client)
        cls.snapshot = cls.admin_client.get_snapshot(
            cls.snapshot['id'])['snapshot']
        cls.snapshot_instances = cls.admin_client.list_snapshot_instances(
            snapshot_id=cls.snapshot['id'])['snapshot_instances']

    @decorators.idempotent_id('53f0f184-7398-4e7a-ac21-fa432570db7f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_snapshot_export_location(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.get_snapshot_export_location,
            self.snapshot['id'],
            "fake-inexistent-snapshot-export-location-id",
        )

    @decorators.idempotent_id('43229517-bf93-4be7-9f89-a69034d2f03c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshot_export_locations_by_different_project_user(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.different_project_client.list_snapshot_export_locations,
            self.snapshot['id']
        )

    @decorators.idempotent_id('66839514-796a-4ee9-a8ed-7614521d01d5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot_export_location_by_different_project_user(self):
        export_locations = (
            self.admin_client.list_snapshot_export_locations(
                self.snapshot['id'])['share_snapshot_export_locations'])

        for export_location in export_locations:
            if export_location['is_admin_only']:
                continue
            self.assertRaises(
                lib_exc.NotFound,
                self.different_project_client.get_snapshot_export_location,
                self.snapshot['id'],
                export_location['id'])

    @decorators.idempotent_id('52e0b807-7b29-4795-960a-518bcadc1503')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_snapshot_instance_export_location(self):
        for snapshot_instance in self.snapshot_instances:
            self.assertRaises(
                lib_exc.NotFound,
                self.admin_client.get_snapshot_instance_export_location,
                snapshot_instance['id'],
                "fake-inexistent-snapshot-export-location-id",
            )

    @decorators.idempotent_id('3f4e2a0e-1522-47fb-b770-9d7a0651dde2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot_instance_export_location_by_member(self):
        for snapshot_instance in self.snapshot_instances:
            export_locations = (
                self.admin_client.list_snapshot_instance_export_locations(
                    snapshot_instance['id'])['share_snapshot_export_locations']
            )
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

        utils.check_skip_if_microversion_not_supported('2.32')

    @classmethod
    def setup_clients(cls):
        super(SnapshotExportLocationsAPIOnlyNegativeTest, cls).setup_clients()
        cls.admin_client = cls.admin_shares_v2_client
        # admin_member_client is a regular user in admin's project
        cls.admin_member_client = (
            cls.admin_project_member_client.shares_v2_client)

    @decorators.idempotent_id('37901216-b574-4786-9b1d-9b1ccdf123d2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_export_locations_by_nonexistent_snapshot(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.list_snapshot_export_locations,
            "fake-inexistent-snapshot-id",
        )

    @decorators.idempotent_id('c2aa3770-c061-4b49-83ac-ab29773c2e0c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_export_locations_by_nonexistent_snapshot_instance(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.list_snapshot_instance_export_locations,
            "fake-inexistent-snapshot-instance-id",
        )

    @decorators.idempotent_id('74d5d46d-8161-4e17-acbc-812248d6d694')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_inexistent_snapshot_instance_export_locations_by_member(
            self):
        self.assertRaises(
            lib_exc.Forbidden,
            self.admin_member_client.list_snapshot_instance_export_locations,
            "fake-inexistent-snapshot-instance-id"
        )
