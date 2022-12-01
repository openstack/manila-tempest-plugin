# Copyright 2022 Red Hat, Inc.
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

import abc

from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base


class ShareRbacAvailabilityZonesTests(rbac_base.ShareRbacBaseTests,
                                      metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacAvailabilityZonesTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()

    @abc.abstractmethod
    def test_list_availability_zones(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacAvailabilityZonesTests,
                               base.BaseSharesTest):

    credentials = ['project_admin']

    @decorators.idempotent_id('87d9bb1c-f4de-40e5-8f25-05a6e1055c0b')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_availability_zones(self):
        self.do_request('list_availability_zones', expected_status=200)


class TestProjectMemberTestsNFS(ShareRbacAvailabilityZonesTests,
                                base.BaseSharesTest):

    credentials = ['project_member']

    @decorators.idempotent_id('ee2db349-176a-47bc-a20d-5ba9b5f8a813')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_availability_zones(self):
        self.do_request('list_availability_zones', expected_status=200)


class TestProjectReaderTestsNFS(ShareRbacAvailabilityZonesTests,
                                base.BaseSharesTest):

    credentials = ['project_reader']

    @decorators.idempotent_id('a095fac8-ae62-4be7-8a3e-b0fc1bc71348')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_availability_zones(self):
        self.do_request('list_availability_zones', expected_status=200)
