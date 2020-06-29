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
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.api import test_snapshot_rules
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class SnapshotIpRulesForNFSNegativeTest(
        test_snapshot_rules.BaseShareSnapshotRulesTest):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(SnapshotIpRulesForNFSNegativeTest, cls).skip_checks()
        if not CONF.share.run_snapshot_tests:
            raise cls.skipException('Snapshot tests are disabled.')
        if not CONF.share.run_mount_snapshot_tests:
            raise cls.skipException('Mountable snapshots tests are disabled.')
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_ip_rules_for_protocols):
            msg = "IP rule tests for %s protocol are disabled." % cls.protocol
            raise cls.skipException(msg)

        utils.check_skip_if_microversion_lt('2.32')

    @classmethod
    def resource_setup(cls):
        super(SnapshotIpRulesForNFSNegativeTest, cls).resource_setup()
        # create share type
        extra_specs = {'mount_snapshot_support': 'True'}
        cls.share_type = cls._create_share_type(specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        cls.snap = cls.create_snapshot_wait_for_active(cls.share["id"])

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data("1.2.3.256", "1.1.1.-", "1.2.3.4/33", "1.2.3.*", "1.2.3.*/23",
              "1.2.3.1|23", "1.2.3.1/", "1.2.3.1/-1",
              "fe80:217:f2ff:fe07:ed62", "2001:db8::1/148",
              "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
              "2001:0db8:0000:85a3:0000:0000:ac1f:8001/64")
    def test_create_access_rule_ip_with_wrong_target(self, target):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_snapshot_access_rule,
                          self.snap["id"], "ip", target)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data("1.2.3.4", "fd8c:b029:bba6:ac54::1",
              "fd8c:b029:bba6:ac54::1/128", "1.2.3.4/32")
    def test_create_duplicate_of_ip_rule(self, access_to):
        self._test_duplicate_rules(access_to)
        self._test_duplicate_rules(access_to)

    def _test_duplicate_rules(self, access_to):
        if ':' in access_to and utils.is_microversion_lt(
                CONF.share.max_api_microversion, '2.38'):
            reason = ("Skipped. IPv6 rules are accepted from and beyond "
                      "API version 2.38, the configured maximum API version "
                      "is %s" % CONF.share.max_api_microversion)
            raise self.skipException(reason)

        # test data
        access_type = "ip"

        # create rule
        rule = self.shares_v2_client.create_snapshot_access_rule(
            self.snap['id'], access_type, access_to)

        self.shares_v2_client.wait_for_snapshot_access_rule_status(
            self.snap['id'], rule['id'])

        # try create duplicate of rule
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_snapshot_access_rule,
                          self.snap["id"], access_type, access_to)

        # try alternate notation
        if '/' in access_to:
            access_to = access_to.split("/")[0]
        else:
            access_to = ('%s/32' % access_to if '.' in access_to else
                         '%s/128' % access_to)
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_snapshot_access_rule,
                          self.snap["id"], access_type, access_to)

        # delete rule and wait for deletion
        self.shares_v2_client.delete_snapshot_access_rule(self.snap['id'],
                                                          rule['id'])
        self.shares_v2_client.wait_for_snapshot_access_rule_deletion(
            self.snap['id'], rule['id'])

        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_snapshot_access_rule,
                          self.snap['id'], rule['id'])
