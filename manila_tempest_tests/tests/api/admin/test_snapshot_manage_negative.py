# Copyright 2015 EMC Corporation.
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

import six
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class ManageNFSSnapshotNegativeTest(base.BaseSharesAdminTest):
    protocol = 'nfs'

    @classmethod
    @base.skip_if_microversion_lt("2.12")
    @testtools.skipUnless(
        CONF.share.run_manage_unmanage_snapshot_tests,
        "Manage/unmanage snapshot tests are disabled.")
    def resource_setup(cls):
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

        utils.skip_if_manage_not_supported_for_version()

        super(ManageNFSSnapshotNegativeTest, cls).resource_setup()

        # Create share type
        cls.st_name = data_utils.rand_name("tempest-manage-st-name")
        cls.extra_specs = {
            'storage_protocol': CONF.share.capability_storage_protocol,
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
            'snapshot_support': six.text_type(
                CONF.share.capability_snapshot_support),
        }

        cls.st = cls.create_share_type(
            name=cls.st_name,
            cleanup_in_class=True,
            extra_specs=cls.extra_specs)

        # Create share
        cls.share = cls.create_share(
            share_type_id=cls.st['share_type']['id'],
            share_protocol=cls.protocol
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_not_found(self):
        # Manage non-existing snapshot fails
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.manage_snapshot,
            'fake-share-id',
            'fake-provider-location',
        )

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_already_exists(self):
        # Manage already existing snapshot fails

        # Create snapshot
        snap = self.create_snapshot_wait_for_active(self.share['id'])
        snap = self.shares_v2_client.get_snapshot(snap['id'])
        self.assertEqual(self.share['id'], snap['share_id'])
        self.assertIsNotNone(snap['provider_location'])

        # Manage snapshot fails
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.manage_snapshot,
            self.share['id'],
            snap['provider_location']
        )

        # Delete snapshot
        self._delete_snapshot_and_wait(snap)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_manage_invalid_provider_location(self):
        # Manage a snapshot with wrong provider location fails

        # Create snapshot
        snap = self.create_snapshot_wait_for_active(self.share['id'])
        snap = self.shares_v2_client.get_snapshot(snap['id'])

        # Unmanage snapshot
        self.shares_v2_client.unmanage_snapshot(snap['id'])
        self.shares_client.wait_for_resource_deletion(
            snapshot_id=snap['id']
        )

        # Manage snapshot with invalid provider location leaves it in
        # manage_error state
        invalid_snap = self.shares_v2_client.manage_snapshot(
            self.share['id'],
            'invalid_provider_location',
            driver_options={}
        )
        self.shares_v2_client.wait_for_snapshot_status(
            invalid_snap['id'],
            constants.STATUS_MANAGE_ERROR
        )
        self.shares_v2_client.unmanage_snapshot(invalid_snap['id'])

        # Manage it properly and delete
        managed_snap = self.shares_v2_client.manage_snapshot(
            self.share['id'],
            snap['provider_location']
        )
        self.shares_v2_client.wait_for_snapshot_status(
            managed_snap['id'],
            constants.STATUS_AVAILABLE
        )
        self._delete_snapshot_and_wait(managed_snap)

    @testtools.skipUnless(CONF.share.multitenancy_enabled,
                          'Multitenancy tests are disabled.')
    @utils.skip_if_microversion_not_supported("2.48")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_unmanage_snapshot_with_server_unsupported(self):
        share = self._create_share_for_manage()
        snap = self.create_snapshot_wait_for_active(share["id"])

        self.assertRaises(
            lib_exc.Forbidden,
            self.shares_v2_client.unmanage_snapshot,
            snap['id'], version="2.48")

        self._delete_snapshot_and_wait(snap)
        self._delete_share_and_wait(share)


class ManageCIFSSnapshotNegativeTest(ManageNFSSnapshotNegativeTest):
    protocol = 'cifs'


class ManageGLUSTERFSSnapshotNegativeTest(ManageNFSSnapshotNegativeTest):
    protocol = 'glusterfs'


class ManageHDFSSnapshotNegativeTest(ManageNFSSnapshotNegativeTest):
    protocol = 'hdfs'


class ManageMapRFSSnapshotNegativeTest(ManageNFSSnapshotNegativeTest):
    protocol = 'maprfs'
