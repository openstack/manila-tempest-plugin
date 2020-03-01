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
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ExportLocationsNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ExportLocationsNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_lt("2.9")

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
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(client=cls.admin_client,
                                     share_type_id=cls.share_type_id)
        cls.share = cls.admin_client.get_share(cls.share['id'])
        cls.share_instances = cls.admin_client.get_instances_of_share(
            cls.share['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_share_export_location(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.admin_client.get_share_export_location,
            self.share['id'],
            "fake-inexistent-share-instance-id",
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_inexistent_share_instance_export_location(self):
        for share_instance in self.share_instances:
            self.assertRaises(
                lib_exc.NotFound,
                self.admin_client.get_share_instance_export_location,
                share_instance['id'],
                "fake-inexistent-share-instance-id",
            )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share_instance_export_locations_as_member(self):
        for share_instance in self.share_instances:
            self.assertRaises(
                lib_exc.Forbidden,
                self.admin_member_client.list_share_instance_export_locations,
                share_instance['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_instance_export_locations_as_member(self):
        for share_instance in self.share_instances:
            export_locations = (
                self.admin_client.list_share_instance_export_locations(
                    share_instance['id']))
            for el in export_locations:
                self.assertRaises(lib_exc.Forbidden,
                                  (self.admin_member_client.
                                   get_share_instance_export_location),
                                  share_instance['id'], el['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share_export_locations_by_different_project_user(self):
        self.assertRaises(
            lib_exc.Forbidden,
            self.different_project_client.list_share_export_locations,
            self.share['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_export_location_by_different_project_user(self):
        export_locations = self.admin_client.list_share_export_locations(
            self.share['id'])

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
        utils.check_skip_if_microversion_lt("2.9")

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_export_locations_by_nonexistent_share(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.list_share_export_locations,
            "fake-inexistent-share-id",
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_export_locations_by_nonexistent_share_instance(self):
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.list_share_instance_export_locations,
            "fake-inexistent-share-instance-id",
        )
