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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import waiters
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base

CONF = config.CONF


class ShareRbacSharesTests(rbac_base.ShareRbacBaseTests,
                           metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacSharesTests, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacSharesTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @classmethod
    def resource_setup(cls):
        super(ShareRbacSharesTests, cls).resource_setup()
        cls.share_type = cls.get_share_type()

    def share(self, share_type_id, size=None):
        share = {}
        share['name'] = data_utils.rand_name('share')
        share['size'] = size or CONF.share.share_size
        share['share_type_id'] = share_type_id
        share['share_protocol'] = self.protocol
        return share

    @abc.abstractmethod
    def test_get_share(self):
        pass

    @abc.abstractmethod
    def test_list_share(self):
        pass

    @abc.abstractmethod
    def test_create_share(self):
        pass

    @abc.abstractmethod
    def test_delete_share(self):
        pass

    @abc.abstractmethod
    def test_force_delete_share(self):
        pass

    @abc.abstractmethod
    def test_update_share(self):
        pass

    @abc.abstractmethod
    def test_reset_share(self):
        pass

    @abc.abstractmethod
    def test_shrink_share(self):
        pass

    @abc.abstractmethod
    def test_extend_share(self):
        pass

    @abc.abstractmethod
    def test_set_share_metadata(self):
        pass

    @abc.abstractmethod
    def test_get_share_metadata(self):
        pass

    @abc.abstractmethod
    def test_delete_share_metadata(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacSharesTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def setup_clients(cls):
        super(TestProjectAdminTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('14a52454-cba0-4973-926a-28e924ae2e63')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'get_share', expected_status=200, share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'get_share', expected_status=200,
            share_id=alt_share['id'])

    @decorators.idempotent_id('5f8c06e6-5b80-45f8-aefb-1b55617d1bd1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])

        params = {"all_tenants": 1}
        share_list = self.do_request(
            'list_shares', expected_status=200, params=params)['shares']
        share_id_list = [
            s['id'] for s in share_list
        ]

        self.assertIn(share['id'], share_id_list)
        self.assertIn(alt_share['id'], share_id_list)

    @decorators.idempotent_id('34b84af3-a9ea-4c19-8414-e4e44648099c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_share(self):
        share = self.do_request(
            'create_share', expected_status=200,
            **self.share(self.share_type['id']))['share']
        waiters.wait_for_resource_status(self.client,
                                         share['id'], 'available')
        self.addCleanup(self.delete_resource, self.client,
                        share_id=share['id'])

    @decorators.idempotent_id('44f2eae6-44d4-4962-a94a-d2717b74728f')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'delete_share', expected_status=202, share_id=share['id'])
        self.client.wait_for_resource_deletion(share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'delete_share', expected_status=202,
            share_id=alt_share['id'])
        self.client.wait_for_resource_deletion(share_id=alt_share['id'])

    @decorators.idempotent_id('2e915a27-488d-4e33-b2f8-37758ef11653')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'force_delete', expected_status=202, s_id=share['id'])
        self.client.wait_for_resource_deletion(share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'force_delete', expected_status=202,
            s_id=alt_share['id'])
        self.client.wait_for_resource_deletion(share_id=alt_share['id'])

    @decorators.idempotent_id('5c2bda4c-0179-4af9-b18c-430a7d31f962')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_update_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        name = data_utils.rand_name("updated_share")
        self.do_request(
            'update_share', expected_status=200,
            share_id=share['id'], name=name)

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        name = data_utils.rand_name("updated_share")
        self.do_request(
            'update_share', expected_status=200,
            share_id=alt_share['id'], name=name)

    @decorators.idempotent_id('44fb7049-8fc0-4584-9ff1-7527395d2ec5')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'reset_state', expected_status=202, s_id=share['id'],
            status="error")

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'reset_state', expected_status=202,
            s_id=alt_share['id'], status="error")

    @decorators.idempotent_id('cc49ae58-6696-4030-a029-a66bae2efa96')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_shrink_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'],
            size=CONF.share.share_size + 1)
        self.do_request(
            'shrink_share', expected_status=202, share_id=share['id'],
            new_size=CONF.share.share_size)
        waiters.wait_for_resource_status(self.client, share['id'], 'available')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            size=CONF.share.share_size + 1)
        self.do_request(
            'shrink_share', expected_status=202,
            share_id=alt_share['id'], new_size=CONF.share.share_size)
        waiters.wait_for_resource_status(
            self.alt_project_share_v2_client, alt_share['id'], 'available')

    @decorators.idempotent_id('2cfa04e5-16cc-43e4-b892-c1a11b0a2f2d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_extend_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'extend_share', expected_status=202, share_id=share['id'],
            new_size=CONF.share.share_size + 1)
        waiters.wait_for_resource_status(self.client, share['id'], 'available')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'extend_share', expected_status=202,
            share_id=alt_share['id'], new_size=CONF.share.share_size + 1)
        waiters.wait_for_resource_status(
            self.alt_project_share_v2_client, alt_share['id'], 'available')

    @decorators.idempotent_id('d6014579-d772-441a-a9b1-01b1e87caeaa')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_set_share_metadata(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'set_metadata', expected_status=200, resource_id=share['id'],
            metadata={'key': 'value'})

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'set_metadata', expected_status=200,
            resource_id=alt_share['id'], metadata={'key': 'value'})

    @decorators.idempotent_id('2d91e97e-d0e5-4112-8b22-60cd4659586c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_metadata(self):
        metadata = {'key': 'value'}
        share = self.create_share(
            self.share_member_client, self.share_type['id'],
            metadata=metadata)
        self.do_request(
            'get_metadata', expected_status=200, resource_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            metadata=metadata)
        self.do_request(
            'get_metadata', expected_status=200,
            resource_id=alt_share['id'])

    @decorators.idempotent_id('4cd807d6-bac4-4d0f-a207-c84dfe77f032')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share_metadata(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'],
            metadata={'key': 'value'})
        self.do_request(
            'delete_metadata', expected_status=200, resource_id=share['id'],
            key='key')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            metadata={'key': 'value'})
        self.do_request(
            'delete_metadata', expected_status=200,
            resource_id=alt_share['id'], key='key')


class TestProjectMemberTestsNFS(ShareRbacSharesTests, base.BaseSharesTest):

    credentials = ['project_member', 'project_alt_member']
    protocol = 'nfs'

    @decorators.idempotent_id('75b9fd40-ae63-4caf-9c93-0fe24b2ce904')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'])
        self.do_request(
            'get_share', expected_status=200, share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'get_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'])

    @decorators.idempotent_id('92fd157a-f357-4a08-9fc6-9e77a55b89a8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'])
        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])

        # We expect this key to be ignored since project_member isn't an admin
        params = {"all_tenants": 1}
        share_list = self.do_request(
            'list_shares', expected_status=200, params=params)['shares']
        share_id_list = [
            s['id'] for s in share_list
        ]

        self.assertIn(share['id'], share_id_list)
        self.assertNotIn(alt_share['id'], share_id_list)

    @decorators.idempotent_id('7a6eef6b-bf8e-4cb3-a39c-6dc7fbe115ab')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_share(self):
        share = self.do_request(
            'create_share', expected_status=200,
            **self.share(self.share_type['id']))['share']
        waiters.wait_for_resource_status(self.client,
                                         share['id'], 'available')
        self.addCleanup(self.client.wait_for_resource_deletion,
                        share_id=share['id'])
        self.addCleanup(self.client.delete_share, share['id'])

    @decorators.idempotent_id('6c546ed7-ebfd-4ac5-a626-d333a25a9e66')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share(self):
        share = self.create_share(self.client, self.share_type['id'])
        self.do_request(
            'delete_share', expected_status=202, share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'delete_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'])

    @decorators.idempotent_id('2349d2b0-6314-4018-85e5-696f8d1ca94a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_share(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'])
        self.do_request(
            'force_delete', expected_status=lib_exc.Forbidden,
            s_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'force_delete', expected_status=lib_exc.Forbidden,
            s_id=alt_share['id'])

    @decorators.idempotent_id('20d6360d-5cea-4305-be36-7e1429007598')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_share(self):
        share = self.create_share(self.client, self.share_type['id'])
        name = data_utils.rand_name("rename_share")
        self.do_request(
            'update_share', expected_status=200, share_id=share['id'],
            name=name)

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        alt_name = data_utils.rand_name("rename_share")
        self.do_request(
            'update_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'], name=alt_name)

    @decorators.idempotent_id('483cbaef-a53d-433a-9259-f2ecc209f405')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_share(self):
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'])
        self.do_request(
            'reset_state', expected_status=lib_exc.Forbidden,
            s_id=share['id'], status="error")

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'reset_state', expected_status=lib_exc.NotFound,
            s_id=alt_share['id'], status="error")

    @decorators.idempotent_id('56a07567-d0a9-460a-9267-fcd82306a371')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_shrink_share(self):
        share = self.create_share(self.client, self.share_type['id'], size=2)
        self.do_request(
            'shrink_share', expected_status=202,
            share_id=share['id'], new_size=CONF.share.share_size)
        waiters.wait_for_resource_status(self.client, share['id'], 'available')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'], size=2)
        self.do_request(
            'shrink_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'], new_size=CONF.share.share_size)

    @decorators.idempotent_id('c09e6a72-5b99-4be6-8ffe-8ecaad0be990')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_extend_share(self):
        share = self.create_share(self.client, self.share_type['id'])
        self.do_request(
            'extend_share', expected_status=202,
            share_id=share['id'], new_size=CONF.share.share_size + 1)
        waiters.wait_for_resource_status(self.client, share['id'], 'available')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'extend_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'], new_size=CONF.share.share_size + 1)

    @decorators.idempotent_id('f1c03630-987c-4f19-938d-4a0ef6529177')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_set_share_metadata(self):
        share = self.create_share(
            self.client, self.share_type['id'])
        self.do_request(
            'set_metadata', expected_status=200, resource_id=share['id'],
            metadata={'key': 'value'})

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'set_metadata', expected_status=lib_exc.Forbidden,
            resource_id=alt_share['id'], metadata={'key': 'value'})

    @decorators.idempotent_id('a69a2b85-3374-4621-83a9-89937ddb520b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_metadata(self):
        metadata = {'key': 'value'}
        share_client = getattr(self, 'share_member_client', self.client)
        share = self.create_share(share_client, self.share_type['id'],
                                  metadata=metadata)
        self.do_request(
            'get_metadata', expected_status=200, resource_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            metadata=metadata)
        self.do_request(
            'get_metadata', expected_status=lib_exc.Forbidden,
            resource_id=alt_share['id'])

    @decorators.idempotent_id('bea5518a-338e-494d-9034-1d03658ed58b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share_metadata(self):
        share = self.create_share(
            self.client, self.share_type['id'], metadata={'key': 'value'})
        self.do_request(
            'delete_metadata', expected_status=200, resource_id=share['id'],
            key='key')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            metadata={'key': 'value'})
        self.do_request(
            'delete_metadata', expected_status=lib_exc.Forbidden,
            resource_id=alt_share['id'], key='key')


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for basic share operations by reader user

    In order to test certain share operations we must create a share resource
    for this. Since reader user is limited in resources creation, we are forced
    to use admin credentials, so we can test other share operations.
    In this class we use admin user to create a member user within reader
    project. That way we can perform a reader actions on this resource.
    """

    credentials = ['project_reader', 'project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(TestProjectReaderTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @decorators.idempotent_id('dc439eaf-c885-4002-be8f-4c488beeca81')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share(self):
        super(TestProjectReaderTestsNFS, self).test_get_share()

    @decorators.idempotent_id('1fbb1078-4386-4b52-aa88-e6be4a286791')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_share(self):
        super(TestProjectReaderTestsNFS, self).test_list_share()

    @decorators.idempotent_id('350ba4c9-def9-4865-824a-de1ddff5dcf9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_share(self):
        self.do_request(
            'create_share', expected_status=lib_exc.Forbidden,
            **self.share(self.share_type['id']))

    @decorators.idempotent_id('eb92b142-fd8d-47e3-99fe-944cce747ad7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'delete_share', expected_status=lib_exc.Forbidden,
            share_id=share['id'])

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'delete_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'])

    @decorators.idempotent_id('cb040955-5897-409f-aea0-84b6ae16b77e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_share(self):
        super(TestProjectReaderTestsNFS, self).test_force_delete_share()

    @decorators.idempotent_id('3184269a-11ca-4484-8a4d-b855a6e1800f')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_update_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        name = data_utils.rand_name("rename_share")
        self.do_request(
            'update_share', expected_status=lib_exc.Forbidden,
            share_id=share['id'], name=name)

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        alt_name = data_utils.rand_name("rename_share")
        self.do_request(
            'update_share', expected_status=lib_exc.Forbidden,
            share_id=alt_share['id'], name=alt_name)

    @decorators.idempotent_id('e5ae5b56-38c0-44ec-b8e0-4bc2a5c1d28a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_share(self):
        super(TestProjectReaderTestsNFS, self).test_reset_share()

    @decorators.idempotent_id('f85818b1-b93a-4b89-8aa4-b099e582be7c')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_shrink_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'],
            size=CONF.share.share_size + 1)
        self.do_request(
            'shrink_share', expected_status=lib_exc.Forbidden,
            share_id=share['id'], new_size=CONF.share.share_size)
        waiters.wait_for_resource_status(self.client, share['id'], 'available')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            size=CONF.share.share_size + 1)
        self.do_request(
            'shrink_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'], new_size=CONF.share.share_size)

    @decorators.idempotent_id('0b57aedb-6b68-498f-814e-173c47e6c307')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_extend_share(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'extend_share', expected_status=lib_exc.Forbidden,
            share_id=share['id'], new_size=CONF.share.share_size + 1)
        waiters.wait_for_resource_status(self.client, share['id'], 'available')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'extend_share', expected_status=lib_exc.NotFound,
            share_id=alt_share['id'], new_size=CONF.share.share_size + 1)

    @decorators.idempotent_id('3def3f4e-33fc-4726-8818-6cffbc2cab51')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_set_share_metadata(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'])
        self.do_request(
            'set_metadata', expected_status=lib_exc.Forbidden,
            resource_id=share['id'], metadata={'key': 'value'})

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'])
        self.do_request(
            'set_metadata', expected_status=lib_exc.Forbidden,
            resource_id=alt_share['id'], metadata={'key': 'value'})

    @decorators.idempotent_id('28cacc77-556f-4707-ba2b-5ef3e56d6ef9')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_share_metadata(self):
        super(TestProjectReaderTestsNFS, self).test_get_share_metadata()

    @decorators.idempotent_id('55486589-a4ef-44f2-b489-96bc29dcd243')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_share_metadata(self):
        share = self.create_share(
            self.share_member_client, self.share_type['id'],
            metadata={'key': 'value'})
        self.do_request(
            'delete_metadata', expected_status=lib_exc.Forbidden,
            resource_id=share['id'], key='key')

        alt_share = self.create_share(
            self.alt_project_share_v2_client, self.share_type['id'],
            metadata={'key': 'value'})
        self.do_request(
            'delete_metadata', expected_status=lib_exc.Forbidden,
            resource_id=alt_share['id'], key='key')


class TestProjectAdminTestsCEPHFS(TestProjectAdminTestsNFS):
    protocol = 'cephfs'


class TestProjectMemberTestsCEPHFS(TestProjectMemberTestsNFS):
    protocol = 'cephfs'


class TestProjectReaderTestsCEPHFS(TestProjectReaderTestsNFS):
    protocol = 'cephfs'


class TestProjectAdminTestsCIFS(TestProjectAdminTestsNFS):
    protocol = 'cifs'


class TestProjectMemberTestsCIFS(TestProjectMemberTestsNFS):
    protocol = 'cifs'


class TestProjectReaderTestsCIFS(TestProjectReaderTestsNFS):
    protocol = 'cifs'
