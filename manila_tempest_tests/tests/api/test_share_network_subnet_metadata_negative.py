# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


class ShareNetworkSubnetMetadataNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareNetworkSubnetMetadataNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.78")

    @classmethod
    def resource_setup(cls):
        super(ShareNetworkSubnetMetadataNegativeTest, cls).resource_setup()
        # create share_network and subnet
        cls.share_network = cls.create_share_network()
        az = cls.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        cls.az_name = az['name']

        data = utils.generate_subnet_data()
        data['share_network_id'] = cls.share_network['id']
        data['availability_zone'] = cls.az_name

        cls.subnet = cls.create_share_network_subnet(**data)

    @decorators.idempotent_id('852d080f-16f3-48c4-af26-d8440be9801b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_metadata_to_unexisting_subnet(self):
        share_network = self.create_share_network()
        md = {"key1": "value1", "key2": "value2", }
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.set_metadata,
                          "wrong_subnet_id", md, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=share_network['id'])

    @decorators.idempotent_id('dfe93a02-43cc-458c-92e5-ede6c2c2e597')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_all_metadata_to_unexisting_subnet(self):
        share_network = self.create_share_network()
        md = {"key1": "value1", "key2": "value2", }
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.update_all_metadata,
                          "wrong_subnet_id", md, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=share_network['id'])

    @decorators.idempotent_id('fc561d8e-a2df-468f-a760-7b5d340b4b29')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_metadata_with_empty_key(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.set_metadata,
                          self.subnet['id'], {"": "value"}, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])

    @decorators.idempotent_id('b6066659-d635-4f24-9a65-fa3a132fd5ad')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_upd_metadata_with_empty_key(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_all_metadata,
                          self.subnet['id'], {"": "value"}, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])

    @decorators.idempotent_id('a1ea51a6-01a4-4b12-8508-04e45fdabb13')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_metadata_with_too_big_key(self):
        too_big_key = "x" * 256
        md = {too_big_key: "value"}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.set_metadata,
                          self.subnet['id'], md, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])

    @decorators.idempotent_id('a02e3970-a3d3-4c0f-a7b8-2ea3f4459214')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_upd_metadata_with_too_big_key(self):
        too_big_key = "x" * 256
        md = {too_big_key: "value"}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_all_metadata,
                          self.subnet['id'], md, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])

    @decorators.idempotent_id('f086589e-81a2-4d73-9fb0-9dd235cd35f1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_metadata_with_too_big_value(self):
        too_big_value = "x" * 1024
        md = {"key": too_big_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.set_metadata,
                          self.subnet['id'], md, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])

    @decorators.idempotent_id('4693e944-4b85-4655-8245-f1da2b5f9ff3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_upd_metadata_with_too_big_value(self):
        too_big_value = "x" * 1024
        md = {"key": too_big_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_all_metadata,
                          self.subnet['id'], md, resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])

    @decorators.idempotent_id('30e82c73-edd3-4f23-8b8f-c38e67668381')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_unexisting_metadata(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_metadata,
                          self.subnet['id'], "wrong_key", resource="subnet",
                          parent_resource="share-networks",
                          parent_id=self.share_network['id'])
