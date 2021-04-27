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

import ddt
from oslo_utils import uuidutils
import six
from tempest import config
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class SnapshotExportLocationsTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(SnapshotExportLocationsTest, cls).skip_checks()
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')
        if not CONF.share.run_mount_snapshot_tests:
            raise cls.skipException('Mountable snapshots tests are disabled.')

        utils.check_skip_if_microversion_not_supported("2.32")

    @classmethod
    def setup_clients(cls):
        super(SnapshotExportLocationsTest, cls).setup_clients()
        cls.admin_client = cls.admin_shares_v2_client

    @classmethod
    def resource_setup(cls):
        super(SnapshotExportLocationsTest, cls).resource_setup()
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

    def _verify_export_location_structure(
            self, export_locations, role='admin', detail=False):

        # Determine which keys to expect based on role, version and format
        summary_keys = ['id', 'path', 'links']
        if detail:
            summary_keys.extend(['created_at', 'updated_at'])

        admin_summary_keys = summary_keys + [
            'share_snapshot_instance_id', 'is_admin_only']

        if role == 'admin':
            expected_keys = admin_summary_keys
        else:
            expected_keys = summary_keys

        if not isinstance(export_locations, (list, tuple, set)):
            export_locations = (export_locations, )

        for export_location in export_locations:

            # Check that the correct keys are present
            self.assertEqual(len(expected_keys), len(export_location))
            for key in expected_keys:
                self.assertIn(key, export_location)

            # Check the format of ever-present summary keys
            self.assertTrue(uuidutils.is_uuid_like(export_location['id']))
            self.assertIsInstance(export_location['path'],
                                  six.string_types)

            if role == 'admin':
                self.assertIn(export_location['is_admin_only'], (True, False))
                self.assertTrue(uuidutils.is_uuid_like(
                    export_location['share_snapshot_instance_id']))

    @decorators.idempotent_id('18287f50-0e12-463d-906f-5c7cba256288')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshot_export_location(self):
        export_locations = (
            self.admin_client.list_snapshot_export_locations(
                self.snapshot['id']))['share_snapshot_export_locations']

        for el in export_locations:
            self._verify_export_location_structure(el)

    @decorators.idempotent_id('6272b60b-31a1-41c1-86f5-af28926898e6')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot_export_location(self):
        export_locations = (
            self.admin_client.list_snapshot_export_locations(
                self.snapshot['id']))['share_snapshot_export_locations']

        for export_location in export_locations:
            el = self.admin_client.get_snapshot_export_location(
                self.snapshot['id'],
                export_location['id'])['share_snapshot_export_location']
            self._verify_export_location_structure(el, detail=True)

    @decorators.idempotent_id('03be6418-5ba3-4919-a798-89d7e5ffb925')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot_instance_export_location(self):
        for snapshot_instance in self.snapshot_instances:
            export_locations = (
                self.admin_client.list_snapshot_instance_export_locations(
                    snapshot_instance['id'])['share_snapshot_export_locations']
            )
            for el in export_locations:
                el = (
                    self.admin_client.get_snapshot_instance_export_location(
                        snapshot_instance['id'],
                        el['id'])['share_snapshot_export_location']
                )
                self._verify_export_location_structure(el, detail=True)

    @decorators.idempotent_id('cdf444ea-95a3-4f7b-ae48-6b027a6b9529')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_snapshot_contains_all_export_locations_of_all_snapshot_instances(
            self):
        snapshot_export_locations = (
            self.admin_client.list_snapshot_export_locations(
                self.snapshot['id']))['share_snapshot_export_locations']
        snapshot_instances_export_locations = []
        for snapshot_instance in self.snapshot_instances:
            snapshot_instance_export_locations = (
                self.admin_client.list_snapshot_instance_export_locations(
                    snapshot_instance['id'])['share_snapshot_export_locations']
            )
            snapshot_instances_export_locations.extend(
                snapshot_instance_export_locations)

        self.assertEqual(
            len(snapshot_export_locations),
            len(snapshot_instances_export_locations)
        )
        self.assertEqual(
            sorted(snapshot_export_locations, key=lambda el: el['id']),
            sorted(snapshot_instances_export_locations,
                   key=lambda el: el['id'])
        )
