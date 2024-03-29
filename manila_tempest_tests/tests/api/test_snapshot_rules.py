# Copyright 2016 Hitachi Data Systems
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
from testtools import testcase as tc

from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF


class BaseShareSnapshotRulesTest(base.BaseSharesMixedTest):

    protocol = ""

    @classmethod
    def resource_setup(cls):
        super(BaseShareSnapshotRulesTest, cls).resource_setup()
        # create share_type
        extra_specs = {
            'snapshot_support': True,
            'mount_snapshot_support': True,
        }
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        cls.snapshot = cls.create_snapshot_wait_for_active(cls.share['id'])

    def _test_create_delete_access_rules(self, access_to):
        # create rule
        rule = self.shares_v2_client.create_snapshot_access_rule(
            self.snapshot['id'], self.access_type,
            access_to)['snapshot_access']

        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, list(rule.keys()))

        waiters.wait_for_resource_status(
            self.shares_v2_client, self.snapshot['id'], 'active',
            resource_name='snapshot_access', rule_id=rule['id'],
            status_attr='state')

        # delete rule and wait for deletion
        self.shares_v2_client.delete_snapshot_access_rule(self.snapshot['id'],
                                                          rule['id'])
        waiters.wait_for_snapshot_access_rule_deletion(
            self.shares_v2_client, self.snapshot['id'], rule['id'])


@ddt.ddt
class ShareSnapshotIpRulesForNFSTest(BaseShareSnapshotRulesTest):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareSnapshotIpRulesForNFSTest, cls).skip_checks()
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')
        if not CONF.share.run_mount_snapshot_tests:
            raise cls.skipException('Mountable snapshots tests are disabled.')
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_ip_rules_for_protocols):
            msg = "IP rule tests for %s protocol are disabled." % cls.protocol
            raise cls.skipException(msg)

        utils.check_skip_if_microversion_not_supported('2.32')

    @classmethod
    def resource_setup(cls):
        super(ShareSnapshotIpRulesForNFSTest, cls).resource_setup()
        cls.access_type = "ip"

    @decorators.idempotent_id('bdce2be8-80b9-4f68-bdc0-09a52ba0e6fd')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data("1.1.1.1", "1.2.3.4/32")
    def test_create_delete_access_rules(self, access_to):
        self._test_create_delete_access_rules(access_to)


@ddt.ddt
class ShareSnapshotUserRulesForCIFSTest(BaseShareSnapshotRulesTest):
    protocol = "cifs"

    @classmethod
    def skip_checks(cls):
        super(ShareSnapshotUserRulesForCIFSTest, cls).skip_checks()
        if not CONF.share.run_mount_snapshot_tests:
            raise cls.skipException('Mountable snapshots tests are disabled.')
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_user_rules_for_protocols):
            msg = ("User rule tests for %s protocol are "
                   "disabled." % cls.protocol)
            raise cls.skipException(msg)
        utils.check_skip_if_microversion_not_supported('2.32')

    @classmethod
    def resource_setup(cls):
        super(ShareSnapshotUserRulesForCIFSTest, cls).resource_setup()
        cls.access_type = "user"

    @decorators.idempotent_id('c2625cd2-4dc0-431d-b47b-8f097e22f16d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    def test_create_delete_access_rules(self):
        access_to = CONF.share.username_for_user_rules
        self._test_create_delete_access_rules(access_to)
