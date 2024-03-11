# Copyright 2024 Cloudification GmbH
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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF
_MIN_SUPPORTED_MICROVERSION = '2.80'


class ShareBackupTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareBackupTest, cls).skip_checks()
        if not CONF.share.run_driver_assisted_backup_tests:
            raise cls.skipException("Share backup tests are disabled.")
        utils.check_skip_if_microversion_not_supported(
            _MIN_SUPPORTED_MICROVERSION)

    def setUp(self):
        super(ShareBackupTest, self).setUp()
        extra_specs = {
            'snapshot_support': True,
            'mount_snapshot_support': True,
        }
        share_type = self.create_share_type(extra_specs=extra_specs)
        share = self.create_share(self.shares_v2_client.share_protocol,
                                  share_type_id=share_type['id'])
        self.share_id = share["id"]

    @decorators.idempotent_id('12c36c97-faf4-4fec-9a9b-7cff0d2035cd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_share_backup(self):
        backup = self.create_backup_wait_for_active(self.share_id)

        # Verify backup create API response, we use the configured max API
        # version to make this call
        expected_keys = ["id", "share_id", "status",
                         "availability_zone", "created_at", "updated_at",
                         "size", "progress", "restore_progress",
                         "name", "description"]
        if utils.is_microversion_ge(CONF.share.max_api_microversion, '2.85'):
            expected_keys.append("backup_type")

        # Strict key check
        actual_backup = self.shares_v2_client.get_share_backup(
            backup['id'])['share_backup']
        actual_keys = actual_backup.keys()
        self.assertEqual(backup['id'], actual_backup['id'])
        self.assertEqual(set(expected_keys), set(actual_keys))

    @decorators.idempotent_id('34c36c97-faf4-4fec-9a9b-7cff0d2035cd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_delete_share_backup(self):
        backup = self.create_backup_wait_for_active(
            self.share_id, cleanup=False)

        # Delete share backup
        self.shares_v2_client.delete_share_backup(backup['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            backup_id=backup['id'])
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.get_share_backup,
            backup['id'])

    @decorators.idempotent_id('56c36c97-faf4-4fec-9a9b-7cff0d2035cd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_restore_share_backup(self):
        backup = self.create_backup_wait_for_active(self.share_id)

        # Restore share backup
        restore = self.shares_v2_client.restore_share_backup(
            backup['id'])['restore']
        waiters.wait_for_resource_status(
            self.shares_v2_client, backup['id'], 'available',
            resource_name='share_backup')

        self.assertEqual(restore['share_id'], self.share_id)

    @decorators.idempotent_id('78c36c97-faf4-4fec-9a9b-7cff0d2035cd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_update_share_backup(self):
        backup = self.create_backup_wait_for_active(self.share_id)

        # Update share backup name
        backup_name2 = data_utils.rand_name('Backup')
        backup = self.shares_v2_client.update_share_backup(
            backup['id'], name=backup_name2)['share_backup']
        updated_backup = self.shares_v2_client.get_share_backup(
            backup['id'])['share_backup']
        self.assertEqual(backup_name2, updated_backup['name'])

    @decorators.idempotent_id('19c36c97-faf4-4fec-9a9b-7cff0d2045af')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_list_share_backups(self):
        self.create_backup_wait_for_active(self.share_id)
        backups = self.shares_v2_client.list_share_backups()
        self.assertEqual(1, len(backups))
