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

import ddt
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class MigrationShareServerBase(base.BaseSharesAdminTest):
    protocol = None

    @classmethod
    def skip_checks(cls):
        super(MigrationShareServerBase, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            raise cls.skipException('%s tests are disabled.' % cls.protocol)
        if not CONF.share.multitenancy_enabled:
            raise cls.skipException('Multitenancy tests are disabled.')
        if not CONF.share.run_share_server_migration_tests:
            raise cls.skipException(
                'Share server migration tests are disabled.')
        utils.check_skip_if_microversion_not_supported('2.57')

    @classmethod
    def resource_setup(cls):
        super(MigrationShareServerBase, cls).resource_setup()
        cls.all_hosts = cls.shares_v2_client.list_pools(detail=True)
        cls.backends = set()
        for pool in cls.all_hosts['pools']:
            if pool['capabilities'].get('driver_handles_share_servers'):
                cls.backends.add(pool['name'].split('#')[0])

        if len(cls.backends) < 2:
            msg = ("Could not find the necessary backends. At least two"
                   " are needed to run the tests of share server migration")
            raise cls.skipException(msg)

        # create share type (generic)
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)

        # create two non routable IPs to be used in NFS access rulesi
        cls.access_rules_ip_rw = utils.rand_ip()
        cls.access_rules_ip_ro = utils.rand_ip()

    def _setup_migration(self, share):
        """Initial share server migration setup."""

        share = self.shares_v2_client.get_share(share['id'])['share']
        server_id = share['share_server_id']

        # (andrer) Verify if have at least one backend compatible with
        # the specified share server.
        dest_host, compatible = (
            self._choose_compatible_backend_for_share_server(server_id))

        snapshot = False
        if (compatible['supported_capabilities']['preserve_snapshots'] and
                share['snapshot_support']):
            snapshot = self.create_snapshot_wait_for_active(
                share['id'], cleanup_in_class=False)['id']

        # (andrer) Check the share export locations.
        old_exports = self.shares_v2_client.list_share_export_locations(
            share['id'])['export_locations']
        self.assertNotEmpty(old_exports)
        old_exports = [x['path'] for x in old_exports
                       if x['is_admin_only'] is False]
        self.assertNotEmpty(old_exports)

        # (andrer) Create the access rules, considering NFS and CIFS
        # protocols.
        access_rules = self._get_access_rule_data_for_protocols()
        for rule in access_rules:
            self.shares_v2_client.create_access_rule(
                share['id'], access_type=rule.get('access_type'),
                access_to=rule.get('access_to'),
                access_level=rule.get('access_level')
            )
        waiters.wait_for_resource_status(
            self.shares_v2_client, share['id'], constants.RULE_STATE_ACTIVE,
            status_attr='access_rules_status')

        share = self.shares_v2_client.get_share(share['id'])['share']

        return share, server_id, dest_host, snapshot

    def _validate_state_of_resources(self, share, expected_status,
                                     snapshot_id):
        """Validates the share and snapshot status."""
        statuses = ((expected_status,)
                    if not isinstance(expected_status, (tuple, list, set))
                    else expected_status)

        share = self.shares_v2_client.get_share(share['id'])['share']
        self.assertIn(share['status'], statuses)

        if snapshot_id:
            snapshot = self.shares_v2_client.get_snapshot(
                snapshot_id)['snapshot']
            self.assertIn(snapshot['status'], statuses)

    def _validate_share_server_migration_complete(
        self, share, dest_host, dest_server_id, snapshot_id=None,
        share_network_id=None, version=CONF.share.max_api_microversion):
        """Validates the share server migration complete. """

        # Check the export locations
        new_exports = self.shares_v2_client.list_share_export_locations(
            share['id'], version=version)['export_locations']
        self.assertNotEmpty(new_exports)
        new_exports = [x['path'] for x in new_exports if
                       x['is_admin_only'] is False]
        self.assertNotEmpty(new_exports)

        # Check the share host, share_network, share_server and status.
        share = self.shares_v2_client.get_share(share['id'])['share']
        self.assertEqual(share['host'].split('#')[0], dest_host)
        self.assertEqual(share_network_id, share['share_network_id'])
        self.assertEqual(dest_server_id, share['share_server_id'])
        self.assertEqual(share['status'], constants.STATUS_AVAILABLE)

        # Check the snapshot status if possible.
        if snapshot_id:
            waiters.wait_for_resource_status(
                self.shares_v2_client, snapshot_id, constants.STATUS_AVAILABLE,
                resource_name='snapshot'
            )

        # Check the share server destination status.
        dest_server = self.shares_v2_client.show_share_server(
            dest_server_id)['share_server']
        self.assertIn(dest_server['task_state'],
                      constants.TASK_STATE_MIGRATION_SUCCESS)

        # Check if the access rules are in the share.
        rules = self.shares_v2_client.list_access_rules(
            share['id'])['access_list']
        if self.protocol == 'cifs':
            expected_rules = [{
                'state': constants.RULE_STATE_ACTIVE,
                'access_to': CONF.share.username_for_user_rules,
                'access_type': 'user',
                'access_level': 'rw',
            }]
        elif self.protocol == 'nfs':
            expected_rules = [{
                'state': constants.RULE_STATE_ACTIVE,
                'access_to': self.access_rules_ip_rw,
                'access_type': 'ip',
                'access_level': 'rw',
            }, {
                'state': constants.RULE_STATE_ACTIVE,
                'access_to': self.access_rules_ip_ro,
                'access_type': 'ip',
                'access_level': 'ro',
            }]

        filtered_rules = [{'state': rule['state'],
                           'access_to': rule['access_to'],
                           'access_level': rule['access_level'],
                           'access_type': rule['access_type']}
                          for rule in rules]

        for r in expected_rules:
            self.assertIn(r, filtered_rules)
        self.assertEqual(len(expected_rules), len(filtered_rules))

    @classmethod
    def _choose_compatible_backend_for_share_server(self, server_id):
        """Choose a compatible host for the share server migration."""
        for backend in self.backends:
            # This try is necessary since if you try migrate the share server
            # using the same backend and share network will raise an exception.
            try:
                compatibility = (
                    self.admin_shares_v2_client.share_server_migration_check(
                        share_server_id=server_id, host=backend))
            except exceptions.Conflict or exceptions.ServerFault:
                continue
            if compatibility['compatible']:
                return backend, compatibility

        raise self.skipException(
            "Not found compatible host for the share server migration.")

    def _choose_incompatible_backend_for_share_server(self, server_id):
        """Choose a not compatible host for the share server migration."""
        for backend in self.backends:
            # This try is necessary since if you try migrate the share server
            # using the same backend and share network will raise an exception.
            try:
                compatibility = (
                    self.admin_shares_v2_client.share_server_migration_check(
                        share_server_id=server_id, host=backend))
            except exceptions.Conflict or exceptions.ServerFault:
                continue
            if not compatibility['compatible']:
                return backend, compatibility

        raise self.skipException(
            "None of the hosts available are incompatible to perform a"
            " negative share server migration test.")

    def _get_share_server_destination_for_migration(self, src_server_id):
        """Find the destination share server chosen for the migration."""
        params = {'source_share_server_id': src_server_id,
                  'status': constants.STATUS_SERVER_MIGRATING_TO}
        dest_server = self.admin_shares_v2_client.list_share_servers(
            search_opts=params)['share_servers']
        dest_server_id = dest_server[0]['id'] if dest_server else None

        return dest_server_id

    def _get_access_rule_data_for_protocols(self):
        """Return fake data for access rules based on configured protocol."""
        if self.protocol == 'nfs':
            return [{
                'access_type': 'ip',
                'access_to': self.access_rules_ip_rw,
                'access_level': 'rw',
            }, {
                'access_type': 'ip',
                'access_to': self.access_rules_ip_ro,
                'access_level': 'ro',
            }]
        elif self.protocol == 'cifs':
            return [{
                'access_type': 'user',
                'access_to': CONF.share.username_for_user_rules,
                'access_level': 'rw',
            }]
        else:
            message = "Unrecognized protocol and access rules configuration"
            raise self.skipException(message)


@ddt.ddt
class ShareServerMigrationBasicNFS(MigrationShareServerBase):
    protocol = "nfs"

    @decorators.idempotent_id('5b84bcb6-17d8-4073-8e02-53b54aee6f8b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_share_server_migration_cancel(self):
        """Test the share server migration cancel."""
        share_network_id = self.provide_share_network(
            self.shares_v2_client, self.networks_client)
        share = self.create_share(share_protocol=self.protocol,
                                  share_type_id=self.share_type['id'],
                                  share_network_id=share_network_id,
                                  cleanup_in_class=False)
        share = self.shares_v2_client.get_share(share['id'])['share']

        # Initial migration setup.
        share, src_server_id, dest_host, snapshot_id = self._setup_migration(
            share)

        preserve_snapshots = True if snapshot_id else False

        # Start share server migration.
        self.shares_v2_client.share_server_migration_start(
            src_server_id, dest_host, preserve_snapshots=preserve_snapshots)

        expected_state = constants.TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE
        waiters.wait_for_resource_status(
            self.shares_v2_client, src_server_id,
            expected_state, resource_name='share_server',
            status_attr='task_state'
        )

        # Get for the destination share server.
        dest_server_id = self._get_share_server_destination_for_migration(
            src_server_id)

        dest_server = self.shares_v2_client.show_share_server(
            dest_server_id)['share_server']
        self.assertEqual(dest_host, dest_server['host'])
        self.assertEqual(share_network_id, dest_server['share_network_id'])

        # Validate the share instances status.
        share_status = constants.STATUS_SERVER_MIGRATING
        self._validate_state_of_resources(share, share_status, snapshot_id)

        # Cancel the share server migration.
        self.shares_v2_client.share_server_migration_cancel(src_server_id)

        # Wait for the migration cancelled status.
        expected_state = constants.TASK_STATE_MIGRATION_CANCELLED
        waiters.wait_for_resource_status(
            self.shares_v2_client, src_server_id,
            expected_state, resource_name='share_server',
            status_attr='task_state')

        # After the cancel operation, we need to validate again the resources.
        expected_status = constants.STATUS_AVAILABLE
        self._validate_state_of_resources(share, expected_status, snapshot_id)

    @decorators.idempotent_id('99e439a8-a716-4205-bf5b-af50128cb908')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(False, True)
    def test_share_server_migration_complete(self, new_share_network):
        """Test the share server migration complete."""
        share_network_id = self.provide_share_network(
            self.shares_v2_client, self.networks_client)
        dest_share_network_id = share_network_id
        if new_share_network:
            src_share_network = self.shares_v2_client.get_share_network(
                share_network_id)['share_network']
            share_net_info = (
                utils.share_network_get_default_subnet(src_share_network))
            dest_share_network_id = self.create_share_network(
                neutron_net_id=share_net_info['neutron_net_id'],
                neutron_subnet_id=share_net_info['neutron_subnet_id'],
                cleanup_in_class=False)['id']

        share = self.create_share(share_protocol=self.protocol,
                                  share_type_id=self.share_type['id'],
                                  share_network_id=share_network_id,
                                  cleanup_in_class=False)
        share = self.shares_v2_client.get_share(share['id'])['share']

        # Initial migration setup.
        share, src_server_id, dest_host, snapshot_id = self._setup_migration(
            share)

        preserve_snapshots = True if snapshot_id else False

        # Start share server migration.
        self.shares_v2_client.share_server_migration_start(
            src_server_id, dest_host,
            new_share_network_id=dest_share_network_id,
            preserve_snapshots=preserve_snapshots)

        expected_state = constants.TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE
        waiters.wait_for_resource_status(
            self.shares_v2_client, src_server_id,
            expected_state, resource_name='share_server',
            status_attr='task_state'
        )
        # Get for the destination share server.
        dest_server_id = self._get_share_server_destination_for_migration(
            src_server_id)

        dest_server = self.shares_v2_client.show_share_server(
            dest_server_id)['share_server']
        self.assertEqual(dest_host, dest_server['host'])
        self.assertEqual(dest_share_network_id,
                         dest_server['share_network_id'])

        expected_status = constants.STATUS_SERVER_MIGRATING
        self._validate_state_of_resources(share, expected_status, snapshot_id)

        # Share server migration complete.
        self.shares_v2_client.share_server_migration_complete(src_server_id)

        # It's necessary wait for the destination server went to active status.
        expected_status = constants.SERVER_STATE_ACTIVE
        waiters.wait_for_resource_status(
            self.shares_v2_client, dest_server_id, expected_status,
            resource_name='share_server'
        )

        # Validate the share server migration complete.
        share = self.shares_v2_client.get_share(share['id'])['share']
        self._validate_share_server_migration_complete(
            share, dest_host, dest_server_id, snapshot_id=snapshot_id,
            share_network_id=dest_share_network_id)
        self.admin_shares_client.wait_for_resource_deletion(
            server_id=src_server_id)

    @decorators.idempotent_id('52e154eb-2d39-45af-b5c1-49ea569ab804')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(True, False)
    def test_share_server_migration_check(self, compatible):
        """The share server migration check compatibility tests."""
        share = self.create_share(share_protocol=self.protocol,
                                  share_type_id=self.share_type['id'],
                                  cleanup_in_class=False)
        share = self.shares_v2_client.get_share(share['id'])['share']
        # Find a backend compatible or not for the share server
        # check compatibility operation.
        if compatible:
            dest_host, result = (
                self._choose_compatible_backend_for_share_server(
                    server_id=share['share_server_id']))
            self.assertTrue(result['compatible'])
            self.assertEqual(result['requested_capabilities']['host'],
                             dest_host)
        else:
            dest_host, result = (
                self._choose_incompatible_backend_for_share_server(
                    server_id=share['share_server_id']))
            self.assertFalse(result['compatible'])
            self.assertEqual(result['requested_capabilities'].get('host'),
                             dest_host)


class ShareServerMigrationBasicCIFS(ShareServerMigrationBasicNFS):
    protocol = "cifs"
