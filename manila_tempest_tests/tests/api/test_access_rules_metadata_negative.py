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
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF


@ddt.ddt
class AccessesMetadataNegativeTest(base.BaseSharesMixedTest):
    """A Test class with generic negative access rule metadata tests.

    Tests in this class don't care about the type of access rule or the
    protocol of the share created. They are meant to test the API semantics
    of the access rule metadata APIs.
    """

    @classmethod
    def skip_checks(cls):
        super(AccessesMetadataNegativeTest, cls).skip_checks()
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
        super(AccessesMetadataNegativeTest, cls).resource_setup()
        cls.protocol = cls.shares_v2_client.share_protocol
        cls.access_type, cls.access_to = (
            cls._get_access_rule_data_from_config()
        )
        # create share type
        cls.share_type = cls._create_share_type()
        cls.share_type_id = cls.share_type['id']
        # create share
        cls.share = cls.create_share(share_type_id=cls.share_type_id)
        cls.access = cls.shares_v2_client.create_access_rule(
            cls.share["id"], cls.access_type, cls.access_to,
            'rw', metadata={u"key1": u"value1"})

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @ddt.data({'data': {"": "value"}}, {'data': {"k" * 256: "value"}},
              {'data': {"key": "x" * 1024}})
    @ddt.unpack
    def test_try_upd_access_metadata_error(self, data):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_v2_client.update_access_metadata,
                          self.access["id"], data)

    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_try_delete_unexisting_access_metadata(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_access_metadata,
                          self.access["id"], "wrong_key")
