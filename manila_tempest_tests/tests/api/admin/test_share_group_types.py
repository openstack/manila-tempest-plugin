# Copyright 2016 Andrew Kerr
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
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from testtools import testcase as tc

from manila_tempest_tests.common import constants
from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils


CONF = config.CONF

LATEST_MICROVERSION = CONF.share.max_api_microversion


@ddt.ddt
class ShareGroupTypesTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(ShareGroupTypesTest, cls).skip_checks()
        if not CONF.share.run_share_group_tests:
            raise cls.skipException('Share Group tests disabled.')

        utils.check_skip_if_microversion_not_supported(
            constants.MIN_SHARE_GROUP_MICROVERSION)

    @classmethod
    def resource_setup(cls):
        super(ShareGroupTypesTest, cls).resource_setup()

        # Create 2 share_types
        name = data_utils.rand_name("tempest-manila")
        extra_specs = cls.add_extra_specs_to_dict()
        cls.share_type = cls.create_share_type(name, extra_specs=extra_specs)

        name = data_utils.rand_name("tempest-manila")
        cls.share_type2 = cls.create_share_type(name, extra_specs=extra_specs)

    @decorators.idempotent_id('e2ba1754-cecc-4178-ad39-eefbb59e4d6d')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(
        *itertools.product(('id', 'name'), utils.deduplicate(
            [LATEST_MICROVERSION, constants.MIN_SHARE_GROUP_MICROVERSION,
             constants.SHARE_GROUPS_GRADUATION_VERSION])))
    @ddt.unpack
    def test_create_get_delete_share_group_type(self, st_key, version):
        utils.check_skip_if_microversion_not_supported(version)
        name = data_utils.rand_name("tempest-manila")

        # Create share group type
        sg_type_c = self.create_share_group_type(
            name=name,
            share_types=self.share_type[st_key],
            cleanup_in_class=False,
            version=version)

        self.assertEqual(
            [self.share_type['id']],
            sg_type_c['share_types'],
            'Share type not applied correctly.')

        # Read share group type
        sg_type_r = self.shares_v2_client.get_share_group_type(
            sg_type_c['id'], version=version)['share_group_type']
        keys = set(sg_type_r.keys())
        self.assertTrue(
            constants.SHARE_GROUP_TYPE_REQUIRED_KEYS.issubset(keys),
            'At least one expected key missing from share group type '
            'response. Expected %s, got %s.' % (
                constants.SHARE_GROUP_TYPE_REQUIRED_KEYS, keys))
        self.assertEqual(sg_type_c['name'], sg_type_r['name'])

        # Delete share group type
        self.shares_v2_client.delete_share_group_type(
            sg_type_r['id'], version=version)
        self.shares_v2_client.wait_for_resource_deletion(
            share_group_type_id=sg_type_r['id'])

    @decorators.idempotent_id('65cf04d6-0620-4e0d-96f2-456946e8a552')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data('id', 'name')
    def test_create_share_group_type_multiple_share_types_min(self, st_key):
        name = data_utils.rand_name("tempest-manila")

        sg_type = self.create_share_group_type(
            name=name,
            share_types=[self.share_type[st_key], self.share_type2[st_key]],
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        self.assertEqual(
            {self.share_type['id'], self.share_type2['id']},
            set(sg_type['share_types']),
            'Share types not applied correctly.')

    @decorators.idempotent_id('6e103b7b-cd01-4edb-91e7-a16681781b36')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_group_type_with_one_spec_min(self):
        name = data_utils.rand_name("tempest-manila")
        group_specs = {'key': 'value'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        self.assertDictMatch(group_specs, sg_type['group_specs'])

    @decorators.idempotent_id('ec459ebb-5c45-4d4f-95f0-3bbf2974366c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_create_share_group_type_with_multiple_specs_min(self):
        name = data_utils.rand_name("tempest-manila")
        group_specs = {'key1': 'value1', 'key2': 'value2'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        self.assertDictMatch(group_specs, sg_type['group_specs'])

    @decorators.idempotent_id('dd620bfd-197b-4675-ace6-e26f809bb26e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_one_share_group_type_extra_spec(self):
        name = data_utils.rand_name('share-group-type')
        group_specs = {'key1': 'value1', 'key2': 'value2'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        extra_spec = self.shares_v2_client.get_share_group_type_spec(
            sg_type['id'], 'key1')

        self.assertEqual({'key1': group_specs['key1']}, extra_spec)

    @decorators.idempotent_id('eef69171-9757-423c-8cd4-487cbd84ca24')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_get_all_share_group_type_extra_specs(self):
        name = data_utils.rand_name('share-group-type')
        group_specs = {'key': 'value'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        extra_specs = self.shares_v2_client.get_share_group_type_specs(
            sg_type['id'])

        self.assertDictMatch(group_specs, extra_specs['group_specs'])

    @decorators.idempotent_id('15b44580-a34d-4e0d-a77b-0e76b45d6199')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_GROUP_MICROVERSION,
                            constants.SHARE_GROUPS_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_update_single_share_group_type_spec(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        name = data_utils.rand_name("tempest-manila")
        group_specs = {'key1': 'value1', 'key2': 'value2'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=version)

        self.assertDictMatch(group_specs, sg_type['group_specs'])

        group_specs = {'key1': 'value1', 'key2': 'value2'}

        self.shares_v2_client.update_share_group_type_spec(
            sg_type['id'], 'key1', 'value3', version=version)
        sg_type = self.shares_v2_client.get_share_group_type(
            sg_type['id'])['share_group_type']

        self.assertIn('key1', sg_type['group_specs'])
        self.assertIn('key2', sg_type['group_specs'])
        self.assertEqual('value3', sg_type['group_specs']['key1'])
        self.assertEqual(group_specs['key2'], sg_type['group_specs']['key2'])

    @decorators.idempotent_id('3ed054c5-d0ab-4a73-b704-994eb7f9c46c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    def test_update_all_share_group_type_specs_min(self):
        name = data_utils.rand_name("tempest-manila")
        group_specs = {'key1': 'value1', 'key2': 'value2'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=constants.MIN_SHARE_GROUP_MICROVERSION)

        self.assertDictMatch(group_specs, sg_type['group_specs'])

        group_specs = {'key1': 'value3', 'key2': 'value4'}

        self.shares_v2_client.update_share_group_type_specs(
            sg_type['id'], group_specs)
        sg_type = self.shares_v2_client.get_share_group_type(
            sg_type['id'])['share_group_type']

        for k, v in group_specs.items():
            self.assertIn(k, sg_type['group_specs'])
            self.assertEqual(v, sg_type['group_specs'][k])

    @decorators.idempotent_id('efddee69-ca23-4681-8247-94ded81c4c3a')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_GROUP_MICROVERSION,
                            constants.SHARE_GROUPS_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_delete_single_share_group_type_spec_min(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        name = data_utils.rand_name("tempest-manila")
        group_specs = {'key1': 'value1', 'key2': 'value2'}

        sg_type = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            group_specs=group_specs,
            cleanup_in_class=False,
            version=version)

        self.assertDictMatch(group_specs, sg_type['group_specs'])

        key_to_delete = 'key1'
        group_specs.pop(key_to_delete)

        self.shares_v2_client.delete_share_group_type_spec(
            sg_type['id'], key_to_delete, version=version)
        sg_type = self.shares_v2_client.get_share_group_type(
            sg_type['id'], version=version)['share_group_type']

        self.assertDictMatch(group_specs, sg_type['group_specs'])

    @decorators.idempotent_id('c2d34b42-e3ec-404e-8b7a-0fe9b1560507')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(
        *utils.deduplicate([constants.MIN_SHARE_GROUP_MICROVERSION,
                            constants.SHARE_GROUPS_GRADUATION_VERSION,
                            LATEST_MICROVERSION]))
    def test_private_share_group_type_access(self, version):
        utils.check_skip_if_microversion_not_supported(version)
        name = data_utils.rand_name("tempest-manila")
        group_specs = {"key1": "value1", "key2": "value2"}
        project_id = self.shares_v2_client.tenant_id

        # Create private share group type
        sgt_create = self.create_share_group_type(
            name=name,
            share_types=[self.share_type['id']],
            is_public=False,
            group_specs=group_specs,
            version=version
        )
        self.assertEqual(name, sgt_create['name'])
        sgt_id = sgt_create["id"]

        # It should not be listed without access
        sgt_list = self.shares_v2_client.list_share_group_types(
            version=version)['share_group_types']
        self.assertFalse(any(sgt_id == sgt["id"] for sgt in sgt_list))

        # List projects that have access for share group type - none expected
        access = self.shares_v2_client.list_access_to_share_group_type(
            sgt_id, version=version)['share_group_type_access']
        self.assertEmpty(access)

        # Add project access to share group type
        access = self.shares_v2_client.add_access_to_share_group_type(
            sgt_id, project_id, version=version)

        # Now it should be listed
        sgt_list = self.shares_v2_client.list_share_group_types(
            version=version)['share_group_types']
        self.assertTrue(any(sgt_id == sgt["id"] for sgt in sgt_list))

        # List projects that have access for share group type - one expected
        access = self.shares_v2_client.list_access_to_share_group_type(
            sgt_id, version=version)['share_group_type_access']
        expected = [{'share_group_type_id': sgt_id, 'project_id': project_id}]
        self.assertEqual(expected, access)

        # Remove project access from share group type
        access = self.shares_v2_client.remove_access_from_share_group_type(
            sgt_id, project_id, version=version)

        # It should not be listed without access
        sgt_list = self.shares_v2_client.list_share_group_types(
            version=version)['share_group_types']
        self.assertFalse(any(sgt_id == sgt["id"] for sgt in sgt_list))

        # List projects that have access for share group type - none expected
        access = self.shares_v2_client.list_access_to_share_group_type(
            sgt_id, version=version)['share_group_type_access']
        self.assertEmpty(access)

    @decorators.idempotent_id('b8b20a96-cecc-4677-8a77-aae3b93e5b96')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API)
    @ddt.data(*utils.deduplicate(('2.45', '2.46', LATEST_MICROVERSION)))
    def test_share_group_type_create_show_list_with_is_default_key(self,
                                                                   version):
        utils.check_skip_if_microversion_not_supported(version)
        name = data_utils.rand_name("tempest-manila")

        # Create share group type
        sg_type_c = self.create_share_group_type(
            name=name,
            share_types=self.share_type['id'],
            cleanup_in_class=False,
            version=version)
        if utils.is_microversion_ge(version, '2.46'):
            self.assertIn('is_default', sg_type_c)
            self.assertIs(False, sg_type_c['is_default'])
        else:
            self.assertNotIn('is_default', sg_type_c)

        # List share group type
        sg_type_list = self.shares_v2_client.list_share_group_types(
            version=version)['share_group_types']
        for sg_type_get in sg_type_list:
            if utils.is_microversion_ge(version, '2.46'):
                self.assertIn('is_default', sg_type_get)
                self.assertTrue(sg_type_get['is_default'] in (True, False))
            else:
                self.assertNotIn('is_default', sg_type_get)

        # Show share group type
        sg_type_id = sg_type_c['id']
        sg_type_show = self.shares_v2_client.get_share_group_type(
            sg_type_id, version=version)['share_group_type']
        if utils.is_microversion_ge(version, '2.46'):
            self.assertIn('is_default', sg_type_show)
            self.assertIs(False, sg_type_show['is_default'])
        else:
            self.assertNotIn('is_default', sg_type_show)
