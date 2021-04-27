# Copyright 2015 Mirantis Inc.
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
from oslo_utils import timeutils
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
class ExportLocationsTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ExportLocationsTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported('2.9')

    @classmethod
    def resource_setup(cls):
        super(ExportLocationsTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.member_client = cls.admin_project_member_client.shares_v2_client
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id,
                                     client=cls.admin_client)
        cls.share = cls.admin_client.get_share(cls.share['id'])['share']
        cls.share_instances = cls.admin_client.get_instances_of_share(
            cls.share['id'])['share_instances']

    def _verify_export_location_structure(
            self, export_locations, role='admin', version=LATEST_MICROVERSION,
            format='summary'):

        # Determine which keys to expect based on role, version and format
        summary_keys = ['id', 'path']
        if utils.is_microversion_ge(version, '2.14'):
            summary_keys += ['preferred']

        admin_summary_keys = summary_keys + [
            'share_instance_id', 'is_admin_only']

        detail_keys = summary_keys + ['created_at', 'updated_at']

        admin_detail_keys = admin_summary_keys + ['created_at', 'updated_at']

        if format == 'summary':
            if role == 'admin':
                expected_keys = admin_summary_keys
            else:
                expected_keys = summary_keys
        else:
            if role == 'admin':
                expected_keys = admin_detail_keys
            else:
                expected_keys = detail_keys

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

            if utils.is_microversion_ge(version, '2.14'):
                self.assertIn(export_location['preferred'], (True, False))

            if role == 'admin':
                self.assertIn(export_location['is_admin_only'], (True, False))
                self.assertTrue(uuidutils.is_uuid_like(
                    export_location['share_instance_id']))

            # Check the format of the detail keys
            if format == 'detail':
                for time in (export_location['created_at'],
                             export_location['updated_at']):
                    # If var 'time' has incorrect value then ValueError
                    # exception is expected to be raised. So, just try parse
                    # it making assertion that it has proper date value.
                    timeutils.parse_strtime(time)

    @decorators.idempotent_id('dfcb05af-369a-44c9-a06a-67d12a2a0917')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.13')
    def test_list_share_export_locations(self):
        export_locations = self.admin_client.list_share_export_locations(
            self.share['id'], version='2.13')['export_locations']

        self._verify_export_location_structure(export_locations,
                                               version='2.13')

    @decorators.idempotent_id('032173d7-3ddf-4730-8524-d1a96a2a9e16')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.14')
    def test_list_share_export_locations_with_preferred_flag(self):
        export_locations = self.admin_client.list_share_export_locations(
            self.share['id'], version='2.14')['export_locations']

        self._verify_export_location_structure(export_locations,
                                               version='2.14')

    @decorators.idempotent_id('814da2ce-2909-4b02-a92e-12bc1b640580')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_export_location(self):
        export_locations = self.admin_client.list_share_export_locations(
            self.share['id'])['export_locations']

        for export_location in export_locations:
            el = self.admin_client.get_share_export_location(
                self.share['id'], export_location['id'])['export_location']
            self._verify_export_location_structure(el, format='detail')

    @decorators.idempotent_id('397969c6-7fc8-4bf8-86c7-300b96857c54')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share_export_locations_by_member(self):
        export_locations = self.member_client.list_share_export_locations(
            self.share['id'])['export_locations']

        self._verify_export_location_structure(export_locations, role='member')

    @decorators.idempotent_id('66cef86f-5da8-4cb4-bc21-91f6c1e27cb5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_export_location_by_member(self):
        export_locations = self.admin_client.list_share_export_locations(
            self.share['id'])['export_locations']

        for export_location in export_locations:
            if export_location['is_admin_only']:
                continue
            el = self.member_client.get_share_export_location(
                self.share['id'], export_location['id'])['export_location']
            self._verify_export_location_structure(el, role='member',
                                                   format='detail')

    @decorators.idempotent_id('06ea2636-1c9f-4889-8b5f-e10c2c2572cb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.13')
    def test_list_share_instance_export_locations(self):
        for share_instance in self.share_instances:
            export_locations = (
                self.admin_client.list_share_instance_export_locations(
                    share_instance['id'], version='2.13'))['export_locations']
            self._verify_export_location_structure(export_locations,
                                                   version='2.13')

    @decorators.idempotent_id('b93e4cba-ea98-4b1c-90f8-e0a8763033a3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported('2.14')
    def test_list_share_instance_export_locations_with_preferred_flag(self):
        for share_instance in self.share_instances:
            export_locations = (
                self.admin_client.list_share_instance_export_locations(
                    share_instance['id'], version='2.14'))['export_locations']
            self._verify_export_location_structure(export_locations,
                                                   version='2.14')

    @decorators.idempotent_id('59421c43-293f-41fd-8ac6-e856deeceac9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_instance_export_location(self):
        for share_instance in self.share_instances:
            export_locations = (
                self.admin_client.list_share_instance_export_locations(
                    share_instance['id'])['export_locations'])
            for el in export_locations:
                el = self.admin_client.get_share_instance_export_location(
                    share_instance['id'], el['id'])['export_location']
                self._verify_export_location_structure(el, format='detail')

    @decorators.idempotent_id('581acd8d-b89d-4684-8310-b910b46acc7a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_share_contains_all_export_locations_of_all_share_instances(self):
        share_export_locations = self.admin_client.list_share_export_locations(
            self.share['id'])['export_locations']
        share_instances_export_locations = []
        for share_instance in self.share_instances:
            share_instance_export_locations = (
                self.admin_client.list_share_instance_export_locations(
                    share_instance['id'])['export_locations'])
            share_instances_export_locations.extend(
                share_instance_export_locations)

        self.assertEqual(
            len(share_export_locations),
            len(share_instances_export_locations)
        )
        self.assertEqual(
            sorted(share_export_locations, key=lambda el: el['id']),
            sorted(share_instances_export_locations, key=lambda el: el['id'])
        )
