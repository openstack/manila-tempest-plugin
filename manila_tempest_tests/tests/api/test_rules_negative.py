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
from tempest import config
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
LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class ShareIpRulesForNFSNegativeTest(base.BaseSharesMixedTest):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareIpRulesForNFSNegativeTest, cls).skip_checks()
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_ip_rules_for_protocols):
            msg = "IP rule tests for %s protocol are disabled" % cls.protocol
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(ShareIpRulesForNFSNegativeTest, cls).resource_setup()
        cls.admin_client = cls.admin_shares_v2_client

        # create share_type
        extra_specs = None
        if CONF.share.run_snapshot_tests:
            extra_specs = {'snapshot_support': True}
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        if CONF.share.run_snapshot_tests:
            # create snapshot
            cls.snap = cls.create_snapshot_wait_for_active(cls.share["id"])

    @decorators.idempotent_id('16781b45-d2bb-4891-aa97-c28c0769d5bd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('1.2.3.256',
              '1.1.1.-',
              '1.2.3.4/33',
              '1.2.3.*',
              '1.2.3.*/23',
              '1.2.3.1|23',
              '1.2.3.1/-1',
              '1.2.3.1/',
              'ad80::abaa:0:c2:2/-3',
              'AD80:ABAA::|26',
              '2001:DB8:2de:0:0:0:0:e13:200a',
              )
    def test_create_access_rule_ip_with_wrong_target(self, ip_address):
        for client_name in ['shares_client', 'shares_v2_client']:
            self.assertRaises(lib_exc.BadRequest,
                              getattr(self, client_name).create_access_rule,
                              self.share["id"], "ip", ip_address)

    @decorators.idempotent_id('e891deff-23d9-4872-911c-bd9b43dc797f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_with_wrong_level(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"],
                          'ip',
                          '2.2.2.2',
                          'su')

    @decorators.idempotent_id('efd594aa-dd24-427e-acdf-10d124afb572')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('1.0', '2.9', LATEST_MICROVERSION)
    def test_create_duplicate_of_ip_rule(self, version):
        # test data
        access_type = "ip"
        access_to = "1.2.3.4"

        if utils.is_microversion_eq(version, '1.0'):
            client = self.shares_client
        else:
            client = self.shares_v2_client

        # create rule
        self.allow_access(
            self.share["id"], client=client, access_type=access_type,
            access_to=access_to, version=version)

        # try create duplicate of rule
        if utils.is_microversion_eq(version, '1.0'):
            self.assertRaises(lib_exc.BadRequest,
                              self.shares_client.create_access_rule,
                              self.share["id"], access_type, access_to)
        else:
            self.assertRaises(lib_exc.BadRequest,
                              self.shares_v2_client.create_access_rule,
                              self.share["id"], access_type, access_to,
                              version=version)

    @decorators.idempotent_id('63932d1d-a60a-4af7-ba3b-7cf6c68aaee9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data("10.20.30.40", "fd8c:b029:bba6:ac54::1",
              "fd2c:b029:bba6:df54::1/128", "10.10.30.40/32")
    def test_create_duplicate_single_host_rules(self, access_to):
        """Test rules for individual clients with and without max-prefix."""
        if ':' in access_to and utils.is_microversion_lt(
                CONF.share.max_api_microversion, '2.38'):
            reason = ("Skipped. IPv6 rules are accepted from and beyond "
                      "API version 2.38, the configured maximum API version "
                      "is %s" % CONF.share.max_api_microversion)
            raise self.skipException(reason)

        self.allow_access(
            self.share["id"], access_type="ip", access_to=access_to)

        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_access_rule,
                          self.share["id"], "ip", access_to)

        if '/' in access_to:
            access_to = access_to.split("/")[0]
        else:
            access_to = ('%s/32' % access_to if '.' in access_to else
                         '%s/128' % access_to)

        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_access_rule,
                          self.share["id"], "ip", access_to)

    @decorators.idempotent_id('d2856c7d-9417-416d-8d08-e68376ee5b2e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_add_access_rule_on_share_with_no_host(self):
        access_type, access_to = self._get_access_rule_data_from_config()
        extra_specs = self.add_extra_specs_to_dict(
            {"share_backend_name": 'invalid_backend'})
        share_type = self.create_share_type('invalid_backend',
                                            extra_specs=extra_specs,
                                            client=self.admin_client,
                                            cleanup_in_class=False)
        share = self.create_share(share_type_id=share_type['id'],
                                  cleanup_in_class=False,
                                  wait_for_status=False)
        waiters.wait_for_resource_status(
            self.shares_v2_client, share['id'], constants.STATUS_ERROR)
        self.assertRaises(lib_exc.BadRequest,
                          self.admin_client.create_access_rule,
                          share["id"], access_type, access_to)


@ddt.ddt
class ShareIpRulesForCIFSNegativeTest(ShareIpRulesForNFSNegativeTest):
    protocol = "cifs"


@ddt.ddt
class ShareUserRulesForNFSNegativeTest(base.BaseSharesMixedTest):
    protocol = "nfs"

    @classmethod
    def resource_setup(cls):
        super(ShareUserRulesForNFSNegativeTest, cls).resource_setup()
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_user_rules_for_protocols):
            msg = "USER rule tests for %s protocol are disabled" % cls.protocol
            raise cls.skipException(msg)
        # create share type
        extra_specs = None
        if CONF.share.run_snapshot_tests:
            extra_specs = {'snapshot_support': True}
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        if CONF.share.run_snapshot_tests:
            # create snapshot
            cls.snap = cls.create_snapshot_wait_for_active(cls.share["id"])

    @decorators.idempotent_id('d6148911-3a0c-4e1f-afdb-fcf203fe4a5b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_user_with_wrong_input_2(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "user",
                          "try+")

    @decorators.idempotent_id('a4d8358d-dec0-4c2a-a544-182816a0ba6f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_user_with_empty_key(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "user", "")

    @decorators.idempotent_id('f5252e86-4767-48ad-8be5-43e12c93df79')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_user_with_too_little_key(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "user", "abc")

    @decorators.idempotent_id('f8f4d3ee-82b8-4d37-917d-a0cd72073df4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_user_with_too_big_key(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "user", "a" * 256)

    @decorators.idempotent_id('21724a99-0790-49d5-a069-d1df43782965')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_user_with_wrong_input_1(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "user",
                          "try+")

    @decorators.idempotent_id('bc62ce96-36fe-4c9b-b6b9-4d5a661c8035')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_create_access_rule_user_to_snapshot(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).create_access_rule,
                          self.snap["id"],
                          access_type="user",
                          access_to="fakeuser")

    @decorators.idempotent_id('04d5b25f-b335-4574-82b0-f607c8b3bf25')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_user_with_wrong_share_id(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).create_access_rule,
                          "wrong_share_id",
                          access_type="user",
                          access_to="fakeuser")

    @decorators.idempotent_id('301bdbd5-4398-4320-b334-7370995369e9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_with_wrong_level(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"],
                          'user',
                          CONF.share.username_for_user_rules,
                          'su')


@ddt.ddt
class ShareUserRulesForCIFSNegativeTest(ShareUserRulesForNFSNegativeTest):
    protocol = "cifs"


@ddt.ddt
class ShareCertRulesForGLUSTERFSNegativeTest(base.BaseSharesMixedTest):
    protocol = "glusterfs"

    @classmethod
    def resource_setup(cls):
        super(ShareCertRulesForGLUSTERFSNegativeTest, cls).resource_setup()
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_cert_rules_for_protocols):
            msg = "CERT rule tests for %s protocol are disabled" % cls.protocol
            raise cls.skipException(msg)
        # create share type
        extra_specs = None
        if CONF.share.run_snapshot_tests:
            extra_specs = {'snapshot_support': True}
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        if CONF.share.run_snapshot_tests:
            # create snapshot
            cls.snap = cls.create_snapshot_wait_for_active(cls.share["id"])

    @decorators.idempotent_id('a16d53d5-50d4-4015-912f-2850c5d62690')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_cert_with_empty_common_name(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "cert", "")

    @decorators.idempotent_id('7b5383d8-5bcd-47aa-955b-ed3757a5bdb4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_cert_with_whitespace_common_name(self,
                                                                 client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "cert", " ")

    @decorators.idempotent_id('1c25c134-92b4-4875-a061-88d394e28bcc')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_cert_with_too_big_common_name(self,
                                                              client_name):
        # common name cannot be more than 64 characters long
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "cert", "a" * 65)

    @decorators.idempotent_id('dd85d5cd-aa83-4f44-8572-bd7e68a84fb2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_cert_to_snapshot(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).create_access_rule,
                          self.snap["id"],
                          access_type="cert",
                          access_to="fakeclient1.com")

    @decorators.idempotent_id('eb47a511-7688-4689-a2ad-54ba85b39b07')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_cert_with_wrong_share_id(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).create_access_rule,
                          "wrong_share_id",
                          access_type="cert",
                          access_to="fakeclient2.com")


@ddt.ddt
class ShareCephxRulesForCephFSNegativeTest(base.BaseSharesMixedTest):
    protocol = "cephfs"

    @classmethod
    def resource_setup(cls):
        super(ShareCephxRulesForCephFSNegativeTest, cls).resource_setup()
        if not (cls.protocol in CONF.share.enable_protocols and
                cls.protocol in CONF.share.enable_cephx_rules_for_protocols):
            msg = ("CEPHX rule tests for %s protocol are disabled" %
                   cls.protocol)
            raise cls.skipException(msg)
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        cls.access_type = "cephx"
        cls.access_to = "david"

    @decorators.idempotent_id('7b33c073-353e-4952-97dc-c3948a3cd037')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('jane.doe', u"bj\u00F6rn")
    def test_create_access_rule_cephx_with_invalid_cephx_id(self, access_to):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_access_rule,
                          self.share["id"], self.access_type, access_to)

    @decorators.idempotent_id('16b7d848-2f7c-4709-85a3-2dfb4576cc59')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_access_rule_cephx_admin_user(self):
        """CVE-2020-27781 - using admin in cephx rule must be disallowed"""

        self.assertRaises(share_exceptions.AccessRuleBuildErrorException,
                          self.allow_access,
                          self.share["id"],
                          access_type=self.access_type,
                          access_to='admin')

    @decorators.idempotent_id('dd8be44c-c7e8-42fe-b81c-095a1c66730c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_access_rule_cephx_with_wrong_level(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.create_access_rule,
                          self.share["id"], self.access_type, self.access_to,
                          access_level="su")

    @decorators.idempotent_id('4ffed391-d7cc-481b-bb74-9f3406ddd75f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_different_tenants_cannot_use_same_cephx_id(self):
        # Grant access to the share
        self.allow_access(self.share['id'], access_to=self.access_to)

        # Create second share by the new user
        share2 = self.create_share(client=self.alt_shares_v2_client,
                                   share_protocol=self.protocol,
                                   share_type_id=self.share_type_id)

        # Try grant access to the second share using the same cephx id as used
        # on the first share.
        # Rule must be set to "error" status.
        self.allow_access(share2['id'], client=self.alt_shares_v2_client,
                          access_to=self.access_to, status='error',
                          raise_rule_in_error_state=False)

        share_alt_updated = self.alt_shares_v2_client.get_share(
            share2['id'])['share']
        self.assertEqual('error', share_alt_updated['access_rules_status'])

    @decorators.idempotent_id('1a9f46f0-d4e1-40ac-8726-aedd0320d583')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_can_apply_new_cephx_rules_when_one_is_in_error_state(self):
        # Create share on "primary" tenant
        share_primary = self.create_share()
        # Add access rule to "Joe" by "primary" user
        self.allow_access(share_primary['id'], access_to='Joe')

        # Create share on "alt" tenant
        share_alt = self.create_share(client=self.alt_shares_v2_client)
        # Add access rule to "Joe" by "alt" user.
        # Rule must be set to "error" status.
        rule1 = self.allow_access(share_alt['id'],
                                  client=self.alt_shares_v2_client,
                                  access_to='Joe',
                                  status='error',
                                  raise_rule_in_error_state=False,
                                  cleanup=False)

        # Share's "access_rules_status" must be in "error" status
        share_alt_updated = self.alt_shares_v2_client.get_share(
            share_alt['id'])['share']
        self.assertEqual('error', share_alt_updated['access_rules_status'])

        # Add second access rule to different client by "alt" user.
        self.allow_access(share_alt['id'], client=self.alt_shares_v2_client)

        # Check share's access_rules_status has transitioned to "active" status
        self.alt_shares_v2_client.delete_access_rule(
            share_alt['id'], rule1['id'])
        waiters.wait_for_resource_status(
            self.alt_shares_v2_client, share_alt['id'], 'active',
            status_attr='access_rules_status')


@ddt.ddt
class ShareRulesNegativeTest(base.BaseSharesMixedTest):
    # Tests independent from rule type and share protocol

    @classmethod
    def skip_checks(cls):
        super(ShareRulesNegativeTest, cls).skip_checks()
        if not (any(p in CONF.share.enable_ip_rules_for_protocols
                    for p in cls.protocols) or
                any(p in CONF.share.enable_user_rules_for_protocols
                    for p in cls.protocols) or
                any(p in CONF.share.enable_cert_rules_for_protocols
                    for p in cls.protocols) or
                any(p in CONF.share.enable_cephx_rules_for_protocols
                    for p in cls.protocols)):
            cls.message = "Rule tests are disabled"
            raise cls.skipException(cls.message)

    @classmethod
    def resource_setup(cls):
        super(ShareRulesNegativeTest, cls).resource_setup()
        # create share type
        extra_specs = None
        if CONF.share.run_snapshot_tests:
            extra_specs = {'snapshot_support': True}
        cls.share_type = cls.create_share_type(extra_specs=extra_specs)
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)
        if CONF.share.run_snapshot_tests:
            # create snapshot
            cls.snap = cls.create_snapshot_wait_for_active(cls.share["id"])

    @decorators.idempotent_id('84da9231-5c4b-4615-8500-8fc6d30ff7ea')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_delete_access_rule_with_wrong_id(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).delete_access_rule,
                          self.share["id"], "wrong_rule_id")

    @decorators.idempotent_id('13f9329f-12db-467d-9268-a9cca75997d9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_ip_with_wrong_type(self, client_name):
        self.assertRaises(lib_exc.BadRequest,
                          getattr(self, client_name).create_access_rule,
                          self.share["id"], "wrong_type", "1.2.3.4")

    @decorators.idempotent_id('fd6ede10-97d6-4ee8-a661-c516b7421c91')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data('shares_client', 'shares_v2_client')
    @testtools.skipUnless(CONF.share.run_snapshot_tests,
                          "Snapshot tests are disabled.")
    def test_create_access_rule_ip_to_snapshot(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).create_access_rule,
                          self.snap["id"])


@ddt.ddt
class ShareRulesAPIOnlyNegativeTest(base.BaseSharesTest):

    @decorators.idempotent_id('01279461-3ccc-49b2-a615-d7984dd0db8c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    @ddt.data('shares_client', 'shares_v2_client')
    def test_create_access_rule_ip_with_wrong_share_id(self, client_name):
        self.assertRaises(lib_exc.NotFound,
                          getattr(self, client_name).create_access_rule,
                          "wrong_share_id")
