# Copyright 2022 Red Hat Inc.
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

from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base

CONF = config.CONF


class ShareRbacServicesTests(rbac_base.ShareRbacBaseTests,
                             metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacServicesTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()

    def test_list_services(self):
        pass


class TestProjectAdminTests(ShareRbacServicesTests, base.BaseSharesTest):
    credentials = ['project_admin']

    @decorators.idempotent_id('08ec3a0b-6e4a-4cbf-bd15-3f48f8ddf71f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_services(self):
        self.do_request('list_services', expected_status=200)


class TestProjectMemberTests(ShareRbacServicesTests, base.BaseSharesTest):
    credentials = ['project_member']

    @decorators.idempotent_id('7431dca6-9b03-48d3-b97c-41f72f7ed0a3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_services(self):
        self.do_request('list_services', expected_status=lib_exc.Forbidden)


class TestProjectReaderTests(TestProjectMemberTests):
    credentials = ['project_reader']

    @decorators.idempotent_id('eca71619-d563-4d15-9e49-b661e6da46c0')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_services(self):
        super(TestProjectReaderTests, self).test_list_services()
