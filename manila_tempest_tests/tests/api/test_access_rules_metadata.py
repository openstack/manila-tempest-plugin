# Copyright 2018 Huawei Inc.
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
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class AccessRulesMetadataTest(base.BaseSharesMixedTest):
    """A Test class to test access rule metadata generically.

    Tests in this class don't care about the type of access rule or the
    protocol of the share created. They are meant to test the API semantics
    of the access rule metadata APIs.
    """

    @classmethod
    def skip_checks(cls):
        super(AccessRulesMetadataTest, cls).skip_checks()
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

        utils.check_skip_if_microversion_lt(
            constants.MIN_SHARE_ACCESS_METADATA_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(AccessRulesMetadataTest, cls).resource_setup()
        cls.protocol = cls.shares_v2_client.share_protocol
        cls.access_type, __ = cls._get_access_rule_data_from_config()
        int_range = range(20, 50)
        cls.access_to = {
            # list of unique values is required for ability to create lots
            # of access rules for one share using different API microversions.
            'ip': set([utils.rand_ipv6_ip() for i in int_range]),
            # following users are fakes and access rules that use it are
            # expected to fail, but they are used only for API testing.
            'user': ['foo_user_%d' % i for i in int_range],
            'cert': ['tenant_%d.example.com' % i for i in int_range],
            'cephx': ['eve%d' % i for i in int_range],
        }
        # create share type
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)
        cls.md1 = {"key1": "value1", "key2": "value2"}
        cls.access = cls.shares_v2_client.create_access_rule(
            cls.share["id"], cls.access_type,
            cls.access_to[cls.access_type].pop(), 'rw', metadata=cls.md1)

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_get_delete_access_metadata(self):
        data = {"key1": "v" * 255, "k" * 255: "value2"}
        # set metadata
        access = self.shares_v2_client.create_access_rule(
            self.share["id"], self.access_type,
            self.access_to[self.access_type].pop(), 'rw', metadata=data)

        # read metadata
        get_access = self.shares_v2_client.get_access(access["id"])

        # verify metadata
        self.assertEqual(data, get_access['metadata'])

        # delete metadata
        for key in data.keys():
            self.shares_v2_client.delete_access_metadata(access["id"], key)

        # verify deletion of metadata
        access_without_md = self.shares_v2_client.get_access(access["id"])
        self.assertEqual({}, access_without_md['metadata'])
        self.shares_v2_client.delete_access_rule(self.share["id"],
                                                 access["id"])
        self.shares_v2_client.wait_for_resource_deletion(
            rule_id=access["id"], share_id=self.share["id"])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_update_metadata_by_key(self):
        md2 = {"key7": "value7", "key2": "value6_new"}

        # update metadata
        self.shares_v2_client.update_access_metadata(
            access_id=self.access['id'], metadata=md2)
        # get metadata
        get_access = self.shares_v2_client.get_access(self.access['id'])

        # verify metadata
        self.md1.update(md2)
        self.assertEqual(self.md1, get_access['metadata'])

    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_access_filter_by_metadata(self):
        data = {"key3": "v3", "key4": "value4"}
        # set metadata
        access = self.shares_v2_client.create_access_rule(
            self.share["id"], self.access_type,
            self.access_to[self.access_type].pop(), 'rw', metadata=data)

        # list metadata with metadata filter
        list_access = self.shares_v2_client.list_access_rules(
            share_id=self.share["id"], metadata={'metadata': data})

        # verify metadata
        self.assertEqual(1, len(list_access))
        self.assertEqual(access['metadata'], list_access[0]['metadata'])
        self.assertEqual(access['id'], list_access[0]['id'])
