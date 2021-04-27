# Copyright 2020 NetApp Inc.
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


from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api.admin import test_share_servers_migration
from manila_tempest_tests.tests.api import base

CONF = config.CONF


class MigrationShareServerNegative(
        test_share_servers_migration.MigrationShareServerBase):
    protocol = None

    @classmethod
    def _setup_migration(cls, cleanup_in_class=True):
        """Setup migration for negative tests."""
        extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled}
        if CONF.share.capability_snapshot_support:
            extra_specs['snapshot_support'] = True
        share_type = cls.create_share_type(
            name=data_utils.rand_name("tempest-share-type"),
            extra_specs=extra_specs,
            cleanup_in_class=cleanup_in_class)
        share = cls.create_share(share_protocol=cls.protocol,
                                 share_type_id=share_type['id'],
                                 cleanup_in_class=cleanup_in_class)
        share = cls.shares_v2_client.get_share(share['id'])['share']
        share_server_id = share['share_server_id']
        dest_host, compatible = (
            cls._choose_compatible_backend_for_share_server(share_server_id))

        return share, share_server_id, dest_host


class ShareServerMigrationInvalidParametersNFS(MigrationShareServerNegative):
    """Tests related to share server not found."""
    protocol = "nfs"

    @classmethod
    def resource_setup(cls):
        super(ShareServerMigrationInvalidParametersNFS, cls).resource_setup()
        cls.fake_server_id = 'fake_server_id'
        cls.fake_host = 'fake_host@fake_backend'

    @decorators.idempotent_id('1be6ec2a-3118-4033-9cdb-ea6d199d97f4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_server_invalid_server_migration_check(self):
        """Not found share server in migration check."""
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.share_server_migration_check,
                          self.fake_server_id,
                          self.fake_host)

    @decorators.idempotent_id('2aeffcfa-4e68-40e4-8a75-03b017503501')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_server_invalid_server_migration_cancel(self):
        """Not found share server in migration cancel."""
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.share_server_migration_cancel,
                          self.fake_server_id)

    @decorators.idempotent_id('52d23980-80e7-40de-8dba-1bb1382ef995')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_server_invalid_server_migration_start(self):
        """Not found share server in migration start."""
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.share_server_migration_start,
                          self.fake_server_id,
                          self.fake_host)

    @decorators.idempotent_id('47795631-eb50-424b-9fac-d2ee832cd01c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_server_invalid_server_migration_get_progress(self):
        """Not found share server in migration get progress."""
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.share_server_migration_get_progress,
            self.fake_server_id)

    @decorators.idempotent_id('3b464298-a4e4-417b-92d6-acfbd30ac45b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_share_server_invalid_server_migration_complete(self):
        """Not found share server in migration complete."""
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.share_server_migration_complete,
            self.fake_server_id)

    @decorators.idempotent_id('2d25cf84-0b5c-4a9f-ae20-9bec09bb6914')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_host_migration_start(self):
        """Invalid host in migration start."""
        share = self.create_share(
            share_protocol=self.protocol,
            share_type_id=self.share_type['id'])
        share = self.shares_v2_client.get_share(share['id'])['share']
        share_server_id = share['share_server_id']
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.share_server_migration_start,
                          share_server_id,
                          self.fake_host)

    @decorators.idempotent_id('e7e2c19c-a0ed-41ab-b666-b2beae4a690c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_host_migration_check(self):
        """Invalid host in migration check."""
        share = self.create_share(
            share_protocol=self.protocol,
            share_type_id=self.share_type['id'])
        share = self.shares_v2_client.get_share(share['id'])['share']
        share_server_id = share['share_server_id']
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.share_server_migration_check,
                          share_server_id,
                          self.fake_host)

    @decorators.idempotent_id('f0d7a055-3b46-4d2b-9b96-1d719bd323e8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_share_network_migration_start(self):
        """Invalid host in migration start."""
        share = self.create_share(
            share_protocol=self.protocol,
            share_type_id=self.share_type['id'])
        share = self.shares_v2_client.get_share(share['id'])['share']
        share_server_id = share['share_server_id']
        dest_host, _ = self._choose_compatible_backend_for_share_server(
            share_server_id)
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.share_server_migration_start,
                          share_server_id,
                          dest_host,
                          new_share_network_id='fake_share_net_id')

    @decorators.idempotent_id('2617e714-7a8e-49a4-8109-beab3ea6527f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_share_network_migration_check(self):
        """Invalid host in migration check."""
        share = self.create_share(
            share_protocol=self.protocol,
            share_type_id=self.share_type['id'])
        share = self.shares_v2_client.get_share(share['id'])['share']
        share_server_id = share['share_server_id']
        dest_host, _ = self._choose_compatible_backend_for_share_server(
            share_server_id)
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.share_server_migration_check,
                          share_server_id,
                          self.fake_host,
                          new_share_network_id='fake_share_net_id')


class ShareServerErrorStatusOperationNFS(MigrationShareServerNegative):
    protocol = "nfs"

    @classmethod
    def resource_setup(cls):
        super(ShareServerErrorStatusOperationNFS, cls).resource_setup()
        cls.share = cls.create_share(
            share_protocol=cls.protocol,
            share_type_id=cls.share_type['id'])
        cls.share = cls.shares_v2_client.get_share(cls.share['id'])['share']
        cls.share_server_id = cls.share['share_server_id']
        cls.dest_host, _ = cls._choose_compatible_backend_for_share_server(
            cls.share_server_id)
        cls.shares_v2_client.share_server_reset_state(
            cls.share_server_id, status=constants.STATUS_ERROR)

    @decorators.idempotent_id('1f8d75c1-aa3c-465a-b2dd-9ad33933944f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_operation_migration_check(self):
        """Share server migration check invalid operation."""
        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.share_server_migration_check,
                          self.share_server_id,
                          self.dest_host)

    @decorators.idempotent_id('c256c5f5-b4d1-47b7-a1f4-af21f19ce600')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_operation_migration_start(self):
        """Share server migration start invalid operation."""
        self.assertRaises(lib_exc.Conflict,
                          self.shares_v2_client.share_server_migration_start,
                          self.share_server_id,
                          self.dest_host)

    @decorators.idempotent_id('d2830fe4-8d13-40d2-b987-18d414bb6196')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_operation_migration_get_progress(self):
        """Share server migration get progress invalid operation."""
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.share_server_migration_get_progress,
            self.share_server_id)

    @decorators.idempotent_id('245f39d7-bcbc-4711-afd7-651a5535a880')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_operation_migration_cancel(self):
        """Share server migration cancel invalid operation."""
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.share_server_migration_cancel,
                          self.share_server_id)

    @decorators.idempotent_id('3db45440-2c70-4fa4-b5eb-75e3cb0204f8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_invalid_operation_migration_complete(self):
        """Share server migration complete invalid operation."""
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.share_server_migration_complete,
            self.share_server_id)


class ShareServerMigrationStartNegativesNFS(MigrationShareServerNegative):
    protocol = "nfs"

    @classmethod
    def resource_setup(cls):
        super(ShareServerMigrationStartNegativesNFS, cls).resource_setup()
        cls.share, cls.server_id, cls.dest_host = cls._setup_migration()
        cls.shares_v2_client.share_server_migration_start(
            cls.server_id, cls.dest_host)

    @classmethod
    def resource_cleanup(cls):
        states = [constants.TASK_STATE_MIGRATION_DRIVER_IN_PROGRESS,
                  constants.TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE]
        waiters.wait_for_resource_status(
            cls.shares_v2_client, cls.server_id, states,
            resource_name="share_server",
            status_attr="task_state")
        cls.shares_v2_client.share_server_migration_cancel(cls.server_id)
        waiters.wait_for_resource_status(
            cls.shares_v2_client, cls.share['id'], status="available")
        super(ShareServerMigrationStartNegativesNFS, cls).resource_cleanup()

    @decorators.idempotent_id('5b904db3-fc36-4c35-a8ef-cf6b80315388')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_migration_start_try_create_snapshot(self):
        """Try create snap during a server migration."""
        if not CONF.share.capability_snapshot_support:
            raise self.skipException(
                'Snapshot tests are disabled or unsupported.')
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_snapshot,
            self.share['id']
        )

    @decorators.idempotent_id('93882b54-78d4-4c4e-95b5-993de0cdb25d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_migration_start_try_create_access_rule(self):
        """Try create access rule during a server migration."""
        self.assertRaises(
            lib_exc.BadRequest,
            self.shares_v2_client.create_access_rule,
            self.share['id']
        )

    @decorators.idempotent_id('7c74a4a8-61b2-4c55-bc4b-02eac73d2c6e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_migration_start_try_delete_share_network(self):
        """Try delete share network during a server migration."""
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.delete_share_network,
            self.share['share_network_id']
        )


class ShareServerMigrationStartInvalidStatesNFS(MigrationShareServerNegative):
    protocol = "nfs"

    @decorators.idempotent_id('bcec0503-b2a9-4514-bf3f-a30d55f41e78')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_migration_start_invalid_network(self):
        """Try server migration start with invalid network."""
        share, share_server_id, dest_host = self._setup_migration(
            cleanup_in_class=False)
        azs = self.get_availability_zones()
        if len(azs) < 2:
            raise self.skipException(
                "Could not find the necessary azs. At least two azs are "
                "needed to run this test.")

        # In this test we'll attempt to start a migration to a share
        # network that isn't available in the destination back ends's
        # availability zone.
        dest_host_az = self.get_availability_zones(backends=[dest_host])

        if dest_host_az[0] != share['availability_zone']:
            share_network_az = share['availability_zone']
        else:
            for az in azs:
                if az != dest_host_az:
                    share_network_az = az
                    break

        share_network = self.create_share_network(
            client=self.shares_v2_client, cleanup_in_class=False,
            availability_zone=share_network_az)
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.share_server_migration_start,
            share_server_id,
            dest_host,
            new_share_network_id=share_network['id'])

    @decorators.idempotent_id('11374277-efcf-4992-ad94-c8f4a393d41b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_migration_start_invalid_share_state(self):
        """Try server migration start with invalid share state."""
        share, share_server_id, dest_host = self._setup_migration(
            cleanup_in_class=False)
        self.shares_v2_client.reset_state(share['id'], status='error')

        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.share_server_migration_start,
            share_server_id,
            dest_host
        )

    @decorators.idempotent_id('ebe8da5b-ee9c-48c7-a7e4-9e71839f813f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_share_server_migration_start_with_share_replica(self):
        """Try server migration start with share replica."""
        if not CONF.share.backend_replication_type or (
                not CONF.share.run_replication_tests):
            raise self.skipException(
                'Share replica tests are disabled or unsupported.')
        extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
            'replication_type': CONF.share.backend_replication_type
        }
        share_type = self.shares_v2_client.create_share_type(
            name=data_utils.rand_name("tempest-share-type"),
            extra_specs=extra_specs,
            cleanup_in_class=False)
        share = self.create_share(share_type_id=share_type['share_type']['id'],
                                  share_protocol=self.protocol,
                                  cleanup_in_class=False)
        share = self.shares_v2_client.get_share(share['id'])['share']
        share_server_id = share['share_server_id']
        dest_host, _ = self._choose_compatible_backend_for_share_server(
            share_server_id)
        self.create_share_replica(
            share['id'],
            cleanup_in_class=False)
        self.assertRaises(
            lib_exc.Conflict,
            self.shares_v2_client.share_server_migration_start,
            share_server_id,
            dest_host
        )


class ShareServerMigrationInvalidParametersCIFS(
    ShareServerMigrationInvalidParametersNFS):
    protocol = "cifs"


class ShareServerErrorStatusOperationCIFS(ShareServerErrorStatusOperationNFS):
    protocol = "cifs"


class ShareServerMigrationStartNegativesCIFS(
        ShareServerMigrationStartNegativesNFS):
    protocol = "cifs"


class ShareServerMigrationInvalidStatesCIFS(
        ShareServerMigrationStartInvalidStatesNFS):
    protocol = "cifs"
