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

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ExportLocationsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ExportLocationsNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.9")

    @classmethod
    def resource_setup(cls):
        super(ExportLocationsNegativeTest, cls).resource_setup()
        # admin_client and different_project_client pertain to isolated
        # projects, admin_member_client is a regular user in admin's project
        cls.admin_client = cls.admin_shares_v2_client
        cls.admin_member_client = (
            cls.admin_project_member_client.shares_v2_client)
        cls.different_project_client = cls.shares_v2_client
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(client=cls.admin_client,
                                     share_type_id=cls.share_type_id)
        cls.share = cls.admin_client.get_share(cls.share['id'])['share']
        cls.share_instances = cls.admin_client.get_instances_of_share(
            cls.share['id'])['share_instances']

    @decorators.idempotent_id('8eac1355-f272-4913-8a49-1a8a9cb086bd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_share_export_location(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.get_share_export_location,
            self.share['id'],
            "fake-inexistent-share-instance-id",
        )

    @decorators.idempotent_id('064a18dd-1a00-42f1-84c0-5a3e3b46fb39')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_share_instance_export_location(self):
        for share_instance in self.share_instances:
            self.assertRaises(
                lib_exc.NotFound,
                self.admin_client.get_share_instance_export_location,
                share_instance['id'],
                "fake-inexistent-share-instance-id",
            )

    @decorators.idempotent_id('6d0b9d1b-fc87-4b7f-add5-919b0ddcda90')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share_instance_export_locations_as_member(self):
        for share_instance in self.share_instances:
            self.assertRaises(
                lib_exc.Forbidden,
                self.admin_member_client.list_share_instance_export_locations,
                share_instance['id'])

    @decorators.idempotent_id('abde4357-a26c-4adb-88a6-ece6b0e15b5e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_instance_export_locations_as_member(self):
        for share_instance in self.share_instances:
            export_locations = (
                self.admin_client.list_share_instance_export_locations(
                    share_instance['id'])['export_locations'])
            for el in export_locations:
                self.assertRaises(lib_exc.Forbidden,
                                  (self.admin_member_client.
                                   get_share_instance_export_location),
                                  share_instance['id'], el['id'])

    @decorators.idempotent_id('a3c3d16b-5f62-4089-8f86-efc660592986')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share_export_locations_by_different_project_user(self):
        self.assertRaises(
            lib_exc.Forbidden,
            self.different_project_client.list_share_export_locations,
            self.share['id'])

    @decorators.idempotent_id('0f6823a5-3929-4025-9cd4-b5198b4384dd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_export_location_by_different_project_user(self):
        export_locations = self.admin_client.list_share_export_locations(
            self.share['id'])['export_locations']

        for export_location in export_locations:
            self.assertRaises(
                lib_exc.Forbidden,
                self.different_project_client.get_share_export_location,
                self.share['id'],
                export_location['id'])


class ExportLocationsAPIOnlyNegativeTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(ExportLocationsAPIOnlyNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.9")

    @decorators.idempotent_id('4b5b4e89-0c80-4383-b272-62d5e0419d9a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_export_locations_by_nonexistent_share(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.list_share_export_locations,
            "fake-inexistent-share-id",
        )

    @decorators.idempotent_id('21ba5111-91a8-4ec3-86dc-689fc2fa90e6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_export_locations_by_nonexistent_share_instance(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.list_share_instance_export_locations,
            "fake-inexistent-share-instance-id",
        )
