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


class SecServicesMappingNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def resource_setup(cls):
        super(SecServicesMappingNegativeTest, cls).resource_setup()
        cls.sn = cls.create_share_network(cleanup_in_class=True,
                                          add_security_services=False)
        cls.share_net_info = (
            utils.share_network_get_default_subnet(cls.sn)
            if utils.share_network_subnets_are_supported() else cls.sn)
        cls.ss = cls.create_security_service(cleanup_in_class=True)
        cls.cl = cls.shares_client
        # create share type
        cls.share_type = cls.create_share_type()
        cls.share_type_id = cls.share_type['id']

    @decorators.idempotent_id('e3d17444-8ed4-445e-bc65-c748dbc5d21f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_sec_service_twice_to_share_network(self):
        self.cl.add_sec_service_to_share_network(self.sn["id"], self.ss["id"])
        self.assertRaises(lib_exc.Conflict,
                          self.cl.add_sec_service_to_share_network,
                          self.sn["id"], self.ss["id"])

    @decorators.idempotent_id('3f7af51f-3afa-495c-94b7-e9d29f06cf1d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_nonexistant_sec_service_to_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.add_sec_service_to_share_network,
                          self.sn["id"], "wrong_ss_id")

    @decorators.idempotent_id('85dd5693-a89c-4d05-9416-0e11fbba23f5')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_empty_sec_service_id_to_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.add_sec_service_to_share_network,
                          self.sn["id"], "")

    @decorators.idempotent_id('d9af5086-ace9-4be3-8119-e765699c0c91')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_sec_service_to_nonexistant_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.add_sec_service_to_share_network,
                          "wrong_sn_id", self.ss["id"])

    @decorators.idempotent_id('7272426d-ab58-4efb-a490-0c78c07fa7fe')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_sec_service_to_share_network_with_empty_id(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.add_sec_service_to_share_network,
                          "", self.ss["id"])

    @decorators.idempotent_id('f87aefa6-9681-477d-a118-603883849f4f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_sec_services_for_nonexistant_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.list_sec_services_for_share_network,
                          "wrong_id")

    @decorators.idempotent_id('7f8d7527-2d62-478a-ab19-213156777612')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_nonexistant_sec_service_from_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.remove_sec_service_from_share_network,
                          self.sn["id"], "wrong_id")

    @decorators.idempotent_id('be1c9c79-efa1-471e-920b-da4733ad383e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_sec_service_from_nonexistant_share_network(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.remove_sec_service_from_share_network,
                          "wrong_id", self.ss["id"])

    @decorators.idempotent_id('c7c2f66f-81f8-4984-b807-2b9520105a33')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_nonexistant_ss_from_nonexistant_sn(self):
        self.assertRaises(lib_exc.NotFound,
                          self.cl.remove_sec_service_from_share_network,
                          "wrong_id", "wrong_id")

    @decorators.idempotent_id('eb66a8f7-b549-4cf1-8719-30844fb151b6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    @testtools.skipIf(
        not CONF.share.multitenancy_enabled, "Only for multitenancy.")
    def test_delete_ss_from_sn_used_by_share_server(self):
        sn = self.shares_client.get_share_network(
            self.shares_client.share_network_id)['share_network']
        fresh_sn = self.create_share_network(
            add_security_services=False,
            neutron_net_id=sn["neutron_net_id"],
            neutron_subnet_id=sn["neutron_subnet_id"])

        self.shares_client.add_sec_service_to_share_network(
            fresh_sn["id"], self.ss["id"])

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
                          self.cl.remove_sec_service_from_share_network,
                          fresh_sn["id"],
                          self.ss["id"])

    @decorators.idempotent_id('6a15c8ff-eba3-40e5-8fa1-6eab52338672')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_map_two_ss_with_same_type_to_sn(self):
        # create share network
        data = utils.generate_share_network_data()

        sn = self.create_share_network(client=self.cl,
                                       add_security_services=False, **data)
        self.assertLessEqual(data.items(), sn.items())

        # create security services with same type
        security_services = []
        for i in range(2):
            data = utils.generate_security_service_data()
            ss = self.create_security_service(client=self.cl, **data)
            self.assertLessEqual(data.items(), ss.items())
            security_services.insert(i, ss)

        # Add security service to share network
        self.cl.add_sec_service_to_share_network(
            sn["id"], security_services[0]["id"])

        # Try to add security service with same type
        self.assertRaises(lib_exc.Conflict,
                          self.cl.add_sec_service_to_share_network,
                          sn["id"], security_services[1]["id"])

    @decorators.idempotent_id('d422a15a-1f4c-4531-a092-9216b90c4179')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_try_delete_ss_that_assigned_to_sn(self):
        # create share network
        data = utils.generate_share_network_data()

        sn = self.create_share_network(client=self.cl,
                                       add_security_services=False, **data)
        self.assertLessEqual(data.items(), sn.items())

        # create security service
        data = utils.generate_security_service_data()

        ss = self.create_security_service(client=self.cl, **data)
        self.assertLessEqual(data.items(), ss.items())

        # Add security service to share network
        self.cl.add_sec_service_to_share_network(sn["id"], ss["id"])

        # Try delete ss, that has been assigned to some sn
        self.assertRaises(lib_exc.Forbidden,
                          self.cl.delete_security_service,
                          ss["id"], )

        # remove seurity service from share-network
        self.cl.remove_sec_service_from_share_network(sn["id"], ss["id"])
