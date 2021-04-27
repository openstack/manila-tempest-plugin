# Copyright 2014 OpenStack Foundation
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

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base


class ShareServersNegativeAdminTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(ShareServersNegativeAdminTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client
        cls.member_client = cls.shares_v2_client

    @decorators.idempotent_id('6d55516f-9018-4372-8310-f725c4562961')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_list_share_servers_with_member(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.list_share_servers)

    @decorators.idempotent_id('d9021f06-c146-4e76-852e-8a1ebb3fa92e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_show_share_server_with_member(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.show_share_server,
                          'fake_id')

    @decorators.idempotent_id('16b6f911-487e-4c25-9241-75de2dbfc8ff')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_show_share_server_details_with_member(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.show_share_server_details,
                          'fake_id')

    @decorators.idempotent_id('f7580ef6-f7bb-4b52-ba45-82d2d2d66dbe')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_share_server_with_inexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.show_share_server,
                          'fake_id')

    @decorators.idempotent_id('368c5404-483e-4eee-bb80-86206d153ea2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_share_server_details_with_inexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.show_share_server_details,
                          'fake_id')

    @decorators.idempotent_id('664b5201-7ba9-4e33-9534-5307fc003e44')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_servers_with_wrong_filter_key(self):
        search_opts = {'fake_filter_key': 'ACTIVE'}
        servers = self.admin_client.list_share_servers(
            search_opts)['share_servers']
        self.assertEqual(0, len(servers))

    @decorators.idempotent_id('dcf169c9-1238-40cb-8a5c-ca6aca9d4d6b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_servers_with_wrong_filter_value(self):
        search_opts = {'host': 123}
        servers = self.admin_client.list_share_servers(
            search_opts)['share_servers']
        self.assertEqual(0, len(servers))

    @decorators.idempotent_id('3e5d6007-5214-4fa2-bd33-dfd3bead67bf')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_servers_with_fake_status(self):
        search_opts = {"status": data_utils.rand_name("fake_status")}
        servers = self.admin_client.list_share_servers(
            search_opts)['share_servers']
        self.assertEqual(0, len(servers))

    @decorators.idempotent_id('e893b32a-124f-4e5c-a425-58c8a4eac4a5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_servers_with_fake_host(self):
        search_opts = {"host": data_utils.rand_name("fake_host")}
        servers = self.admin_client.list_share_servers(
            search_opts)['share_servers']
        self.assertEqual(0, len(servers))

    @decorators.idempotent_id('2f1162a8-bb52-4e2a-abc0-68d16f769e4f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_servers_with_fake_project(self):
        search_opts = {"project_id": data_utils.rand_name("fake_project_id")}
        servers = self.admin_client.list_share_servers(
            search_opts)['share_servers']
        self.assertEqual(0, len(servers))

    @decorators.idempotent_id('ca23f385-56b2-4c02-9797-d88c3b7fb981')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_servers_with_fake_share_network(self):
        search_opts = {
            "share_network": data_utils.rand_name("fake_share_network"),
        }
        servers = self.admin_client.list_share_servers(
            search_opts)['share_servers']
        self.assertEqual(0, len(servers))

    @decorators.idempotent_id('0acb9107-18b2-4e9d-8432-37fd0d4c79b3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_server_with_nonexistent_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.admin_client.delete_share_server,
                          "fake_nonexistent_share_server_id")

    @decorators.idempotent_id('65e12bf7-2ec6-4a5b-971b-b1ecb67b77b7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_server_with_member(self):
        self.assertRaises(lib_exc.Forbidden,
                          self.member_client.delete_share_server,
                          "fake_nonexistent_share_server_id")
