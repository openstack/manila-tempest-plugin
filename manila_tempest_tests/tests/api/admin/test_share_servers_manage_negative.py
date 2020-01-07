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
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class ManageShareServersNegativeTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(ManageShareServersNegativeTest, cls).skip_checks()
        if not CONF.share.multitenancy_enabled:
            raise cls.skipException('Multitenancy tests are disabled.')
        if not CONF.share.run_manage_unmanage_tests:
            raise cls.skipException('Manage/unmanage tests are disabled.')

        utils.check_skip_if_microversion_lt('2.49')

    @classmethod
    def resource_setup(cls):
        super(ManageShareServersNegativeTest, cls).resource_setup()

        # create share type
        cls.st_name = data_utils.rand_name("manage-st-name")
        cls.extra_specs = {
            'storage_protocol': CONF.share.capability_storage_protocol,
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }
        cls.share_type = cls.create_share_type(
            name=cls.st_name,
            cleanup_in_class=True,
            extra_specs=cls.extra_specs)
        cls.original_share_network = cls.shares_v2_client.get_share_network(
            cls.shares_v2_client.share_network_id)
        cls.share_net_info = (
            utils.share_network_get_default_subnet(cls.original_share_network)
            if utils.share_network_subnets_are_supported() else
            cls.original_share_network)

    def _create_share_with_new_share_network(self):
        share_network = self.create_share_network(
            neutron_net_id=self.share_net_info['neutron_net_id'],
            neutron_subnet_id=self.share_net_info['neutron_subnet_id'],
            cleanup_in_class=True
        )
        share = self.create_share(
            share_type_id=self.share_type['share_type']['id'],
            share_network_id=share_network['id']
        )
        return self.shares_v2_client.get_share(share['id'])

    @ddt.data(
        ('host', 'invalid_host'),
        ('share_network_id', 'invalid_share_network_id'),
        ('share_network_subnet_id', 'invalid_share_network_subnet_id'),
    )
    @ddt.unpack
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share_server_invalid_params(self, param, invalid_value):

        sn_subnets_not_supported = utils.is_microversion_lt(
            LATEST_MICROVERSION, utils.SHARE_NETWORK_SUBNETS_MICROVERSION)
        if param == 'share_network_subnet_id' and sn_subnets_not_supported:
            raise self.skipException("Share network subnets not supported by "
                                     "microversion %s" % LATEST_MICROVERSION)

        # create share
        share = self._create_share_with_new_share_network()
        el = self.shares_v2_client.list_share_export_locations(share['id'])
        share['export_locations'] = el
        share_server = self.shares_v2_client.show_share_server(
            share['share_server_id']
        )

        self._unmanage_share_and_wait(share)
        self._unmanage_share_server_and_wait(share_server)

        # forge invalid params
        invalid_params = share_server.copy()
        invalid_params[param] = invalid_value

        # try to manage in the wrong way
        self.assertRaises(
            lib_exc.BadRequest,
            self._manage_share_server,
            share_server,
            invalid_params
        )

        # manage in the correct way
        managed_share_server = self._manage_share_server(share_server)
        managed_share = self._manage_share(
            share,
            name="managed share that had ID %s" % share['id'],
            description="description for managed share",
            share_server_id=managed_share_server['id']
        )

        # delete share
        self._delete_share_and_wait(managed_share)

        # delete share server
        self._delete_share_server_and_wait(managed_share_server['id'])

    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share_server_invalid_state(self):

        # create share
        share = self._create_share_with_new_share_network()

        for state in (constants.SERVER_STATE_MANAGE_STARTING,
                      constants.SERVER_STATE_CREATING,
                      constants.SERVER_STATE_DELETING):
            # leave it in the wrong state
            self.shares_v2_client.share_server_reset_state(
                share['share_server_id'],
                status=state,
            )

            # try to delete
            self.assertRaises(
                lib_exc.Forbidden,
                self.shares_v2_client.delete_share_server,
                share['share_server_id'],
            )

            # put it in the correct state
            self.shares_v2_client.share_server_reset_state(
                share['share_server_id'],
                status=constants.SERVER_STATE_ACTIVE,
            )
            self.shares_v2_client.wait_for_share_server_status(
                share['share_server_id'],
                constants.SERVER_STATE_ACTIVE,
            )

        # delete share
        self._delete_share_and_wait(share)

        # delete share server
        self._delete_share_server_and_wait(share['share_server_id'])

    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share_server_invalid_state(self):

        # create share
        share = self._create_share_with_new_share_network()

        for state in (constants.SERVER_STATE_MANAGE_STARTING,
                      constants.SERVER_STATE_CREATING,
                      constants.SERVER_STATE_DELETING):
            # leave it in the wrong state
            self.shares_v2_client.share_server_reset_state(
                share['share_server_id'],
                status=state,
            )

            # try to unmanage
            self.assertRaises(
                lib_exc.BadRequest,
                self.shares_v2_client.unmanage_share_server,
                share['share_server_id'],
            )

            # put it in the correct state
            self.shares_v2_client.share_server_reset_state(
                share['share_server_id'],
                status=constants.SERVER_STATE_ACTIVE,
            )
            self.shares_v2_client.wait_for_share_server_status(
                share['share_server_id'],
                constants.SERVER_STATE_ACTIVE,
            )

        # delete share
        self._delete_share_and_wait(share)

        # delete share server
        self._delete_share_server_and_wait(share['share_server_id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_reset_state_invalid_state(self):

        # create share
        share = self.create_share(
            share_type_id=self.share_type['share_type']['id'])
        share = self.shares_v2_client.get_share(share['id'])

        # try to change it to wrong state
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.share_server_reset_state,
            share['share_server_id'],
            status='invalid_state',
        )

        # delete share
        self._delete_share_and_wait(share)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share_server_with_share(self):

        # create share
        share = self.create_share(
            share_type_id=self.share_type['share_type']['id'])
        share = self.shares_v2_client.get_share(share['id'])

        # try to unmanage
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.unmanage_share_server,
            share['share_server_id'],
        )

        # delete share
        self._delete_share_and_wait(share)

    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share_network.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share_server_invalid_identifier(self):
        # create share
        share = self._create_share_with_new_share_network()
        el = self.shares_v2_client.list_share_export_locations(share['id'])
        share['export_locations'] = el
        share_server = self.shares_v2_client.show_share_server(
            share['share_server_id']
        )

        self._unmanage_share_and_wait(share)
        self._unmanage_share_server_and_wait(share_server)

        # forge invalid params
        invalid_params = share_server.copy()
        invalid_params['identifier'] = 'invalid_id'

        self.assertRaises(
            share_exceptions.ShareServerBuildErrorException,
            self._manage_share_server,
            invalid_params
        )

        # unmanage the share server in manage_error
        search_opts = {'identifier': 'invalid_id'}
        invalid_servers = self.shares_v2_client.list_share_servers(search_opts)
        self._unmanage_share_server_and_wait(invalid_servers[0])

        # manage in the correct way
        managed_share_server = self._manage_share_server(share_server)
        managed_share_server = self.shares_v2_client.show_share_server(
            managed_share_server['id']
        )
        managed_share = self._manage_share(
            share,
            name="managed share that had ID %s" % share['id'],
            description="description for managed share",
            share_server_id=managed_share_server['id']
        )

        # delete share
        self._delete_share_and_wait(managed_share)

        # delete share server
        self._delete_share_server_and_wait(managed_share_server['id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share_server_double_manage(self):

        # create share
        share = self.create_share(
            share_type_id=self.share_type['share_type']['id'])
        share = self.shares_v2_client.get_share(share['id'])

        share_server = self.shares_v2_client.show_share_server(
            share['share_server_id'])

        # try with more data around the identifier
        invalid_params = share_server.copy()
        invalid_params['identifier'] = (
            'foo_' + share_server['identifier'] + '_bar')

        self.assertRaises(
            lib_exc.BadRequest,
            self._manage_share_server,
            invalid_params)

        # try with part of the identifier
        invalid_params['identifier'] = share_server['identifier'].split("-")[2]

        self.assertRaises(
            lib_exc.BadRequest,
            self._manage_share_server,
            invalid_params)

        # try with same identifier but underscores
        invalid_params['identifier'] = (
            share_server['identifier'].replace("-", "_"))

        self.assertRaises(
            lib_exc.BadRequest,
            self._manage_share_server,
            invalid_params)

        # delete share
        self._delete_share_and_wait(share)

        # Delete share server, since it can't be "auto-deleted"
        if not CONF.share.share_network_id:
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(share_server['id'])
