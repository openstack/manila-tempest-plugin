# Copyright 2016 Andrew Kerr
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
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class ShareGroupsTest(base.BaseSharesMixedTest):
    """Covers share group functionality."""

    @classmethod
    def skip_checks(cls):
        super(ShareGroupsTest, cls).skip_checks()
        if not CONF.share.run_share_group_tests:
            raise cls.skipException('Share Group tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            constants.MIN_SHARE_GROUP_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ShareGroupsTest, cls).resource_setup()
        # create share type
        extra_specs = {}
        if CONF.share.capability_snapshot_support:
            extra_specs.update({'snapshot_support': True})
        if CONF.share.capability_create_share_from_snapshot_support:
            extra_specs.update({'create_share_from_snapshot_support': True})
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

        # create share group type
        cls.share_group_type = cls._create_share_group_type()
        cls.share_group_type_id = cls.share_group_type['id']

    @decorators.idempotent_id('809d5e3d-5a4b-458a-a985-853d59800da5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_populate_delete_share_group_min(self):
        # Create a share group
        share_group = self.create_share_group(
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION,
            share_group_type_id=self.share_group_type_id,
            share_type_ids=[self.share_type_id],
        )

        keys = set(share_group.keys())
        self.assertTrue(
            constants.SHARE_GROUP_DETAIL_REQUIRED_KEYS.issubset(keys),
            'At least one expected element missing from share group '
            'response. Expected %(expected)s, got %(actual)s.' % {
                "expected": constants.SHARE_GROUP_DETAIL_REQUIRED_KEYS,
                "actual": keys}
        )
        # Populate
        share = self.create_share(
            share_type_id=self.share_type_id,
            share_group_id=share_group['id'],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        # Delete
        params = {"share_group_id": share_group['id']}
        self.shares_v2_client.delete_share(
            share['id'],
            params=params,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)
        self.shares_client.wait_for_resource_deletion(share_id=share['id'])
        self.shares_v2_client.delete_share_group(
            share_group['id'], version=constants.MIN_SHARE_GROUP_MICROVERSION)
        self.shares_v2_client.wait_for_resource_deletion(
            share_group_id=share_group['id'])

        # Verify
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.get_share_group, share_group['id'])
        self.assertRaises(
            lib_exc.NotFound, self.shares_client.get_share, share['id'])

    @decorators.idempotent_id('cf7984af-1e1d-4eaf-bf9a-d8ddf5cebd01')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_create_delete_empty_share_group_snapshot_min(self):
        # Create base share group
        share_group = self.create_share_group(
            share_group_type_id=self.share_group_type_id,
            share_type_ids=[self.share_type_id],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        # Create share group snapshot
        sg_snapshot = self.create_share_group_snapshot_wait_for_active(
            share_group["id"],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        keys = set(sg_snapshot.keys())
        self.assertTrue(
            constants.SHARE_GROUP_SNAPSHOT_DETAIL_REQUIRED_KEYS.issubset(keys),
            'At least one expected element missing from share group snapshot '
            'response. Expected %(e)s, got %(a)s.' % {
                "e": constants.SHARE_GROUP_SNAPSHOT_DETAIL_REQUIRED_KEYS,
                "a": keys})

        sg_snapshot_members = sg_snapshot['members']
        self.assertEmpty(
            sg_snapshot_members,
            'Expected 0 share_group_snapshot members, got %s' % len(
                sg_snapshot_members))

        # Delete snapshot
        self.shares_v2_client.delete_share_group_snapshot(
            sg_snapshot["id"], version=constants.MIN_SHARE_GROUP_MICROVERSION)
        self.shares_v2_client.wait_for_resource_deletion(
            share_group_snapshot_id=sg_snapshot["id"])
        self.assertRaises(
            lib_exc.NotFound,
            self.shares_v2_client.get_share_group_snapshot,
            sg_snapshot['id'],
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

    @decorators.idempotent_id('727d9c69-4c3b-4375-a91b-8b3efd349976')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_create_share_group_from_empty_share_group_snapshot_min(self):
        # Create base share group
        share_group = self.create_share_group(
            share_group_type_id=self.share_group_type_id,
            share_type_ids=[self.share_type_id],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        # Create share group snapshot
        sg_snapshot = self.create_share_group_snapshot_wait_for_active(
            share_group["id"], cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        snapshot_members = sg_snapshot['members']

        self.assertEmpty(
            snapshot_members,
            'Expected 0 share group snapshot members, got %s' %
            len(snapshot_members))

        new_share_group = self.create_share_group(
            share_group_type_id=self.share_group_type_id,
            cleanup_in_class=False,
            source_share_group_snapshot_id=sg_snapshot['id'],
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        new_shares = self.shares_v2_client.list_shares(
            params={'share_group_id': new_share_group['id']},
            version=constants.MIN_SHARE_GROUP_MICROVERSION)['shares']

        self.assertEmpty(
            new_shares, 'Expected 0 new shares, got %s' % len(new_shares))

        msg = ('Expected source_ishare_group_snapshot_id %s '
               'as source of share group %s' % (
                   sg_snapshot['id'],
                   new_share_group['source_share_group_snapshot_id']))
        self.assertEqual(
            new_share_group['source_share_group_snapshot_id'],
            sg_snapshot['id'],
            msg)

        msg = ('Unexpected share_types on new share group. Expected '
               '%s, got %s.' % (share_group['share_types'],
                                new_share_group['share_types']))
        self.assertEqual(
            sorted(share_group['share_types']),
            sorted(new_share_group['share_types']), msg)

        # Assert the share_network information is the same
        msg = 'Expected share_network %s as share_network of cg %s' % (
            share_group['share_network_id'],
            new_share_group['share_network_id'])
        self.assertEqual(
            share_group['share_network_id'],
            new_share_group['share_network_id'],
            msg)

    @utils.skip_if_microversion_not_supported("2.34")
    @decorators.idempotent_id('14fd6d88-87ff-4af2-ad17-f95dbd8dcd61')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(
        'sg', 'sg_and_share', 'none',
    )
    def test_create_sg_and_share_specifying_az(self, where_specify_az):
        # Get list of existing availability zones, at least one always
        # should exist
        azs = self.get_availability_zones_matching_share_type(
            self.share_type)

        sg_kwargs = {
            'share_group_type_id': self.share_group_type_id,
            'share_type_ids': [self.share_type_id],
            'version': '2.34',
            'cleanup_in_class': False,
        }
        if where_specify_az in ('sg', 'sg_and_share'):
            sg_kwargs['availability_zone'] = azs[0]

        # Create share group
        share_group = self.create_share_group(**sg_kwargs)

        # Get latest share group info
        share_group = self.shares_v2_client.get_share_group(
            share_group['id'], '2.34')['share_group']

        self.assertIn('availability_zone', share_group)
        if where_specify_az in ('sg', 'sg_and_share'):
            self.assertEqual(azs[0], share_group['availability_zone'])
        else:
            self.assertIn(share_group['availability_zone'], azs)

        # Test 'consistent_snapshot_support' as part of 2.33 API change
        self.assertIn('consistent_snapshot_support', share_group)
        self.assertIn(
            share_group['consistent_snapshot_support'], ('host', 'pool', None))

        s_kwargs = {
            'share_type_id': self.share_type_id,
            'share_group_id': share_group['id'],
            'version': '2.33',
            'cleanup_in_class': False,
        }
        if where_specify_az == 'sg_and_share':
            s_kwargs['availability_zone'] = azs[0]

        # Create share in share group
        share = self.create_share(**s_kwargs)

        # Get latest share info
        share = self.shares_v2_client.get_share(share['id'], '2.34')['share']

        # Verify that share always has the same AZ as share group does
        self.assertEqual(
            share_group['availability_zone'], share['availability_zone'])

    @utils.skip_if_microversion_not_supported("2.70")
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.multitenancy_enabled,
                          "Multitenancy is disabled.")
    @testtools.skipUnless(CONF.share.run_share_server_multiple_subnet_tests,
                          "Share server multiple subnet tests are disabled.")
    @testtools.skipIf(CONF.share.share_network_id != "",
                      "This test is not suitable for pre-existing "
                      "share networks.")
    @ddt.data(False, True)
    @decorators.idempotent_id('17fd1867-03a3-43d0-9be3-daf90b6c5e02')
    def test_create_sg_and_share_with_multiple_subnets(
        self, network_allocation_update):
        if network_allocation_update and not (
            CONF.share.run_network_allocation_update_tests):
            raise self.skipException(
                'Network allocation update tests are disabled.')
        extra_specs = {
            'driver_handles_share_servers': CONF.share.multitenancy_enabled,
            'share_server_multiple_subnet_support': True,
        }
        if network_allocation_update:
            extra_specs['network_allocation_update_support'] = True
        share_type = self.create_share_type(extra_specs=extra_specs)
        sg_type_name = data_utils.rand_name("tempest-manila")
        sg_type = self.create_share_group_type(
            name=sg_type_name, share_types=share_type['id'],
            client=self.admin_shares_v2_client)
        # Get list of existing availability zones, at least one always
        # should exist
        azs = self.get_availability_zones_matching_share_type(share_type)
        if len(azs) == 0:
            raise self.skipException(
                "No AZs were found. Make sure there is at least one "
                "configured.")
        share_network = self.shares_v2_client.get_share_network(
            self.shares_v2_client.share_network_id)['share_network']
        new_share_network_id = self.create_share_network(
            cleanup_in_class=False)['id']

        default_subnet = utils.share_network_get_default_subnet(
            share_network)
        subnet_data = {
            'neutron_net_id': default_subnet.get('neutron_net_id'),
            'neutron_subnet_id': default_subnet.get('neutron_subnet_id'),
            'share_network_id': new_share_network_id,
            'availability_zone': azs[0]
        }
        subnet1 = self.create_share_network_subnet(**subnet_data)
        if not network_allocation_update:
            subnet2 = self.create_share_network_subnet(**subnet_data)

        sg_kwargs = {
            'share_group_type_id': sg_type['id'],
            'share_type_ids': [share_type['id']],
            'share_network_id': new_share_network_id,
            'availability_zone': azs[0],
            'version': constants.MIN_SHARE_GROUP_MICROVERSION,
            'cleanup_in_class': False,
        }

        # Create share group
        share_group = self.create_share_group(**sg_kwargs)

        # Get latest share group info
        share_group = self.shares_v2_client.get_share_group(
            share_group['id'])['share_group']

        self.assertIn('availability_zone', share_group)
        self.assertEqual(azs[0], share_group['availability_zone'])

        # Test 'consistent_snapshot_support' as part of 2.33 API change
        self.assertIn('consistent_snapshot_support', share_group)
        self.assertIn(
            share_group['consistent_snapshot_support'], ('host', 'pool', None))

        share_data = {
            'share_type_id': share_type['id'],
            'share_group_id': share_group['id'],
            'share_network_id': new_share_network_id,
            'availability_zone': azs[0],
            'cleanup_in_class': False,
        }

        # Create share in share group
        share = self.create_share(**share_data)

        # Get latest share info
        share = self.admin_shares_v2_client.get_share(share['id'])['share']
        # Verify that share always has the same AZ as share group does
        self.assertEqual(
            share_group['availability_zone'], share['availability_zone'])

        # Get share server info
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id'])['share_server']
        if network_allocation_update:
            waiters.wait_for_subnet_create_check(
                self.shares_v2_client, new_share_network_id,
                neutron_net_id=subnet_data['neutron_net_id'],
                neutron_subnet_id=subnet_data['neutron_subnet_id'],
                availability_zone=azs[0])

            subnet2 = self.create_share_network_subnet(**subnet_data)
            waiters.wait_for_resource_status(
                self.admin_shares_v2_client, share['share_server_id'],
                constants.SERVER_STATE_ACTIVE,
                resource_name="share_server",
                status_attr="status")
        share_server = self.admin_shares_v2_client.show_share_server(
            share['share_server_id'])['share_server']
        # Check if share server has multiple subnets
        self.assertIn(subnet1['id'], share_server['share_network_subnet_ids'])
        self.assertIn(subnet2['id'], share_server['share_network_subnet_ids'])
        # Delete share
        params = {"share_group_id": share_group['id']}
        self.shares_v2_client.delete_share(
            share['id'],
            params=params,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)
        self.shares_client.wait_for_resource_deletion(share_id=share['id'])
        # Delete subnet
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet1['id'])
        self.shares_v2_client.delete_subnet(
            new_share_network_id, subnet2['id'])
