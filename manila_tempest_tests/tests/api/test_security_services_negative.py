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

from oslo_log import log
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
import testtools
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF
LOG = log.getLogger(__name__)


class SecurityServicesNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SecurityServicesNegativeTest, cls).resource_setup()
        # create share_type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

    @decorators.idempotent_id('f5cdf074-f5d4-4d9e-990b-c3d9385dfc2b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_security_service_with_empty_type(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_security_service, "")

    @decorators.idempotent_id('6a7efebc-989a-42b3-a971-c28af1e209f5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_create_security_service_with_wrong_type(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.shares_client.create_security_service,
                          "wrong_type")

    @decorators.idempotent_id('2935de41-40b1-4907-8ab5-f4921f670bfd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_security_service_without_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_security_service, "")

    @decorators.idempotent_id('34e923a4-e5b4-4375-88b4-8bb05e8f010d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_get_security_service_with_wrong_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_security_service,
                          "wrong_id")

    @decorators.idempotent_id('887e0c2c-6658-442d-92e7-3b0c86a2dfcd')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_security_service_without_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_security_service, "")

    @decorators.idempotent_id('c94eb229-5caf-4e81-b8a9-d73c0b63a93b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_security_service_with_wrong_type(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.delete_security_service,
                          "wrong_id")

    @decorators.idempotent_id('60e51b95-af7f-463d-8d8e-6bca4ed3bec8')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_nonexistant_security_service(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.update_security_service,
                          "wrong_id", name="name")

    @decorators.idempotent_id('e4554b3b-bc74-4204-8596-d502149bb408')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_update_security_service_with_empty_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.update_security_service,
                          "", name="name")

    @decorators.idempotent_id('ab62240a-219c-4fa7-b1ca-08f91bec76f0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_try_update_invalid_keys_sh_server_exists(self):
        ss_data = utils.generate_security_service_data()
        ss = self.create_security_service(**ss_data)

        sn = self.shares_client.get_share_network(
            self.shares_client.share_network_id)['share_network']
        fresh_sn = self.create_share_network(
            add_security_services=False,
            neutron_net_id=sn["neutron_net_id"],
            neutron_subnet_id=sn["neutron_subnet_id"])

        self.shares_client.add_sec_service_to_share_network(
            fresh_sn["id"], ss["id"])

        # Security service with fake data is used, so if we use backend driver
        # that fails on wrong data, we expect error here.
        # We require any share that uses our share-network.
        try:
            self.create_share(share_type_id=self.share_type_id,
                              share_network_id=fresh_sn["id"],
                              cleanup_in_class=False)
        except Exception as e:
            # we do wait for either 'error' or 'available' status because
            # it is the only available statuses for proper deletion.
            LOG.warning("Caught exception. It is expected in case backend "
                        "fails having security-service with improper data "
                        "that leads to share-server creation error. "
                        "%s", str(e))

        self.assertRaises(lib_exc.Forbidden,
                          self.shares_client.update_security_service,
                          ss["id"],
                          user="new_user")

    @decorators.idempotent_id('288dbf42-ee22-4445-8363-7ebb1c3d89c9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_get_deleted_security_service(self):
        data = utils.generate_security_service_data()
        ss = self.create_security_service(**data)
        self.assertLessEqual(data.items(), ss.items())

        self.shares_client.delete_security_service(ss["id"])

        # try get deleted security service entity
        self.assertRaises(lib_exc.NotFound,
                          self.shares_client.get_security_service,
                          ss["id"])
