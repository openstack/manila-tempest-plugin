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

from collections import defaultdict

from tempest import config
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


class SharesFromSnapshotAcrossPools(base.BaseSharesMixedTest):
    """Test class for share creation from a snapshot across pools."""

    @classmethod
    def resource_setup(cls):
        super(SharesFromSnapshotAcrossPools, cls).resource_setup()
        # create share_type
        extra_specs = {"create_share_from_snapshot_support": True,
                       "snapshot_support": True}
        cls.share_type = cls._create_share_type(specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        cls.admin_client = cls.admin_shares_v2_client
        cls.pools = cls.get_pools_matching_share_type(cls.share_type,
                                                      client=cls.admin_client)
        if len(cls.pools) < 2:
            msg = ("Could not find the necessary pools. At least two "
                   "compatibles pools are needed to run the tests to create "
                   "share from snapshot across pools.")
            raise cls.skipException(msg)

        # Availability zones grouped by 'replication_domain'
        cls.rep_domain_azs = defaultdict(set)
        for pool in cls.pools:
            backend = pool['name'].split("#")[0]
            rep_domain = pool['capabilities'].get('replication_domain')

            if rep_domain is not None:
                # Update pools with the availability zone
                pool['availability_zone'] = (
                    cls.get_availability_zones(backends=[backend])[0])
                cls.rep_domain_azs[rep_domain].add(pool['availability_zone'])

    @classmethod
    def skip_checks(cls):
        super(SharesFromSnapshotAcrossPools, cls).skip_checks()
        if not CONF.share.capability_create_share_from_snapshot_support:
            raise cls.skipException(
                'Create share from snapshot tests are disabled.')
        if (not CONF.share
                .run_create_share_from_snapshot_in_another_pool_or_az_tests):
            raise cls.skipException(
                'Create share from snapshot in another pool or az tests are '
                'disabled.')
        utils.check_skip_if_microversion_lt("2.54")

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_share_from_snapshot_across_pools_within_backend(self):
        backends = [pool['backend'] for pool in self.pools]
        duplicated_backend_names = [x for n, x in enumerate(backends)
                                    if x in backends[:n]]
        if not duplicated_backend_names:
            msg = ("Could not find the necessary pools. At least two pools in"
                   " the same backend are needed to run the tests to create"
                   " share from snapshot in another pool in the same backend.")
            raise self.skipException(msg)

        # This filter will return the pool_names of the first duplicated
        # backend
        pool_names = [x['pool'] for x in filter(
            lambda x: x['backend'] == duplicated_backend_names[0], self.pools)]

        # Creating share type setting up the pool_name and backend_name
        extra_specs = {"pool_name": pool_names[0]}
        self.admin_client.update_share_type_extra_specs(
            self.share_type['id'], extra_specs)
        share_type_a_get = self.admin_client.get_share_type(
            self.share_type['id'])

        self.addCleanup(
            self.admin_shares_v2_client.delete_share_type_extra_spec,
            self.share_type['id'], 'pool_name')

        # Create source share
        share_a = self.create_share(
            share_type_id=share_type_a_get["share_type"]["id"])

        # Retrieving the share using admin client because the shares's host
        # field is necessary to do the assert
        share_get_a = self.admin_client.get_share(share_a["id"])

        # Create snapshot from source share
        snap = self.create_snapshot_wait_for_active(share_get_a["id"])

        # There's really no other way of deterministically ensuring a snapshot
        # can be cloned in a different pool, because the scheduler will ensure
        # it finds the best pool with knowledge that make senses at that point
        # in time. Force the creation in another pool using the same share type
        self.admin_client.update_share_type_extra_spec(
            self.share_type['id'], "pool_name", pool_names[1])

        # Create share from snapshot another pool
        share_b = self.create_share(snapshot_id=snap["id"])

        # Retrieving the share using admin client because the shares's host
        # field is necessary to do the assert
        share_get_b = self.admin_client.get_share(share_b['id'])

        # Verify share created from snapshot
        msg = ("Expected snapshot_id %s as "
               "source of share %s" % (snap["id"], share_get_b["snapshot_id"]))
        self.assertEqual(share_get_b["snapshot_id"], snap["id"], msg)

        # Verify different pools
        pool_name_a = share_get_a["host"].split("#")[1]
        pool_name_b = share_get_b["host"].split("#")[1]
        msg = ("The snapshot clone share was created on the same pool as the"
               " source share %s" % pool_name_a)
        self.assertNotEqual(pool_name_a, pool_name_b, msg)

    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_share_from_snapshot_across_azs(self):
        azs = next((self.rep_domain_azs[rep] for rep in self.rep_domain_azs if
                    len(self.rep_domain_azs[rep]) > 1), None)
        if azs is None:
            msg = ("Could not find the necessary azs. At least two azs "
                   "are needed to run the test to create share from snapshot "
                   "across azs.")
            raise self.skipException(msg)
        azs = list(azs)
        share_a = self.create_share(share_type_id=self.share_type_id,
                                    is_public=True,
                                    availability_zone=azs[0])

        # Create snapshot
        snap = self.create_snapshot_wait_for_active(share_a["id"])

        # Create share from snapshot
        share_b = self.create_share(availability_zone=azs[1],
                                    snapshot_id=snap["id"])

        # Verify share created from snapshot
        msg = ("Expected snapshot_id %s as "
               "source of share: %s" % (snap["id"], share_b["snapshot_id"]))
        self.assertEqual(share_b["snapshot_id"], snap["id"], msg)

        # Verify different azs
        msg = ("The snapshot clone share was created on the same AZ as the"
               " source share %s" % share_a["availability_zone"])
        self.assertNotEqual(share_b["availability_zone"],
                            share_a["availability_zone"],
                            msg)
