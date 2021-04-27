# Copyright 2015 Hitachi Data Systems.
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
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests import share_exceptions
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class MigrationNegativeTest(base.BaseSharesAdminTest):
    """Tests Share Migration.

    Tests share migration in multi-backend environment.
    """

    protocol = "nfs"

    @classmethod
    def resource_setup(cls):
        super(MigrationNegativeTest, cls).resource_setup()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled." % cls.protocol
            raise cls.skipException(message)
        if not (CONF.share.run_host_assisted_migration_tests or
                CONF.share.run_driver_assisted_migration_tests):
            raise cls.skipException("Share migration tests are disabled.")

        pools = cls.shares_client.list_pools(detail=True)['pools']

        if len(pools) < 2:
            raise cls.skipException("At least two different pool entries "
                                    "are needed to run share migration tests.")

        # create share type (generic)
        extra_specs = {}

        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(cls.protocol,
                                     size=CONF.share.share_size + 1,
                                     share_type_id=cls.share_type_id)
        cls.share = cls.shares_client.get_share(cls.share['id'])['share']

        dest_pool = utils.choose_matching_backend(
            cls.share, pools, cls.share_type)

        if not dest_pool or dest_pool.get('name') is None:
            raise share_exceptions.ShareMigrationException(
                "No valid pool entries to run share migration tests.")

        cls.dest_pool = dest_pool['name']

        cls.new_type_invalid = cls.create_share_type(
            name=data_utils.rand_name(
                'new_invalid_share_type_for_migration'),
            cleanup_in_class=True,
            extra_specs=utils.get_configured_extra_specs(variation='invalid'))

    @decorators.idempotent_id('8aa1f2a0-bc44-4df5-a556-161590e594a3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_migration_cancel_invalid(self):
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migration_cancel,
            self.share['id'])

    @decorators.idempotent_id('6d0dfb2e-51a0-4cb7-8c69-6135a49c6057')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_migration_get_progress_None(self):
        self.shares_v2_client.reset_task_state(self.share["id"], None)
        waiters.wait_for_resource_status(
            self.shares_v2_client, self.share["id"], None,
            status_attr='task_state')
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migration_get_progress,
            self.share['id'])

    @decorators.idempotent_id('2ab1fc82-bc13-4c99-8324-c6b23530e8a4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_migration_complete_invalid(self):
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migration_complete,
            self.share['id'])

    @decorators.idempotent_id('8ef562b4-7704-4a78-973f-9bf8d2b6f6a6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_migration_cancel_not_found(self):
        self.assertRaises(
            lib_exc.NotFound, self.shares_v2_client.migration_cancel,
            'invalid_share_id')

    @decorators.idempotent_id('044c792b-63e0-42c3-9f44-dc2280e2af08')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_migration_get_progress_not_found(self):
        self.assertRaises(
            lib_exc.NotFound, self.shares_v2_client.migration_get_progress,
            'invalid_share_id')

    @decorators.idempotent_id('a509871a-3f3a-4618-bb60-9661732dd371')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.22")
    def test_migration_complete_not_found(self):
        self.assertRaises(
            lib_exc.NotFound, self.shares_v2_client.migration_complete,
            'invalid_share_id')

    @decorators.idempotent_id('6276bea6-6939-4569-930f-218d99c0fa56')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_migrate_share_with_snapshot(self):
        snap = self.create_snapshot_wait_for_active(self.share['id'])
        self.assertRaises(
            lib_exc.Conflict, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool,
            force_host_assisted_migration=True)
        self.shares_v2_client.delete_snapshot(snap['id'])
        self.shares_v2_client.wait_for_resource_deletion(snapshot_id=snap[
            "id"])

    @decorators.idempotent_id('78670c24-c4ee-45b5-b166-2d053c333144')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    @ddt.data(True, False)
    def test_migrate_share_same_host(self, specified):
        new_share_type_id = None
        new_share_network_id = None
        if specified:
            new_share_type_id = self.share_type_id
            new_share_network_id = self.share['share_network_id']
        self.migrate_share(
            self.share['id'], self.share['host'],
            wait_for_status=constants.TASK_STATE_MIGRATION_SUCCESS,
            new_share_type_id=new_share_type_id,
            new_share_network_id=new_share_network_id)
        # NOTE(ganso): No need to assert, it is already waiting for correct
        # status (migration_success).

    @decorators.idempotent_id('af17204f-ffab-4ba8-8cb6-032e49216f67')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_host_invalid(self):
        self.assertRaises(
            lib_exc.NotFound, self.shares_v2_client.migrate_share,
            self.share['id'], 'invalid_host')

    @decorators.idempotent_id('0558e9c4-0416-41d2-b28a-803d4b81521a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    @ddt.data({'writable': False, 'preserve_metadata': False,
               'preserve_snapshots': False, 'nondisruptive': True},
              {'writable': False, 'preserve_metadata': False,
               'preserve_snapshots': True, 'nondisruptive': False},
              {'writable': False, 'preserve_metadata': True,
               'preserve_snapshots': False, 'nondisruptive': False},
              {'writable': True, 'preserve_metadata': False,
               'preserve_snapshots': False, 'nondisruptive': False})
    @ddt.unpack
    def test_migrate_share_host_assisted_not_allowed_API(
            self, writable, preserve_metadata, preserve_snapshots,
            nondisruptive):
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool,
            force_host_assisted_migration=True, writable=writable,
            preserve_metadata=preserve_metadata, nondisruptive=nondisruptive,
            preserve_snapshots=preserve_snapshots)

    @decorators.idempotent_id('ee57024c-d00e-4def-8eec-cbc62bae327f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_change_type_no_valid_host(self):
        if not CONF.share.multitenancy_enabled:
            new_share_network_id = self.create_share_network(
                neutron_net_id='fake_net_id',
                neutron_subnet_id='fake_subnet_id')['id']
        else:
            new_share_network_id = None

        self.shares_v2_client.migrate_share(
            self.share['id'], self.dest_pool,
            new_share_type_id=self.new_type_invalid['id'],
            new_share_network_id=new_share_network_id)
        waiters.wait_for_migration_status(
            self.shares_v2_client, self.share['id'], self.dest_pool,
            constants.TASK_STATE_MIGRATION_ERROR)

    @decorators.idempotent_id('e2bd0cca-c091-4785-a9dc-7f42d2bb95a5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_not_found(self):
        self.assertRaises(
            lib_exc.NotFound, self.shares_v2_client.migrate_share,
            'invalid_share_id', self.dest_pool)

    @decorators.idempotent_id('86b427a7-27c0-4cd5-8f52-9688b339980b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_not_available(self):
        self.shares_client.reset_state(self.share['id'],
                                       constants.STATUS_ERROR)
        waiters.wait_for_resource_status(
            self.shares_v2_client, self.share['id'], constants.STATUS_ERROR)
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool)
        self.shares_client.reset_state(self.share['id'],
                                       constants.STATUS_AVAILABLE)
        waiters.wait_for_resource_status(
            self.shares_v2_client, self.share['id'],
            constants.STATUS_AVAILABLE)

    @decorators.idempotent_id('e8f1e491-697a-4941-bf51-4d37f0a93fa5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_invalid_share_network(self):
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool,
            new_share_network_id='invalid_net_id')

    @decorators.idempotent_id('be262d44-2ca2-4b9c-be3a-5a6a98ed871b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_invalid_share_type(self):
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool,
            new_share_type_id='invalid_type_id')

    @decorators.idempotent_id('16c72693-6f9e-4cb4-a166-c60accd3479b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_migrate_share_opposite_type_share_network_invalid(self):

        extra_specs = utils.get_configured_extra_specs(
            variation='opposite_driver_modes')

        new_type_opposite = self.create_share_type(
            name=data_utils.rand_name('share_type_migration_negative'),
            extra_specs=extra_specs)

        new_share_network_id = None

        if CONF.share.multitenancy_enabled:

            new_share_network_id = self.create_share_network(
                neutron_net_id='fake_net_id',
                neutron_subnet_id='fake_subnet_id')['id']

        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool,
            new_share_type_id=new_type_opposite['id'],
            new_share_network_id=new_share_network_id)

    @decorators.idempotent_id('1f529b09-e404-4f0e-9423-bb4b117b5522')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.48")
    def test_share_type_azs_share_migrate_unsupported_az(self):
        extra_specs = self.add_extra_specs_to_dict({
            'availability_zones': 'non-existent az'})
        new_share_type = self.create_share_type(
            name=data_utils.rand_name('share_type_specific_az'),
            extra_specs=extra_specs, cleanup_in_class=False)
        self.assertRaises(
            lib_exc.BadRequest, self.shares_v2_client.migrate_share,
            self.share['id'], self.dest_pool,
            new_share_type_id=new_share_type['id'])

    @decorators.idempotent_id('90cf0ae4-4251-4142-bfa8-41f67a9e5b23')
    @testtools.skipUnless(CONF.share.run_driver_assisted_migration_tests,
                          "Driver-assisted migration tests are disabled.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_create_snapshot_during_share_migration(self):
        self._test_share_actions_during_share_migration('create_snapshot', [])

    @decorators.idempotent_id('20121039-bb11-45d8-9972-d2daff7a779c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    @ddt.data(('extend_share', [CONF.share.share_size + 2]),
              ('shrink_share', [CONF.share.share_size]))
    @ddt.unpack
    def test_share_resize_during_share_migration(self, method_name, *args):
        self._test_share_actions_during_share_migration(method_name, *args)

    def skip_if_tests_are_disabled(self, method_name):
        property_to_evaluate = {
            'extend_share': CONF.share.run_extend_tests,
            'shrink_share': CONF.share.run_shrink_tests,
            'create_snapshot': CONF.share.run_snapshot_tests,
        }
        if not property_to_evaluate[method_name]:
            raise self.skipException(method_name + 'tests are disabled.')

    @decorators.idempotent_id('6e83fc25-4e3e-49a7-93e8-db4e6b355a91')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @utils.skip_if_microversion_not_supported("2.29")
    def test_add_access_rule_during_migration(self):
        access_type = "ip"
        access_to = "50.50.50.50"
        self.shares_v2_client.reset_state(self.share['id'],
                                          constants.STATUS_MIGRATING)
        self.shares_v2_client.reset_task_state(
            self.share['id'],
            constants.TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE)
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_access_rule,
            self.share['id'], access_type, access_to)
        # Revert the migration state by cancelling the migration
        self.shares_v2_client.reset_state(self.share['id'],
                                          constants.STATUS_AVAILABLE)
        self.shares_v2_client.reset_task_state(
            self.share['id'],
            constants.TASK_STATE_MIGRATION_CANCELLED)

    def _test_share_actions_during_share_migration(self, method_name, *args):
        self.skip_if_tests_are_disabled(method_name)
        # Verify various share operations during share migration
        self.shares_v2_client.reset_state(self.share['id'],
                                          constants.STATUS_MIGRATING)
        self.shares_v2_client.reset_task_state(
            self.share['id'],
            constants.TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE)

        self.assertRaises(
            lib_exc.BadRequest, getattr(self.shares_v2_client, method_name),
            self.share['id'], *args)
        # Revert the migration state by cancelling the migration
        self.shares_v2_client.reset_state(self.share['id'],
                                          constants.STATUS_AVAILABLE)
        self.shares_v2_client.reset_task_state(
            self.share['id'],
            constants.TASK_STATE_MIGRATION_CANCELLED)
