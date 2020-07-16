# Copyright 2014 Mirantis Inc.
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
import manila_tempest_tests.tests.api.test_replication_negative as rep_neg_test
from tempest import config
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
PRE_SHARE_GROUPS_MICROVERSION = "2.39"
SHARE_GROUPS_MICROVERSION = "2.40"
PRE_SHARE_REPLICA_QUOTAS_MICROVERSION = "2.52"
SHARE_REPLICA_QUOTAS_MICROVERSION = "2.53"


@ddt.ddt
class SharesAdminQuotasNegativeTest(base.BaseSharesAdminTest):

    # We want to force some fresh projects for this test class, since we'll be
    # manipulating project quotas - and any pre-existing projects may have
    # resources, quotas and the like that might interfere with our test cases.
    force_tenant_isolation = True

    @classmethod
    def skip_checks(cls):
        super(SharesAdminQuotasNegativeTest, cls).skip_checks()
        if not CONF.auth.use_dynamic_credentials:
            raise cls.skipException('Dynamic credentials are required')
        if not CONF.share.run_quota_tests:
            msg = "Quota tests are disabled."
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(SharesAdminQuotasNegativeTest, cls).resource_setup()
        cls.client = cls.shares_v2_client
        cls.user_id = cls.client.user_id
        cls.tenant_id = cls.client.tenant_id
        # create share type
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share group type
        cls.share_group_type = cls._create_share_group_type()
        cls.share_group_type_id = cls.share_group_type['id']

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_quotas_with_empty_tenant_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_quotas, "")

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_reset_quotas_with_empty_tenant_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.client.reset_quotas, "")

    @ddt.data(
        {"shares": -2},
        {"snapshots": -2},
        {"gigabytes": -2},
        {"snapshot_gigabytes": -2},
        {"share_networks": -2},
    )
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_quota_with_wrong_data(self, kwargs):
        # -1 is acceptable value as unlimited
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          **kwargs)

    @ddt.data(
        {"share_groups": -2},
        {"share_group_snapshots": -2},
    )
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @testtools.skipUnless(
        CONF.share.run_share_group_tests, 'Share Group tests disabled.')
    @utils.skip_if_microversion_not_supported(SHARE_GROUPS_MICROVERSION)
    def test_update_sg_quota_with_wrong_data(self, kwargs):
        # -1 is acceptable value as unlimited
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          **kwargs)

    @ddt.data(
        {"share_replicas": -2},
        {"replica_gigabytes": -2},
    )
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported(
        SHARE_REPLICA_QUOTAS_MICROVERSION)
    def test_update_replica_quotas_wrong_data(self, kwargs):
        # -1 is acceptable value as unlimited
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          **kwargs)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_with_size_bigger_than_quota(self):
        quotas = self.client.show_quotas(self.tenant_id)
        overquota = int(quotas['gigabytes']) + 2

        # try schedule share with size, bigger than gigabytes quota
        self.assertRaises(lib_exc.OverLimit,
                          self.create_share,
                          size=overquota)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @testtools.skipUnless(
        CONF.share.run_share_group_tests, 'Share Group tests disabled.')
    @utils.skip_if_microversion_not_supported(SHARE_GROUPS_MICROVERSION)
    def test_create_share_group_with_exceeding_quota_limit(self):
        self.update_quotas(self.tenant_id, share_groups=0)

        # Try schedule share group creation
        self.assertRaises(lib_exc.OverLimit,
                          self.create_share_group,
                          share_group_type_id=self.share_group_type_id,
                          share_type_ids=[self.share_type_id],
                          cleanup_in_class=False)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_user_quota_shares_bigger_than_tenant_quota(self):

        # get current quotas for tenant
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # try set user quota for shares bigger than tenant quota
        bigger_value = int(tenant_quotas["shares"]) + 2
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          user_id=self.user_id,
                          force=False,
                          shares=bigger_value)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_user_quota_snaps_bigger_than_tenant_quota(self):

        # get current quotas for tenant
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # try set user quota for snapshots bigger than tenant quota
        bigger_value = int(tenant_quotas["snapshots"]) + 2
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          user_id=self.user_id,
                          force=False,
                          snapshots=bigger_value)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_user_quota_gigabytes_bigger_than_tenant_quota(self):

        # get current quotas for tenant
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # try set user quota for gigabytes bigger than tenant quota
        bigger_value = int(tenant_quotas["gigabytes"]) + 2
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          user_id=self.user_id,
                          force=False,
                          gigabytes=bigger_value)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_user_quota_snap_gigabytes_bigger_than_tenant_quota(self):
        # get current quotas for tenant
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # try set user quota for snapshot gigabytes bigger than tenant quota
        bigger_value = int(tenant_quotas["snapshot_gigabytes"]) + 2
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          user_id=self.user_id,
                          force=False,
                          snapshot_gigabytes=bigger_value)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_set_user_quota_share_networks_bigger_than_tenant_quota(self):

        # get current quotas for tenant
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # try set user quota for share_networks bigger than tenant quota
        bigger_value = int(tenant_quotas["share_networks"]) + 2
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          user_id=self.user_id,
                          force=False,
                          share_networks=bigger_value)

    @ddt.data("share_replicas", "replica_gigabytes")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @utils.skip_if_microversion_not_supported(
        SHARE_REPLICA_QUOTAS_MICROVERSION)
    def test_try_set_user_quota_replicas_bigger_than_tenant_quota(self, key):
        # get current quotas for tenant
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # try set user quota for snapshots bigger than tenant quota
        bigger_value = int(tenant_quotas[key]) + 2
        kwargs = {key: bigger_value}
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          user_id=self.user_id,
                          force=False,
                          **kwargs)

    @ddt.data(
        ('quota-sets', '2.0', 'show_quotas'),
        ('quota-sets', '2.0', 'default_quotas'),
        ('quota-sets', '2.0', 'reset_quotas'),
        ('quota-sets', '2.0', 'update_quotas'),
        ('quota-sets', '2.6', 'show_quotas'),
        ('quota-sets', '2.6', 'default_quotas'),
        ('quota-sets', '2.6', 'reset_quotas'),
        ('quota-sets', '2.6', 'update_quotas'),
        ('os-quota-sets', '2.7', 'show_quotas'),
        ('os-quota-sets', '2.7', 'default_quotas'),
        ('os-quota-sets', '2.7', 'reset_quotas'),
        ('os-quota-sets', '2.7', 'update_quotas'),
    )
    @ddt.unpack
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_not_supported("2.7")
    def test_show_quotas_with_wrong_versions(self, url, version, method_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self.client, method_name),
                          self.tenant_id,
                          version=version,
                          url=url)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_show_quota_detail_with_wrong_versions(self):
        version = '2.24'
        url = 'quota-sets'

        self.assertRaises(lib_exc.NotFound,
                          self.client.detail_quotas,
                          self.tenant_id,
                          version=version,
                          url=url)

    @ddt.data('show', 'reset', 'update')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_lt("2.39")
    def test_share_type_quotas_using_nonexistent_share_type(self, op):

        kwargs = {"share_type": "fake_nonexistent_share_type"}
        if op == 'update':
            tenant_quotas = self.client.show_quotas(self.tenant_id)
            kwargs['shares'] = tenant_quotas['shares']

        self.assertRaises(lib_exc.NotFound,
                          getattr(self.client, op + '_quotas'),
                          self.tenant_id,
                          **kwargs)

    @ddt.data('id', 'name')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_lt("2.39")
    def test_try_update_share_type_quota_for_share_networks(self, key):
        share_type = self._create_share_type()
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        # Try to set 'share_networks' quota for share type
        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          share_type=share_type[key],
                          share_networks=int(tenant_quotas["share_networks"]))

    @ddt.data('share_groups', 'share_group_snapshots')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_lt(SHARE_GROUPS_MICROVERSION)
    def test_try_update_share_type_quota_for_share_groups(self, quota_name):
        share_type = self._create_share_type()
        tenant_quotas = self.client.show_quotas(self.tenant_id)

        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          share_type=share_type["name"],
                          **{quota_name: int(tenant_quotas[quota_name])})

    @ddt.data('share_groups', 'share_group_snapshots')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_not_supported(PRE_SHARE_GROUPS_MICROVERSION)
    @base.skip_if_microversion_not_supported(SHARE_GROUPS_MICROVERSION)
    def test_share_group_quotas_using_too_old_microversion(self, quota_key):
        tenant_quotas = self.client.show_quotas(
            self.tenant_id, version=SHARE_GROUPS_MICROVERSION)
        kwargs = {
            "version": PRE_SHARE_GROUPS_MICROVERSION,
            quota_key: tenant_quotas[quota_key],
        }

        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_quotas,
                          self.tenant_id,
                          **kwargs)

    @ddt.data("share_replicas", "replica_gigabytes")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_not_supported(SHARE_REPLICA_QUOTAS_MICROVERSION)
    def test_share_replica_quotas_using_too_old_microversion(self, quota_key):
        tenant_quotas = self.client.show_quotas(
            self.tenant_id, version=SHARE_REPLICA_QUOTAS_MICROVERSION)
        kwargs = {
            "version": PRE_SHARE_REPLICA_QUOTAS_MICROVERSION,
            quota_key: tenant_quotas[quota_key],
        }

        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          **kwargs)

    @ddt.data('show', 'reset', 'update')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_lt("2.38")
    def test_share_type_quotas_using_too_old_microversion(self, op):
        share_type = self._create_share_type()
        kwargs = {"version": "2.38", "share_type": share_type["name"]}
        if op == 'update':
            tenant_quotas = self.client.show_quotas(self.tenant_id)
            kwargs['shares'] = tenant_quotas['shares']

        self.assertRaises(lib_exc.BadRequest,
                          getattr(self.client, op + '_quotas'),
                          self.tenant_id,
                          **kwargs)

    @ddt.data('show', 'reset', 'update')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_lt("2.39")
    def test_quotas_providing_share_type_and_user_id(self, op):
        share_type = self._create_share_type()
        kwargs = {"share_type": share_type["name"], "user_id": self.user_id}
        if op == 'update':
            tenant_quotas = self.client.show_quotas(self.tenant_id)
            kwargs['shares'] = tenant_quotas['shares']

        self.assertRaises(lib_exc.BadRequest,
                          getattr(self.client, op + '_quotas'),
                          self.tenant_id,
                          **kwargs)

    @ddt.data(11, -1)
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @base.skip_if_microversion_lt("2.39")
    def test_update_share_type_quotas_bigger_than_project_quota(self, st_q):
        share_type = self._create_share_type()
        self.update_quotas(self.tenant_id, shares=10)

        self.assertRaises(lib_exc.BadRequest,
                          self.update_quotas,
                          self.tenant_id,
                          share_type=share_type['name'],
                          force=False,
                          shares=st_q)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_share_over_quota_limit(self):
        self.create_share(share_type_id=self.share_type_id)

        updated_quota = self.update_quotas(self.tenant_id, shares=1)
        self.assertEqual(1, updated_quota['shares'])

        self.assertRaises(lib_exc.OverLimit,
                          self.create_share,
                          share_type_id=self.share_type_id)


@ddt.ddt
class ReplicaQuotasNegativeTest(rep_neg_test.ReplicationNegativeBase):

    # We want to force some fresh projects for this test class, since we'll be
    # manipulating project quotas - and any pre-existing projects may have
    # resources, quotas and the like that might interfere with our test cases.
    force_tenant_isolation = True

    @classmethod
    def resource_setup(cls):
        super(ReplicaQuotasNegativeTest, cls).resource_setup()
        cls.client = cls.shares_v2_client
        cls.user_id = cls.client.user_id
        cls.tenant_id = cls.client.tenant_id

    @classmethod
    def skip_checks(cls):
        super(ReplicaQuotasNegativeTest, cls).skip_checks()
        if not CONF.auth.use_dynamic_credentials:
            raise cls.skipException('Dynamic credentials are required')
        if not CONF.share.run_quota_tests:
            msg = "Quota tests are disabled."
            raise cls.skipException(msg)
        utils.check_skip_if_microversion_lt(SHARE_REPLICA_QUOTAS_MICROVERSION)

    def _modify_quotas_for_test(self, quota_key, new_limit):
        kwargs = {quota_key: new_limit}

        # Update the current quotas
        self.update_quotas(self.tenant_id, client=self.admin_client, **kwargs)

        # Get the updated quotas and add a cleanup
        updated_quota = self.admin_client.show_quotas(self.tenant_id)

        # Make sure that the new value was properly set
        self.assertEqual(new_limit, updated_quota[quota_key])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(('share_replicas', 2), ('replica_gigabytes', None))
    @ddt.unpack
    def test_create_replica_over_replica_limit(self, quota_key, new_limit):
        # Define the quota values to be updated
        new_limit = (int(self.share1['size'] * 2)
                     if quota_key == 'replica_gigabytes' else new_limit)

        # Create an inactive share replica
        self.create_share_replica(
            self.share1["id"], self.replica_zone, cleanup_in_class=False)

        # Modify the quota limit for this test
        self._modify_quotas_for_test(quota_key, new_limit)

        # Make sure that the request to create a third one will fail
        self.assertRaises(lib_exc.OverLimit,
                          self.create_share_replica,
                          self.share1['id'],
                          availability_zone=self.replica_zone)

    @testtools.skipUnless(
        CONF.share.run_extend_tests,
        "Share extend tests are disabled.")
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_extend_replica_over_limit(self):
        # Define the quota values to be updated
        quota_key = 'replica_gigabytes'

        # Modify the quota limit for this test
        self._modify_quotas_for_test(quota_key, new_limit=self.share1['size'])

        new_size = self.share1['size'] + 1

        # Make sure that the request to create a third one will fail
        self.assertRaises(lib_exc.OverLimit,
                          self.client.extend_share,
                          self.share1['id'],
                          new_size)
