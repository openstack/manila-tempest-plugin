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

import itertools

import ddt
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF
LATEST_MICROVERSION = CONF.share.max_api_microversion


def _create_delete_ro_access_rule(self, version):
    """Common test case for usage in test suites with different decorators.

    :param self: instance of test class
    """

    if utils.is_microversion_le(version, '2.9'):
        client = self.shares_client
    else:
        client = self.shares_v2_client

    rule = self.allow_access(
        self.share["id"], client=client, access_type=self.access_type,
        access_to=self.access_to, access_level='ro', version=version)

    self.assertEqual('ro', rule['access_level'])
    for key in ('deleted', 'deleted_at', 'instance_mappings'):
        self.assertNotIn(key, rule.keys())

    # rules must start out in 'new' until 2.28 & 'queued_to_apply' after 2.28
    if utils.is_microversion_le(version, "2.27"):
        self.assertEqual("new", rule['state'])
    else:
        self.assertEqual("queued_to_apply", rule['state'])

        # If the 'access_rules_status' transitions to 'active',
        # rule state must too
        rules = self.shares_v2_client.list_access_rules(
            self.share['id'])['access_list']
        rule = [r for r in rules if r['id'] == rule['id']][0]
        self.assertEqual("active", rule['state'])


@ddt.ddt
class ShareIpRulesForNFSTest(base.BaseSharesMixedTest):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareIpRulesForNFSTest, cls).skip_checks()
        if (cls.protocol not in CONF.share.enable_protocols or
                cls.protocol not in CONF.share.enable_ip_rules_for_protocols):
            msg = "IP rule tests for %s protocol are disabled" % cls.protocol
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(ShareIpRulesForNFSTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)
        cls.access_type = "ip"
        cls.access_to = "2.2.2.2"

    @decorators.idempotent_id('3390df2d-f6f8-4634-a562-87c1be994f6a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(*itertools.chain(
        itertools.product(
            utils.deduplicate(['1.0', '2.9', '2.37', LATEST_MICROVERSION]),
            [4]),
        itertools.product(
            utils.deduplicate(['2.38', LATEST_MICROVERSION]), [6])
    ))
    @ddt.unpack
    def test_create_delete_access_rules_with_one_ip(self, version,
                                                    ip_version):

        if ip_version == 4:
            access_to = utils.rand_ip()
        else:
            access_to = utils.rand_ipv6_ip()

        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client

        # create rule
        rule = self.allow_access(
            self.share["id"], client=client, access_type=self.access_type,
            access_to=access_to, version=version)

        self.assertEqual('rw', rule['access_level'])
        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, rule.keys())

        # rules must start out in 'new' until 2.28 & 'queued_to_apply' after
        if utils.is_microversion_le(version, "2.27"):
            self.assertEqual("new", rule['state'])
        else:
            self.assertEqual("queued_to_apply", rule['state'])

    @decorators.idempotent_id('5d25168a-d646-443e-8cf1-3151eb7887f5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(*itertools.chain(
        itertools.product(
            utils.deduplicate(['1.0', '2.9', '2.37', LATEST_MICROVERSION]),
            [4]),
        itertools.product(
            utils.deduplicate(['2.38', LATEST_MICROVERSION]), [6])
    ))
    @ddt.unpack
    def test_create_delete_access_rule_with_cidr(self, version, ip_version):
        if ip_version == 4:
            access_to = utils.rand_ip(network=True)
        else:
            access_to = utils.rand_ipv6_ip(network=True)
        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client
        # create rule
        rule = self.allow_access(
            self.share["id"], client=client, access_type=self.access_type,
            access_to=access_to, version=version)

        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, rule.keys())
        self.assertEqual('rw', rule['access_level'])

    @decorators.idempotent_id('187a4fb0-ba1d-45b9-83c9-f0272e7e6f3e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        "nfs" not in CONF.share.enable_ro_access_level_for_protocols,
        "RO access rule tests are disabled for NFS protocol.")
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_ro_access_rule(self, client_name):
        _create_delete_ro_access_rule(self, client_name)


@ddt.ddt
class ShareIpRulesForCIFSTest(ShareIpRulesForNFSTest):
    protocol = "cifs"

    @decorators.idempotent_id('8fa0a15f-c04c-4521-91e7-020943bede8a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        "cifs" not in CONF.share.enable_ro_access_level_for_protocols,
        "RO access rule tests are disabled for CIFS protocol.")
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_ro_access_rule(self, version):
        _create_delete_ro_access_rule(self, version)


@ddt.ddt
class ShareUserRulesForNFSTest(base.BaseSharesMixedTest):
    protocol = "nfs"

    @classmethod
    def skip_checks(cls):
        super(ShareUserRulesForNFSTest, cls).skip_checks()
        if (cls.protocol not in CONF.share.enable_protocols or
                cls.protocol not in
                CONF.share.enable_user_rules_for_protocols):
            msg = "USER rule tests for %s protocol are disabled" % cls.protocol
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(ShareUserRulesForNFSTest, cls).resource_setup()

        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)

        cls.access_type = "user"
        cls.access_to = CONF.share.username_for_user_rules

    @decorators.idempotent_id('1f87565f-c3d9-448d-b89a-387d6c2fdae6')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_user_rule(self, version):
        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client

        # create rule
        rule = self.allow_access(
            self.share["id"], client=client, access_type=self.access_type,
            access_to=self.access_to, version=version)

        self.assertEqual('rw', rule['access_level'])
        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, rule.keys())

        # rules must start out in 'new' until 2.28 & 'queued_to_apply' after
        if utils.is_microversion_le(version, "2.27"):
            self.assertEqual("new", rule['state'])
        else:
            self.assertEqual("queued_to_apply", rule['state'])

    @decorators.idempotent_id('ccb08342-b7ef-4dda-84ba-8de9879d8862')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        "nfs" not in CONF.share.enable_ro_access_level_for_protocols,
        "RO access rule tests are disabled for NFS protocol.")
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_ro_access_rule(self, version):
        _create_delete_ro_access_rule(self, version)


@ddt.ddt
class ShareUserRulesForCIFSTest(ShareUserRulesForNFSTest):
    protocol = "cifs"

    @decorators.idempotent_id('ee11084d-6c1d-4856-8044-9aa9e6c670fb')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        "cifs" not in CONF.share.enable_ro_access_level_for_protocols,
        "RO access rule tests are disabled for CIFS protocol.")
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_ro_access_rule(self, version):
        _create_delete_ro_access_rule(self, version)


@ddt.ddt
class ShareCertRulesForGLUSTERFSTest(base.BaseSharesMixedTest):
    protocol = "glusterfs"

    @classmethod
    def skip_checks(cls):
        super(ShareCertRulesForGLUSTERFSTest, cls).skip_checks()
        if (cls.protocol not in CONF.share.enable_protocols or
                cls.protocol not in
                CONF.share.enable_cert_rules_for_protocols):
            msg = "Cert rule tests for %s protocol are disabled" % cls.protocol
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(ShareCertRulesForGLUSTERFSTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)

        cls.access_type = "cert"
        # Provide access to a client identified by a common name (CN) of the
        # certificate that it possesses.
        cls.access_to = "client1.com"

    @decorators.idempotent_id('775ebc55-4a4d-4012-a030-2eeb7b6d2ce8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_cert_rule(self, version):
        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client

        # create rule
        rule = self.allow_access(
            self.share["id"], client=client, access_type=self.access_type,
            access_to=self.access_to, version=version)

        self.assertEqual('rw', rule['access_level'])
        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, rule.keys())

        # rules must start out in 'new' until 2.28 & 'queued_to_apply' after
        if utils.is_microversion_le(version, "2.27"):
            self.assertEqual("new", rule['state'])
        else:
            self.assertEqual("queued_to_apply", rule['state'])

    @decorators.idempotent_id('cdd93d8e-7255-4ed4-8ef0-929a62bb302c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @testtools.skipIf(
        "glusterfs" not in CONF.share.enable_ro_access_level_for_protocols,
        "RO access rule tests are disabled for GLUSTERFS protocol.")
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_create_delete_cert_ro_access_rule(self, version):
        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client
        rule = self.allow_access(
            self.share["id"], client=client, access_type='cert',
            access_to='client2.com', access_level='ro', version=version)

        self.assertEqual('ro', rule['access_level'])
        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, rule.keys())

        # rules must start out in 'new' until 2.28 & 'queued_to_apply' after
        if utils.is_microversion_le(version, "2.27"):
            self.assertEqual("new", rule['state'])
        else:
            self.assertEqual("queued_to_apply", rule['state'])


@ddt.ddt
class ShareCephxRulesForCephFSTest(base.BaseSharesMixedTest):
    protocol = "cephfs"

    @classmethod
    def skip_checks(cls):
        super(ShareCephxRulesForCephFSTest, cls).skip_checks()
        if (cls.protocol not in CONF.share.enable_protocols or
                cls.protocol not in
                CONF.share.enable_cephx_rules_for_protocols):
            msg = ("Cephx rule tests for %s protocol are disabled." %
                   cls.protocol)
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(ShareCephxRulesForCephFSTest, cls).resource_setup()
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

        # create share
        cls.share = cls.create_share(cls.protocol,
                                     share_type_id=cls.share_type_id)

        cls.access_type = "cephx"
        # Provide access to a client identified by a cephx auth id.
        cls.access_to = "bob"

    @decorators.idempotent_id('4e636fd2-26ef-4b63-96eb-77860a8b6cdf')
    @tc.attr(base.TAG_POSITIVE, base.TAG_BACKEND)
    @ddt.data(*itertools.product(
        utils.deduplicate(['2.13', '2.27', '2.28', LATEST_MICROVERSION]),
        ("alice", "alice_bob", "alice bob"),
        ('rw', 'ro')))
    @ddt.unpack
    def test_create_delete_cephx_rule(self, version, access_to, access_level):
        rule = self.allow_access(
            self.share["id"], access_type=self.access_type,
            access_to=access_to, version=version, access_level=access_level)

        self.assertEqual(access_level, rule['access_level'])
        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            self.assertNotIn(key, rule.keys())

    @decorators.idempotent_id('ad907303-a439-4fcb-8845-fe91ecab7dc2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_different_users_in_same_tenant_can_use_same_cephx_id(self):
        # Grant access to the share
        self.allow_access(
            self.share['id'], access_type=self.access_type,
            access_to=self.access_to, access_level='rw')

        # Create a new user in the current project
        project = self.os_admin.projects_client.show_project(
            self.shares_v2_client.tenant_id)['project']
        user_client = self.create_user_and_get_client(project)

        # Create second share by the new user
        share2 = self.create_share(client=user_client.shares_v2_client,
                                   share_protocol=self.protocol,
                                   share_type_id=self.share_type_id)

        # Grant access to the second share using the same cephx ID that was
        # used in access1
        self.allow_access(
            share2['id'], client=user_client.shares_v2_client,
            access_type=self.access_type, access_to=self.access_to,
            access_level='rw')


@ddt.ddt
class ShareRulesTest(base.BaseSharesMixedTest):
    """A Test class to test access rules generically.

    Tests in this class don't care about the type of access rule or the
    protocol of the share created. They are meant to test the API semantics
    of the access rules APIs.
    """

    @classmethod
    def skip_checks(cls):
        super(ShareRulesTest, cls).skip_checks()
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
        super(ShareRulesTest, cls).resource_setup()
        cls.protocol = cls.shares_v2_client.share_protocol
        cls.access_type, cls.access_to = (
            cls._get_access_rule_data_from_config()
        )
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']
        cls.share = cls.create_share(share_type_id=cls.share_type_id)

    @decorators.idempotent_id('c52e95cc-d6ea-4d02-9b52-cd7c1913dfff')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(*utils.deduplicate(
        ['1.0', '2.9', '2.27', '2.28', '2.45', LATEST_MICROVERSION]))
    def test_list_access_rules(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        if (utils.is_microversion_lt(version, '2.13') and
                CONF.share.enable_cephx_rules_for_protocols):
            msg = ("API version %s does not support cephx access type, need "
                   "version >= 2.13." % version)
            raise self.skipException(msg)

        metadata = None
        if utils.is_microversion_ge(version, '2.45'):
            metadata = {'key1': 'v1', 'key2': 'v2'}
        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client
        # create rule
        rule = self.allow_access(
            self.share["id"], client=client, access_type=self.access_type,
            access_to=self.access_to, metadata=metadata, version=version)

        # verify added rule keys since 2.33 when create rule
        if utils.is_microversion_ge(version, '2.33'):
            self.assertIn('created_at', list(rule.keys()))
            self.assertIn('updated_at', list(rule.keys()))
        else:
            self.assertNotIn('created_at', list(rule.keys()))
            self.assertNotIn('updated_at', list(rule.keys()))

        # rules must start out in 'new' until 2.28 & 'queued_to_apply' after
        if utils.is_microversion_le(version, "2.27"):
            self.assertEqual("new", rule['state'])
        else:
            self.assertEqual("queued_to_apply", rule['state'])

        # list rules
        if utils.is_microversion_eq(version, '1.0'):
            rules = self.shares_client.list_access_rules(
                self.share["id"])['access_list']
        else:
            rules = self.shares_v2_client.list_access_rules(
                self.share["id"], version=version)['access_list']

        # verify keys
        keys = ("id", "access_type", "access_to", "access_level")
        if utils.is_microversion_ge(version, '2.21'):
            keys += ("access_key", )
        if utils.is_microversion_ge(version, '2.33'):
            keys += ("created_at", "updated_at", )
        if utils.is_microversion_ge(version, '2.45'):
            keys += ("metadata",)
        for key in keys:
            [self.assertIn(key, r.keys()) for r in rules]
        for key in ('deleted', 'deleted_at', 'instance_mappings'):
            [self.assertNotIn(key, r.keys()) for r in rules]

        # verify values
        self.assertEqual(self.access_type, rules[0]["access_type"])
        self.assertEqual(self.access_to, rules[0]["access_to"])
        self.assertEqual('rw', rules[0]["access_level"])
        if utils.is_microversion_ge(version, '2.21'):
            if self.access_type == 'cephx':
                self.assertIsNotNone(rules[0]['access_key'])
            else:
                self.assertIsNone(rules[0]['access_key'])

        # our share id in list and have no duplicates
        gen = [r["id"] for r in rules if r["id"] in rule["id"]]
        msg = "expected id lists %s times in rule list" % (len(gen))
        self.assertEqual(1, len(gen), msg)

    @decorators.idempotent_id('b77bcbda-9754-48f0-9be6-79341ad1af64')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data(*utils.deduplicate(['1.0', '2.9', '2.27', '2.28',
                                 LATEST_MICROVERSION]))
    def test_access_rules_deleted_if_share_deleted(self, version):
        if (utils.is_microversion_lt(version, '2.13') and
                CONF.share.enable_cephx_rules_for_protocols):
            msg = ("API version %s does not support cephx access type, need "
                   "version >= 2.13." % version)
            raise self.skipException(msg)
        if utils.is_microversion_le(version, '2.9'):
            client = self.shares_client
        else:
            client = self.shares_v2_client

        # create share
        share = self.create_share(share_type_id=self.share_type_id)

        # create rule
        rule = self.allow_access(
            share["id"], client=client, access_type=self.access_type,
            access_to=self.access_to, version=version, cleanup=False)

        # rules must start out in 'new' until 2.28 & 'queued_to_apply' after
        if utils.is_microversion_le(version, "2.27"):
            self.assertEqual("new", rule['state'])
        else:
            self.assertEqual("queued_to_apply", rule['state'])

        # delete share
        if utils.is_microversion_eq(version, '1.0'):
            self.shares_client.delete_share(share['id'])
            self.shares_client.wait_for_resource_deletion(share_id=share['id'])
        else:
            self.shares_v2_client.delete_share(share['id'], version=version)
            self.shares_v2_client.wait_for_resource_deletion(
                share_id=share['id'], version=version)

        # verify absence of rules for nonexistent share id
        if utils.is_microversion_eq(version, '1.0'):
            self.assertRaises(lib_exc.NotFound,
                              self.shares_client.list_access_rules,
                              share['id'])
        elif utils.is_microversion_lt(version, '2.45'):
            self.assertRaises(lib_exc.NotFound,
                              self.shares_v2_client.list_access_rules,
                              share['id'], version)
        else:
            self.assertRaises(lib_exc.BadRequest,
                              self.shares_v2_client.list_access_rules,
                              share['id'], version)
