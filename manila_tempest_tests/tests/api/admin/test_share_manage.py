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
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF


@ddt.ddt
class ManageNFSShareTest(base.BaseSharesAdminTest):
    protocol = 'nfs'

    # NOTE(vponomaryov): be careful running these tests using generic driver
    # because cinder volumes will stay attached to service Nova VM and
    # won't be deleted.

    @classmethod
    def skip_checks(cls):
        super(ManageNFSShareTest, cls).skip_checks()
        if not CONF.share.run_manage_unmanage_tests:
            raise cls.skipException('Manage/unmanage tests are disabled.')
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)
        utils.skip_if_manage_not_supported_for_version()

    @classmethod
    def resource_setup(cls):
        super(ManageNFSShareTest, cls).resource_setup()
        # Create share type
        cls.st_name = data_utils.rand_name("manage-st-name")
        cls.extra_specs = {
            'storage_protocol': CONF.share.capability_storage_protocol,
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
        }

        cls.st = cls.create_share_type(
            name=cls.st_name,
            cleanup_in_class=True,
            extra_specs=cls.extra_specs)

    def _test_manage(self, is_public=False,
                     version=CONF.share.max_api_microversion,
                     check_manage=False):

        utils.skip_if_manage_not_supported_for_version(version)

        share = self._create_share_for_manage()

        name = "Name for 'managed' share that had ID %s" % share['id']
        description = "Description for 'managed' share"

        # Unmanage share
        self._unmanage_share_and_wait(share)

        if check_manage:
            # After 'unmanage' operation, share instance should be deleted.
            # Assert not related to 'manage' test, but placed here for
            # resource optimization.
            share_instance_list = self.shares_v2_client.list_share_instances(
                )['share_instances']
            share_ids = [si['share_id'] for si in share_instance_list]
            self.assertNotIn(share['id'], share_ids)

        export_path = share['export_locations'][0]
        if utils.is_microversion_ge(version, "2.8"):
            export_path = share['export_locations'][0]['path']

        # Manage share
        manage_params = {
            'service_host': share['host'],
            'export_path': export_path,
            'protocol': share['share_proto'],
            'share_type_id': self.st['id'],
            'name': name,
            'description': description,
            'is_public': is_public,
            'version': version,
        }
        if CONF.share.multitenancy_enabled:
            manage_params['share_server_id'] = share['share_server_id']
        managed_share = self.shares_v2_client.manage_share(
            **manage_params)['share']

        # Add managed share to cleanup queue
        self.method_resources.insert(
            0, {'type': 'share', 'id': managed_share['id'],
                'client': self.shares_client})

        # Wait for success
        waiters.wait_for_resource_status(self.shares_v2_client,
                                         managed_share['id'],
                                         constants.STATUS_AVAILABLE)

        # Verify data of managed share
        self.assertEqual(name, managed_share['name'])
        self.assertEqual(description, managed_share['description'])
        self.assertEqual(share['host'], managed_share['host'])
        self.assertEqual(share['share_proto'], managed_share['share_proto'])

        if utils.is_microversion_ge(version, "2.6"):
            self.assertEqual(self.st['id'],
                             managed_share['share_type'])
        else:
            self.assertEqual(self.st['name'],
                             managed_share['share_type'])

        if utils.is_microversion_ge(version, "2.8"):
            self.assertEqual(is_public, managed_share['is_public'])
        else:
            self.assertFalse(managed_share['is_public'])

        if utils.is_microversion_ge(version, "2.16"):
            self.assertEqual(share['user_id'], managed_share['user_id'])
        else:
            self.assertNotIn('user_id', managed_share)

        # Delete share
        self._delete_share_and_wait(managed_share)

        # Delete share server, since it can't be "auto-deleted"
        if (CONF.share.multitenancy_enabled and
                not CONF.share.share_network_id):
            # For a pre-configured share_network_id, we don't
            # delete the share server.
            self._delete_share_server_and_wait(
                managed_share['share_server_id'])

    @decorators.idempotent_id('15b654d0-34ed-4154-9f5f-b96d2e4e9d1c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.5")
    def test_manage_with_os_share_manage_url(self):
        self._test_manage(version="2.5")

    @decorators.idempotent_id('8c0beefb-19da-441e-b73f-d90eb8000ff3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.8")
    def test_manage_with_is_public_True(self):
        self._test_manage(is_public=True, version="2.8")

    @decorators.idempotent_id('da7b7a4f-6693-4460-bdb7-1f8d42032bc6')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.16")
    def test_manage_show_user_id(self):
        self._test_manage(version="2.16")

    @decorators.idempotent_id('24ec7840-0174-484f-8b3a-8c6f162bf576')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_manage(self):
        self._test_manage(check_manage=True)


class ManageCIFSShareTest(ManageNFSShareTest):
    protocol = 'cifs'


class ManageGLUSTERFSShareTest(ManageNFSShareTest):
    protocol = 'glusterfs'


class ManageHDFSShareTest(ManageNFSShareTest):
    protocol = 'hdfs'


class ManageCephFSShareTest(ManageNFSShareTest):
    protocol = 'cephfs'


class ManageMapRFSShareTest(ManageNFSShareTest):
    protocol = 'maprfs'
