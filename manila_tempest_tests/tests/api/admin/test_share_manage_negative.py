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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ManageNFSShareNegativeTest(base.BaseSharesAdminTest):
    protocol = 'nfs'

    # NOTE(lseki): be careful running these tests using generic driver
    # because cinder volumes will stay attached to service Nova VM and
    # won't be deleted.

    @classmethod
    def skip_checks(cls):
        super(ManageNFSShareNegativeTest, cls).skip_checks()
        if not CONF.share.run_manage_unmanage_tests:
            raise cls.skipException('Manage/unmanage tests are disabled.')

    @classmethod
    def resource_setup(cls):
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

        utils.skip_if_manage_not_supported_for_version()

        super(ManageNFSShareNegativeTest, cls).resource_setup()

        # Create share type
        cls.st_name = data_utils.rand_name("manage-st-name")
        cls.extra_specs = {
            'storage_protocol': CONF.share.capability_storage_protocol,
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
            'snapshot_support': CONF.share.capability_snapshot_support,
        }

        cls.st = cls.create_share_type(
            name=cls.st_name,
            cleanup_in_class=True,
            extra_specs=cls.extra_specs)

    def _manage_share_and_wait(self, params,
                               state=constants.STATUS_AVAILABLE):
        # Manage the share and wait for the expected state.
        # Return the managed share object.
        managed_share = self.shares_v2_client.manage_share(**params)
        self.shares_v2_client.wait_for_share_status(
            managed_share['id'], state)

        return managed_share

    def _get_manage_params_from_share(self, share, invalid_params=None):
        valid_params = {
            'service_host': share['host'],
            'protocol': share['share_proto'],
            'share_type_id': share['share_type'],
        }
        if CONF.share.multitenancy_enabled:
            valid_params['share_server_id'] = share['share_server_id']

        if utils.is_microversion_ge(CONF.share.max_api_microversion, "2.9"):
            el = self.shares_v2_client.list_share_export_locations(share["id"])
            valid_params['export_path'] = el[0]['path']

        if invalid_params:
            valid_params.update(invalid_params)

        return valid_params

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_invalid_param_raises_exception(self):
        # Try to manage share with invalid parameters, it should not succeed
        # because the api will reject it. If it succeeds, then this test case
        # failed. Then, in order to remove the resource from backend, we need
        # to manage it again, properly, so we can delete it. Consequently the
        # second part of this test also tests that manage operation with a
        # proper share type that works.

        share = self._create_share_for_manage()

        valid_params = self._get_manage_params_from_share(share)
        self._unmanage_share_and_wait(share)

        test_set = [
            ('service_host', 'invalid_host#invalid_pool', lib_exc.NotFound),
            ('share_type_id', 'invalid_share_type_id', lib_exc.NotFound),
        ]
        if CONF.share.multitenancy_enabled:
            test_set.append(
                ('share_server_id', 'invalid_server_id', lib_exc.BadRequest)
            )

        for invalid_key, invalid_value, expected_exception in test_set:
            # forge a bad param
            invalid_params = valid_params.copy()
            invalid_params.update({
                invalid_key: invalid_value
            })

            # the attempt to manage with bad param should fail and raise an
            # exception
            self.assertRaises(
                expected_exception,
                self.shares_v2_client.manage_share,
                **invalid_params
            )

        # manage it properly and cleanup
        managed_share = self._manage_share_and_wait(valid_params)
        self._delete_share_and_wait(managed_share)

        # Delete share server, since it can't be "auto-deleted"
        if (CONF.share.multitenancy_enabled and
                not CONF.share.share_network_id):
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(
                managed_share['share_server_id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_invalid_param_manage_error(self):
        # Try to manage share with invalid parameters, it should not succeed.
        # If it succeeds, then this test case failed. Then, in order to remove
        # the resource from backend, we need to manage it again, properly, so
        # we can delete it. Consequently the second part of this test also
        # tests that manage operation with a proper share type works.
        share = self._create_share_for_manage()

        valid_params = self._get_manage_params_from_share(share)
        self._unmanage_share_and_wait(share)

        for invalid_key, invalid_value in (
            ('export_path', 'invalid_export'),
            ('protocol', 'invalid_protocol'),
        ):

            # forge a bad param
            invalid_params = valid_params.copy()
            invalid_params.update({invalid_key: invalid_value})

            # the attempt to manage the share with invalid params should fail
            # and leave it in manage_error state
            invalid_share = self.shares_v2_client.manage_share(
                **invalid_params
            )
            self.shares_v2_client.wait_for_share_status(
                invalid_share['id'], constants.STATUS_MANAGE_ERROR)

            # cleanup
            self._unmanage_share_and_wait(invalid_share)

        # manage it properly and cleanup
        managed_share = self._manage_share_and_wait(valid_params)
        self._delete_share_and_wait(managed_share)

        # Delete share server, since it can't be "auto-deleted"
        if (CONF.share.multitenancy_enabled and
                not CONF.share.share_network_id):
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(
                managed_share['share_server_id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share_duplicate(self):
        share = self._create_share_for_manage()

        manage_params = self._get_manage_params_from_share(share)
        self._unmanage_share_and_wait(share)

        # manage the share for the first time
        managed_share = self._manage_share_and_wait(manage_params)

        # update managed share's reference
        managed_share = self.shares_v2_client.get_share(managed_share['id'])
        manage_params = self._get_manage_params_from_share(managed_share)

        # the second attempt to manage the same share should fail
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.manage_share,
            **manage_params
        )

        # cleanup
        self._delete_share_and_wait(managed_share)

        # Delete share server, since it can't be "auto-deleted"
        if (CONF.share.multitenancy_enabled and
                not CONF.share.share_network_id):
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(
                managed_share['share_server_id'])

    @testtools.skipUnless(CONF.share.multitenancy_enabled,
                          'Multitenancy tests are disabled.')
    @utils.skip_if_microversion_not_supported("2.49")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_share_without_share_server_id(self):
        share = self._create_share_for_manage()
        manage_params = self._get_manage_params_from_share(share)
        share_server_id = manage_params.pop('share_server_id')
        self._unmanage_share_and_wait(share)

        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.manage_share,
            **manage_params)

        manage_params['share_server_id'] = share_server_id

        managed_share = self._manage_share_and_wait(manage_params)
        self._delete_share_and_wait(managed_share)

        # Delete share server, since it can't be "auto-deleted"
        if (CONF.share.multitenancy_enabled and
                not CONF.share.share_network_id):
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(
                managed_share['share_server_id'])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share_in_manage_error(self):
        share = self._create_share_for_manage()

        valid_params = self._get_manage_params_from_share(share)

        # forge bad param to have a share in manage_error state
        invalid_params = valid_params.copy()
        invalid_params.update({'export_path': 'invalid'})
        invalid_share = self.shares_v2_client.manage_share(**invalid_params)

        self.shares_v2_client.wait_for_share_status(
            invalid_share['id'], constants.STATUS_MANAGE_ERROR)
        self._unmanage_share_and_wait(share)

        # the attempt to delete a share in manage_error should raise an
        # exception
        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.delete_share,
            invalid_share['id']
        )

        # cleanup
        self.shares_v2_client.unmanage_share(invalid_share['id'])
        managed_share = self._manage_share_and_wait(valid_params)
        self._delete_share_and_wait(managed_share)

        # Delete share server, since it can't be "auto-deleted"
        if (CONF.share.multitenancy_enabled and
                not CONF.share.share_network_id):
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(
                managed_share['share_server_id'])

    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          'Snapshot tests are disabled.')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share_with_snapshot(self):
        # A share with snapshot cannot be unmanaged
        share = self._create_share_for_manage()

        snap = self.create_snapshot_wait_for_active(share["id"])
        snap = self.shares_v2_client.get_snapshot(snap['id'])

        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.unmanage_share,
            share['id']
        )

        # cleanup
        self._delete_snapshot_and_wait(snap)
        self._delete_share_and_wait(share)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share_transitional_state(self):
        # A share in transitional state cannot be unmanaged
        share = self._create_share_for_manage()
        for state in (constants.STATUS_CREATING,
                      constants.STATUS_DELETING,
                      constants.STATUS_MIGRATING,
                      constants.STATUS_MIGRATING_TO):
            self.shares_v2_client.reset_state(share['id'], state)

            self.assertRaises(
                lib_exc.Forbidden,
                self.shares_v2_client.unmanage_share,
                share['id']
            )

        # cleanup
        self._reset_state_and_delete_share(share)

    @testtools.skipUnless(CONF.share.multitenancy_enabled,
                          'Multitenancy tests are disabled.')
    @utils.skip_if_microversion_not_supported("2.48")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_share_with_server_unsupported(self):
        share = self._create_share_for_manage()

        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.unmanage_share,
            share['id'], version="2.48")

        self._delete_share_and_wait(share)


class ManageCIFSShareNegativeTest(ManageNFSShareNegativeTest):
    protocol = 'cifs'


class ManageGLUSTERFSShareNegativeTest(ManageNFSShareNegativeTest):
    protocol = 'glusterfs'


class ManageHDFSShareNegativeTest(ManageNFSShareNegativeTest):
    protocol = 'hdfs'


class ManageCephFSShareNegativeTest(ManageNFSShareNegativeTest):
    protocol = 'cephfs'


class ManageMapRFSShareNegativeTest(ManageNFSShareNegativeTest):
    protocol = 'maprfs'
