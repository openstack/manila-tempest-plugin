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
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


class ShareNetworkSubnetMetadataTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareNetworkSubnetMetadataTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.78")

    @classmethod
    def resource_setup(cls):
        super(ShareNetworkSubnetMetadataTest, cls).resource_setup()
        # create share_network and subnet
        cls.share_network = cls.create_share_network(cleanup_in_class=True)
        az = cls.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        cls.az_name = az['name']

        cls.data = utils.generate_subnet_data()
        cls.data['share_network_id'] = cls.share_network['id']
        cls.data['availability_zone'] = cls.az_name

        cls.subnet = cls.create_share_network_subnet(cleanup_in_class=True,
                                                     **cls.data)

    def _verify_subnet_metadata(self, subnet, md):
        # get metadata of share-network-subnet
        metadata = self.shares_v2_client.get_metadata(
            subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=subnet['share_network_id'])['metadata']

        # verify metadata
        self.assertEqual(md, metadata)

        # verify metadata items
        for key in md:
            get_value = self.shares_v2_client.get_metadata_item(
                subnet['id'], key, resource="subnet",
                parent_resource="share-networks",
                parent_id=subnet['share_network_id'])['meta']
            self.assertEqual(md[key], get_value[key])

    @decorators.idempotent_id('260744c2-c062-4ce3-a57e-cce475650e7b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_in_subnet_creation(self):
        share_network = self.create_share_network()
        az = self.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        az_name = az['name']

        # Generate subnet data
        data = utils.generate_subnet_data()
        data['share_network_id'] = share_network['id']
        data['availability_zone'] = az_name

        md = {"key1": "value1", "key2": "value2", }

        # create network subnet with metadata
        subnet = self.create_share_network_subnet(metadata=md,
                                                  cleanup_in_class=False,
                                                  **data)

        # verify metadata
        self._verify_subnet_metadata(subnet, md)

        # Delete the subnets
        self.shares_v2_client.delete_subnet(share_network['id'], subnet['id'])

    @decorators.idempotent_id('ec5c02e9-fcee-4890-87bc-7937a247afe9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_get_delete_metadata(self):
        md = {"key3": "value3", "key4": "value4", "key.5.1": "value.5"}

        # create subnet
        subnet = self.create_share_network_subnet(**self.data)

        # set metadata
        self.shares_v2_client.set_metadata(
            subnet['id'], md, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        # verify metadata
        self._verify_subnet_metadata(subnet, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(
                subnet['id'], key, resource="subnet",
                parent_resource="share-networks",
                parent_id=self.share_network['id'])

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']
        self.assertEmpty(get_metadata)

        # Delete the subnet
        self.shares_v2_client.delete_subnet(self.share_network['id'],
                                            subnet['id'])

    @decorators.idempotent_id('9ff9c3b4-9bd0-4e8a-a317-726cab640a67')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_not_delete_pre_metadata(self):
        md1 = {"key9": "value9", "key10": "value10", }
        md2 = {"key11": "value11", "key12": "value12", }

        # create subnet
        subnet = self.create_share_network_subnet(**self.data)

        # set metadata
        self.shares_v2_client.set_metadata(
            subnet['id'], md1, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        # verify metadata
        self._verify_subnet_metadata(subnet, md1)

        # set metadata again
        self.shares_v2_client.set_metadata(
            subnet['id'], md2, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        md1.update(md2)
        md = md1

        # verify metadata
        self._verify_subnet_metadata(subnet, md)

        # delete metadata
        for key in md.keys():
            self.shares_v2_client.delete_metadata(
                subnet['id'], key, resource="subnet",
                parent_resource="share-networks",
                parent_id=self.share_network['id'])

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']
        self.assertEmpty(get_metadata)

        # Delete the subnet
        self.shares_v2_client.delete_subnet(self.share_network['id'],
                                            subnet['id'])

    @decorators.idempotent_id('1973bcb0-93a5-49a5-84fb-a03f6f6ff43b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_key_already_exist(self):
        md1 = {"key9": "value9", "key10": "value10", }
        md2 = {"key9": "value13", "key11": "value11", }

        # create subnet
        subnet = self.create_share_network_subnet(**self.data)

        # set metadata
        self.shares_v2_client.set_metadata(
            subnet['id'], md1, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        # verify metadata
        self._verify_subnet_metadata(subnet, md1)

        # set metadata again
        self.shares_v2_client.set_metadata(
            subnet['id'], md2, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        # verify metadata
        md1.update(md2)
        self._verify_subnet_metadata(subnet, md1)

        # delete metadata
        for key in md1.keys():
            self.shares_v2_client.delete_metadata(
                subnet['id'], key, resource="subnet",
                parent_resource="share-networks",
                parent_id=self.share_network['id'])

        # verify deletion of metadata
        get_metadata = self.shares_v2_client.get_metadata(
            subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']
        self.assertEmpty(get_metadata)

        # Delete the subnets
        self.shares_v2_client.delete_subnet(self.share_network['id'],
                                            subnet['id'])

    @decorators.idempotent_id('d37ea163-7215-4c35-996a-1bc165e554de')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_and_update_metadata_by_key(self):
        md1 = {"key5": "value5", "key6": "value6", }
        md2 = {"key7": "value7", "key8": "value8", }

        # create subnet
        subnet = self.create_share_network_subnet(**self.data)

        # set metadata
        self.shares_v2_client.set_metadata(
            subnet['id'], md1, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        # update metadata
        self.shares_v2_client.update_all_metadata(
            subnet['id'], md2, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        # verify metadata
        self._verify_subnet_metadata(subnet, md2)

        # Delete the subnets
        self.shares_v2_client.delete_subnet(self.share_network['id'],
                                            subnet['id'])

    @decorators.idempotent_id('20b96e7e-33cf-41f2-8f00-357170fa27f9')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_v2_client.set_metadata(self.subnet['id'],
                                           data, resource="subnet",
                                           parent_resource="share-networks",
                                           parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']
        self.assertEqual(data['k'], body_get.get('k'))

    @decorators.idempotent_id('b7933b35-04e7-4487-8e6a-730f7261a736')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_v2_client.set_metadata(self.subnet['id'],
                                           data, resource="subnet",
                                           parent_resource="share-networks",
                                           parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertIn(max_key, body_get)
        self.assertEqual(data[max_key], body_get.get(max_key))

    @decorators.idempotent_id('469cd8ca-5846-4ff7-9a94-1087fc369e0f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_v2_client.set_metadata(self.subnet['id'],
                                           data, resource="subnet",
                                           parent_resource="share-networks",
                                           parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('5aa3b4a2-79d3-4fa4-b923-eb120bbe2f29')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_set_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_v2_client.set_metadata(self.subnet['id'],
                                           data, resource="subnet",
                                           parent_resource="share-networks",
                                           parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertEqual(data['key'], body_get['key'])

    @decorators.idempotent_id('336970cb-eb04-4d08-9941-44c1267c1d5a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_upd_metadata_min_size_key(self):
        data = {"k": "value"}

        self.shares_v2_client.update_all_metadata(
            self.subnet['id'], data, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertEqual(data, body_get)

    @decorators.idempotent_id('93ec3f28-4cd7-48da-8418-e945b9ec4530')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_upd_metadata_max_size_key(self):
        max_key = "k" * 255
        data = {max_key: "value"}

        self.shares_v2_client.update_all_metadata(
            self.subnet['id'], data, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertEqual(data, body_get)

    @decorators.idempotent_id('f9372c69-559a-47b8-b6a2-0b2876d7a985')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_upd_metadata_min_size_value(self):
        data = {"key": "v"}

        self.shares_v2_client.update_all_metadata(
            self.subnet['id'], data, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertEqual(data, body_get)

    @decorators.idempotent_id('fdb6696f-910a-41a7-aab3-79addad86936')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_upd_metadata_max_size_value(self):
        max_value = "v" * 1023
        data = {"key": max_value}

        self.shares_v2_client.update_all_metadata(
            self.subnet['id'], data, resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])

        body_get = self.shares_v2_client.get_metadata(
            self.subnet['id'], resource="subnet",
            parent_resource="share-networks",
            parent_id=self.share_network['id'])['metadata']

        self.assertEqual(data, body_get)
