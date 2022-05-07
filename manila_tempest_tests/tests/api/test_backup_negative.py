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


class ShareBackupNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ShareBackupNegativeTest, cls).skip_checks()
        if not CONF.share.run_driver_assisted_backup_tests:
            raise cls.skipException("Share backup tests are disabled.")
        utils.check_skip_if_microversion_not_supported(
            _MIN_SUPPORTED_MICROVERSION)

    def setUp(self):
        super(ShareBackupNegativeTest, self).setUp()
        extra_specs = {
            'snapshot_support': True,
            'mount_snapshot_support': True,
        }
        share_type = self.create_share_type(extra_specs=extra_specs)
        share = self.create_share(self.shares_v2_client.share_protocol,
                                  share_type_id=share_type['id'])
        self.share_id = share["id"]
        self.backup_options = (
            CONF.share.driver_assisted_backup_test_driver_options)

    @decorators.idempotent_id('58c36c97-faf4-4fec-9a9b-7cff0d2035ab')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_create_backup_when_share_is_in_backup_creating_state(self):
        backup_name1 = data_utils.rand_name('Backup')
        backup1 = self.shares_v2_client.create_share_backup(
            self.share_id,
            name=backup_name1,
            backup_options=self.backup_options)['share_backup']

        # try create backup when share state is busy
        backup_name2 = data_utils.rand_name('Backup')
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_share_backup,
                          self.share_id,
                          name=backup_name2,
                          backup_options=self.backup_options)
        waiters.wait_for_resource_status(
            self.shares_v2_client, backup1['id'], "available",
            resource_name='share_backup')

        # delete the share backup
        self.shares_v2_client.delete_share_backup(backup1['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            backup_id=backup1['id'])

    @decorators.idempotent_id('58c36c97-faf4-4fec-9a9b-7cff0d2012ab')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_create_backup_when_share_is_in_error_state(self):
        self.admin_shares_v2_client.reset_state(self.share_id,
                                                status='error')

        # try create backup when share is not available
        backup_name = data_utils.rand_name('Backup')
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_share_backup,
                          self.share_id,
                          name=backup_name,
                          backup_options=self.backup_options)

        self.admin_shares_v2_client.reset_state(self.share_id,
                                                status='available')

    @decorators.idempotent_id('58c36c97-faf4-4fec-9a9b-7cff0d2012de')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_create_backup_when_share_has_snapshots(self):
        self.create_snapshot_wait_for_active(self.share_id,
                                             cleanup_in_class=False)

        # try create backup when share has snapshots
        backup_name = data_utils.rand_name('Backup')
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_share_backup,
                          self.share_id,
                          name=backup_name,
                          backup_options=self.backup_options)

    @decorators.idempotent_id('58c12c97-faf4-4fec-9a9b-7cff0d2012de')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_delete_backup_when_backup_is_not_available(self):
        backup = self.create_backup_wait_for_active(self.share_id)
        self.admin_shares_v2_client.reset_state_share_backup(
            backup['id'], status='creating')

        # try delete backup when share backup is not available
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.delete_share_backup,
                          backup['id'])

        self.admin_shares_v2_client.reset_state_share_backup(
            backup['id'], status='available')

    @decorators.idempotent_id('58c56c97-faf4-4fec-9a9b-7cff0d2012de')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_restore_backup_when_share_is_not_available(self):
        backup = self.create_backup_wait_for_active(self.share_id)
        self.admin_shares_v2_client.reset_state(self.share_id,
                                                status='error')

        # try restore backup when share is not available
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.restore_share_backup,
                          backup['id'])

        self.admin_shares_v2_client.reset_state(self.share_id,
                                                status='available')

    @decorators.idempotent_id('58c12998-faf4-4fec-9a9b-7cff0d2012de')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_BACKEND)
    def test_restore_backup_when_backup_is_not_available(self):
        backup = self.create_backup_wait_for_active(self.share_id)
        self.admin_shares_v2_client.reset_state_share_backup(
            backup['id'], status='creating')

        # try restore backup when backup is not available
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.restore_share_backup,
                          backup['id'])

        self.admin_shares_v2_client.reset_state_share_backup(
            backup['id'], status='available')
