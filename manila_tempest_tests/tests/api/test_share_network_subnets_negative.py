# Copyright 2019 NetApp Inc.
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
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class ShareNetworkSubnetsNegativeTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(ShareNetworkSubnetsNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported("2.51")

    @classmethod
    def resource_setup(cls):
        super(ShareNetworkSubnetsNegativeTest, cls).resource_setup()
        # Create a new share network which will be used in the tests
        cls.share_network = cls.shares_v2_client.create_share_network(
            cleanup_in_class=True)['share_network']
        cls.share_network_id = cls.share_network['id']
        cls.share_type = cls.create_share_type()
        cls.az = (
            cls.shares_v2_client.list_availability_zones()
            ['availability_zones'][0]
        )
        cls.az_name = cls.az['name']

    @decorators.idempotent_id('d20b6105-22d1-4fc0-8468-45dd019240c0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_network_subnet_share_network_not_found(self):
        data = utils.generate_subnet_data()
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.create_subnet,
                          'fake_inexistent_id',
                          **data)

    @decorators.idempotent_id('68264ac2-57e5-47ea-aa71-198c020be975')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_network_subnet_az_not_found(self):
        data = {'availability_zone': 'non-existent-az'}

        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_subnet,
                          self.share_network_id, **data)

    @decorators.idempotent_id('13f397bf-5e3a-42b0-b4f9-9cd2dbbb0955')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data(True, False)
    @utils.skip_if_is_microversion_ge(LATEST_MICROVERSION, "2.70")
    def test_add_share_network_subnet_in_same_az_exists(self, is_default):
        share_network = self.shares_v2_client.create_share_network(
            )['share_network']
        data = {}

        if not is_default:
            azs = self.get_availability_zones_matching_share_type(
                self.share_type)
            data['availability_zone'] = azs[0]
            self.shares_v2_client.create_subnet(
                share_network['id'], **data)

        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.create_subnet,
                          share_network['id'], **data)

    @decorators.idempotent_id('36e991c1-f09b-47dc-adc9-3da388b14612')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_network_subnet_missing_parameters(self):
        # Generate subnet data
        data = utils.generate_subnet_data()
        data['availability_zone'] = self.az_name

        data.pop('neutron_net_id')
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_subnet,
                          self.share_network_id, **data)

    @decorators.idempotent_id('11e76b07-f3e3-401f-9469-256b93a768e6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_subnet_share_network_not_found(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_subnet,
                          'fake-subnet',
                          'fake-sn')

    @decorators.idempotent_id('22d4528b-39ae-4f97-b1b2-1b9d65146c97')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_subnet_not_found(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_subnet,
                          'fake-subnet',
                          self.share_network_id)

    @decorators.idempotent_id('9dfc6ba3-c7be-4a6d-b104-ce77d2337bb3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_deleted_subnet(self):
        # Generate subnet data
        data = utils.generate_subnet_data()
        data['share_network_id'] = self.share_network_id
        az = self.shares_v2_client.list_availability_zones(
            )['availability_zones'][0]
        data['availability_zone'] = az['name']

        subnet = self.create_share_network_subnet(**data)

        # Make sure that the created subnet contains the data
        self.assertLessEqual(data.items(), subnet.items())

        # Delete the given subnet
        self.shares_v2_client.delete_subnet(self.share_network_id,
                                            subnet['id'])
        share_network = self.shares_v2_client.get_share_network(
            self.share_network_id
        )['share_network']

        self.assertIsNotNone(share_network)
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_subnet,
                          subnet['id'],
                          self.share_network['id'])

    @decorators.idempotent_id('bf9d63c4-37fb-4646-add7-905b196316f1')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(not CONF.share.multitenancy_enabled,
                      'Can run only with drivers that do handle share servers '
                      'creation. Skipping.')
    @testtools.skipIf(not CONF.share.run_manage_unmanage_tests,
                      'Can run only with manage/unmanage tests enabled.')
    def test_delete_contains_unmanaged_share_servers(self):
        # Get a compatible availability zone
        az = self.get_availability_zones_matching_share_type(
            self.share_type)[0]

        share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id
        )['share_network']
        share_network_id = share_network['id']
        subnet = utils.share_network_get_default_subnet(share_network)

        # Generate subnet data
        data = {'neutron_net_id': subnet['neutron_net_id'],
                'neutron_subnet_id': subnet['neutron_subnet_id'],
                'share_network_id': share_network_id,
                'availability_zone': az}

        # Create a new subnet in the desired az
        subnet = self.create_share_network_subnet(**data)

        args = {'share_network_id': share_network_id,
                'share_type_id': self.share_type['id'],
                'availability_zone': az}

        # Create a share into the share network
        share = self.shares_v2_client.create_share(**args)['share']
        waiters.wait_for_resource_status(
            self.shares_v2_client, share['id'], constants.STATUS_AVAILABLE)
        share = self.shares_v2_client.get_share(share['id'])['share']

        # Gets the export locations to be used in the future
        el = self.shares_v2_client.list_share_export_locations(
            share['id'])['export_locations']
        share['export_locations'] = el

        # Unmanages the share to make the share server become is_auto
        # deletable=False
        self._unmanage_share_and_wait(share)

        # Assert that the user cannot delete a subnet that contains share
        # servers which may have unmanaged stuff
        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.delete_subnet,
                          share_network_id,
                          subnet['id'])

        # Manages the share again to start cleaning up the test stuff
        managed_share = self.shares_v2_client.manage_share(
            service_host=share['host'],
            export_path=share['export_locations'][0],
            protocol=share['share_proto'],
            share_type_id=self.share_type['id'],
            name='share_to_be_deleted',
            description='share managed to be deleted',
            share_server_id=share['share_server_id']
        )['share']

        # Do some necessary cleanup
        waiters.wait_for_resource_status(
            self.shares_v2_client, managed_share['id'],
            constants.STATUS_AVAILABLE)
        self.shares_client.delete_share(managed_share['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            share_id=managed_share["id"])
        self._delete_share_server_and_wait(share['share_server_id'])
        self.shares_v2_client.delete_subnet(share_network_id,
                                            subnet['id'])

    @decorators.idempotent_id('5088edfe-2800-4dec-a982-42c864bba954')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(not CONF.share.multitenancy_enabled,
                      'Can run only with drivers that do handle share servers '
                      'creation. Skipping.')
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    def test_delete_contains_shares(self):
        # Get a compatible availability zone
        az = self.get_availability_zones_matching_share_type(
            self.share_type)[0]
        check_multiple_subnets = utils.is_microversion_ge(
            CONF.share.max_api_microversion, '2.70')
        original_share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id
        )['share_network']
        share_net_info = (
            utils.share_network_get_default_subnet(original_share_network))
        share_network = self.create_share_network(
            neutron_net_id=share_net_info['neutron_net_id'],
            neutron_subnet_id=share_net_info['neutron_subnet_id'],
        )
        share_network = self.shares_v2_client.get_share_network(
            share_network['id']
        )['share_network']
        share_network_id = share_network['id']
        default_subnet = share_network['share_network_subnets'][0]

        # Generate subnet data
        data = {'neutron_net_id': default_subnet['neutron_net_id'],
                'neutron_subnet_id': default_subnet['neutron_subnet_id'],
                'share_network_id': share_network_id,
                'availability_zone': az}

        # Create a new subnet in the desired az
        subnet = self.create_share_network_subnet(**data)

        args = {'share_network_id': share_network_id,
                'share_type_id': self.share_type['id'],
                'availability_zone': az}

        # Create a share into the share network
        share = self.shares_v2_client.create_share(**args)['share']
        waiters.wait_for_resource_status(
            self.shares_v2_client, share['id'], constants.STATUS_AVAILABLE)
        share = self.admin_shares_v2_client.get_share(share['id'])['share']
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id']
        )['share_server']
        # Match share server subnet
        if check_multiple_subnets:
            self.assertIn(subnet['id'],
                          share_server['share_network_subnet_ids'])
        else:
            self.assertEqual(subnet['id'],
                             share_server['share_network_subnet_id'])

        # Assert that the user cannot delete a subnet that contain shares
        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.delete_subnet,
                          share_network_id,
                          subnet['id'])
        # Assert that the user cannot delete a share-network that contain
        # shares
        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.delete_share_network,
                          share_network_id)
        # Cleanups
        self.shares_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(share_id=share["id"])
        self._delete_share_server_and_wait(share['share_server_id'])
        self.shares_v2_client.delete_subnet(share_network_id,
                                            subnet['id'])

    @decorators.idempotent_id('1025b69b-f1fd-4e44-b749-33779545ffe8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_subnet_share_network_not_found(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_subnet,
                          'fake-sn',
                          'fake-subnet')

    @decorators.idempotent_id('a5bdc817-0c34-4856-9732-f561e6ab5a83')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_subnet_not_found(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_subnet,
                          self.share_network_id,
                          'fake-subnet')
