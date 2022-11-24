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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.rbac import base as rbac_base
from manila_tempest_tests import utils

CONF = config.CONF


class ShareRbacShareGroupTypesTests(rbac_base.ShareRbacBaseTests,
                                    metaclass=abc.ABCMeta):

    @classmethod
    def setup_clients(cls):
        super(ShareRbacShareGroupTypesTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.admin_shares_v2_client = (
            cls.os_project_admin.share_v2.SharesV2Client())

    @classmethod
    def skip_checks(cls):
        super(ShareRbacShareGroupTypesTests, cls).skip_checks()
        if not CONF.share.run_share_group_tests:
            raise cls.skipException('Share Group tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            constants.MIN_SHARE_GROUP_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ShareRbacShareGroupTypesTests, cls).resource_setup()
        cls.group_specs1 = {u'key1': u'value1'}
        cls.group_specs2 = {u'key2': u'value2'}
        cls.share_type = cls.create_share_type()
        cls.share_group_type = cls.create_share_group_type(
            cls.share_type['id'], group_specs=cls.group_specs1)
        cls.private_share_group_type = cls.create_share_group_type(
            cls.share_type['id'], is_public=False)

    @abc.abstractmethod
    def test_create_share_group_type(self):
        pass

    @abc.abstractmethod
    def test_get_share_group_type(self):
        pass

    @abc.abstractmethod
    def test_list_share_group_types(self):
        pass

    @abc.abstractmethod
    def test_delete_share_group_type(self):
        pass

    @abc.abstractmethod
    def test_create_share_group_type_extra_specs(self):
        pass

    @abc.abstractmethod
    def test_update_share_group_type_extra_spec(self):
        pass

    @abc.abstractmethod
    def test_delete_share_group_type_extra_spec(self):
        pass

    @abc.abstractmethod
    def test_add_share_group_type_access(self):
        pass

    @abc.abstractmethod
    def test_list_share_group_type_access(self):
        pass

    @abc.abstractmethod
    def test_remove_share_group_type_access(self):
        pass


class ProjectAdminTests(ShareRbacShareGroupTypesTests, base.BaseSharesTest):

    credentials = ['project_admin']

    @decorators.idempotent_id('9ea9954a-ae09-4d02-a082-9a72b80009fc')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_group_type(self):
        share_group_type = self.do_request(
            'create_share_group_type', expected_status=200,
            name='gt', share_types=self.share_type['id'])['share_group_type']
        self.addCleanup(self.delete_resource, self.client,
                        share_group_type_id=share_group_type['id'])

    @decorators.idempotent_id('fcad2b86-ca43-42b0-82bd-37e6f760e4d2')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_group_type(self):
        self.do_request(
            'get_share_group_type', expected_status=200,
            share_group_type_id=self.share_group_type['id'])

    @decorators.idempotent_id('7871b1b5-610a-425c-9363-d0bcf2beff72')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_group_types(self):
        share_group_type_list = self.do_request(
            'list_share_group_types', expected_status=200)['share_group_types']
        share_group_type_id_list = [
            sgt['id'] for sgt in share_group_type_list
        ]
        self.assertIn(self.share_group_type['id'], share_group_type_id_list)

    @decorators.idempotent_id('c23da121-8b1f-4443-80cc-11881745a1c3')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_share_group_type(self):
        share_group_type = self.create_share_group_type(
            share_types=self.share_type['id'])
        self.do_request(
            'delete_share_group_type', expected_status=204,
            share_group_type_id=share_group_type['id'])

    @decorators.idempotent_id('80eb22cb-846a-4b51-a71d-ceef0b804901')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_group_type_extra_specs(self):
        self.do_request(
            'create_share_group_type_specs', expected_status=200,
            share_group_type_id=self.share_group_type['id'],
            group_specs_dict=self.group_specs2)
        self.addCleanup(
            self.admin_shares_v2_client.delete_share_group_type_spec,
            self.share_group_type['id'], group_spec_key='key2')

    @decorators.idempotent_id('fe29877d-2226-42ca-b492-4be0dacd6eaf')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_share_group_type_extra_spec(self):
        self.do_request(
            'update_share_group_type_spec', expected_status=200,
            share_group_type_id=self.share_group_type['id'],
            group_spec_key='key', group_spec_value='value_updated')

    @decorators.idempotent_id('743c18dc-8c3a-4934-9ef8-8b342daffe7c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_delete_share_group_type_extra_spec(self):
        self.admin_shares_v2_client.create_share_group_type_specs(
            self.share_group_type['id'], self.group_specs2)
        self.do_request(
            'delete_share_group_type_spec', expected_status=204,
            share_group_type_id=self.share_group_type['id'],
            group_spec_key='key2')

    @decorators.idempotent_id('89876c46-1167-450d-8b98-746d97fff388')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_add_share_group_type_access(self):
        self.do_request(
            'add_access_to_share_group_type', expected_status=202,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)
        self.addCleanup(
            self.client.remove_access_from_share_group_type,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)

    @decorators.idempotent_id('64a7be53-d1af-40c3-950b-743a2704ac97')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_group_type_access(self):
        self.client.add_access_to_share_group_type(
            self.private_share_group_type['id'], self.client.project_id)
        self.addCleanup(
            self.client.remove_access_from_share_group_type,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)
        access_list = self.do_request(
            'list_access_to_share_group_type', expected_status=200,
            share_group_type_id=self.private_share_group_type['id']
        )['share_group_type_access']

        project_id_list = [
            access['project_id'] for access in access_list
        ]

        self.assertIn(self.client.project_id, project_id_list)

    @decorators.idempotent_id('fc67ba18-78e9-4c02-9b37-2bd49c8a4470')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_remove_share_group_type_access(self):
        self.client.add_access_to_share_group_type(
            self.private_share_group_type['id'], self.client.project_id)
        self.do_request(
            'remove_access_from_share_group_type', expected_status=202,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)


class ProjectMemberTests(ShareRbacShareGroupTypesTests, base.BaseSharesTest):

    credentials = ['project_member', 'project_admin']

    @decorators.idempotent_id('f9e6f2fd-7c1a-4eee-817c-bf1988904515')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type(self):
        self.do_request(
            'create_share_group_type', expected_status=lib_exc.Forbidden,
            name='gt', share_types=self.share_type['id'])

    @decorators.idempotent_id('8eaf4a99-9706-41c9-8b12-40856d0900f4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_group_type(self):
        self.do_request(
            'get_share_group_type', expected_status=200,
            share_group_type_id=self.share_group_type['id'])

    @decorators.idempotent_id('d2dd61f4-c763-49f9-9c93-8b587879f554')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_group_types(self):
        share_group_type_list = self.do_request(
            'list_share_group_types', expected_status=200)['share_group_types']
        share_group_type_id_list = [
            sgt['id'] for sgt in share_group_type_list
        ]
        self.assertIn(self.share_group_type['id'], share_group_type_id_list)

    @decorators.idempotent_id('8f45798f-717d-41b0-acba-a80dd647cddf')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_group_type(self):
        share_group_type = self.create_share_group_type(
            share_types=self.share_type['id'])
        self.do_request(
            'delete_share_group_type', expected_status=lib_exc.Forbidden,
            share_group_type_id=share_group_type['id'])

    @decorators.idempotent_id('2fa2f953-f068-4c60-ab52-eeb1bd69a7a4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_extra_specs(self):
        self.do_request(
            'create_share_group_type_specs', expected_status=lib_exc.Forbidden,
            share_group_type_id=self.share_group_type['id'],
            group_specs_dict=self.group_specs2)

    @decorators.idempotent_id('30c73c94-b7bc-4e1f-8172-192335997879')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_group_type_extra_spec(self):
        self.do_request(
            'update_share_group_type_spec', expected_status=lib_exc.Forbidden,
            share_group_type_id=self.share_group_type['id'],
            group_spec_key='key', group_spec_value='value_updated')

    @decorators.idempotent_id('95aa1fbf-3eaf-4d65-96b5-4554b0fb0937')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_group_type_extra_spec(self):
        self.admin_shares_v2_client.create_share_group_type_specs(
            self.share_group_type['id'], self.group_specs2)
        self.do_request(
            'delete_share_group_type_spec', expected_status=lib_exc.Forbidden,
            share_group_type_id=self.share_group_type['id'],
            group_spec_key='key2')

    @decorators.idempotent_id('85b69e26-9c67-45c4-80e0-2ce212977c2a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_group_type_access(self):
        self.do_request(
            'add_access_to_share_group_type',
            expected_status=lib_exc.Forbidden,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)

    @decorators.idempotent_id('027314a9-6b14-4ae9-83f2-471e84ccaa01')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_group_type_access(self):
        self.admin_shares_v2_client.add_access_to_share_group_type(
            self.private_share_group_type['id'], self.client.project_id)
        self.addCleanup(
            self.admin_shares_v2_client.remove_access_from_share_group_type,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)
        self.do_request(
            'list_access_to_share_group_type',
            expected_status=lib_exc.Forbidden,
            share_group_type_id=self.private_share_group_type['id'])

    @decorators.idempotent_id('d8518122-dabd-4d2d-8b6a-4eed975e19ee')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_remove_share_group_type_access(self):
        self.admin_shares_v2_client.add_access_to_share_group_type(
            self.private_share_group_type['id'], self.client.project_id)
        self.addCleanup(
            self.admin_shares_v2_client.remove_access_from_share_group_type,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)
        self.do_request(
            'remove_access_from_share_group_type',
            expected_status=lib_exc.Forbidden,
            share_group_type_id=self.private_share_group_type['id'],
            project_id=self.client.project_id)


class ProjectReaderTests(ProjectMemberTests):

    credentials = ['project_reader', 'project_member', 'project_admin']

    @decorators.idempotent_id('8c47bbe9-f3f1-419e-b00b-97c9c942a48a')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type(self):
        super(ProjectReaderTests, self).test_create_share_group_type()

    @decorators.idempotent_id('fe3b28a3-6980-4782-8eaa-518bbd3913d1')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_share_group_type(self):
        super(ProjectReaderTests, self).test_get_share_group_type()

    @decorators.idempotent_id('47f92f0b-424e-4685-a742-8a4e00cc6901')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_list_share_group_types(self):
        super(ProjectReaderTests, self).test_list_share_group_types()

    @decorators.idempotent_id('e853fd60-8906-4e38-b0b4-ec5723696518')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_group_type(self):
        super(ProjectReaderTests, self).test_delete_share_group_type()

    @decorators.idempotent_id('caa6d960-4f34-4dff-9cc0-9a0cde44c2ae')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_create_share_group_type_extra_specs(self):
        super(
            ProjectReaderTests,
            self).test_create_share_group_type_extra_specs()

    @decorators.idempotent_id('2782c329-2447-49f7-95e7-0c4c766cfda3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_update_share_group_type_extra_spec(self):
        super(
            ProjectReaderTests, self).test_update_share_group_type_extra_spec()

    @decorators.idempotent_id('003a0eee-0075-47b0-ba8a-8e57e958c1d3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_delete_share_group_type_extra_spec(self):
        super(
            ProjectReaderTests, self).test_delete_share_group_type_extra_spec()

    @decorators.idempotent_id('93bba264-104c-48af-af91-5a79ec3e695e')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_add_share_group_type_access(self):
        super(ProjectReaderTests, self).test_add_share_group_type_access()

    @decorators.idempotent_id('176b280c-7a46-43ae-8164-3bdd945d2dd4')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_list_share_group_type_access(self):
        super(ProjectReaderTests, self).test_list_share_group_type_access()

    @decorators.idempotent_id('00caa020-3805-4322-aac1-86d4552268a2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API)
    def test_remove_share_group_type_access(self):
        super(ProjectReaderTests, self).test_remove_share_group_type_access()
