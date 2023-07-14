# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime

from oslo_utils import timeutils
from oslo_utils import uuidutils
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF

LOCKS_MIN_API_VERSION = '2.81'

RESOURCE_LOCK_FIELDS = {
    'id',
    'resource_id',
    'resource_action',
    'resource_type',
    'user_id',
    'project_id',
    'lock_context',
    'created_at',
    'updated_at',
    'lock_reason',
    'links',
}


class ResourceLockCRUTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ResourceLockCRUTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(LOCKS_MIN_API_VERSION)

    @classmethod
    def resource_setup(cls):
        super(ResourceLockCRUTest, cls).resource_setup()
        # create share type
        share_type = cls.create_share_type()
        cls.share_type_id = share_type['id']

        # create share and place a "delete" lock on it
        cls.share = cls.create_share(share_type_id=cls.share_type_id)
        cls.lock = cls.create_resource_lock(cls.share['id'])

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('f3d162a6-2ab4-433b-b8e7-6bf4f0bb6b0e')
    def test_list_resource_locks(self):
        locks = self.shares_v2_client.list_resource_locks()['resource_locks']
        self.assertIsInstance(locks, list)
        self.assertIn(self.lock['id'], [x['id'] for x in locks])
        lock = locks[0]
        self.assertEqual(RESOURCE_LOCK_FIELDS, set(lock.keys()))

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('72cc0d43-f676-4dd8-8a93-faa71608de98')
    def test_list_resource_locks_sorted_and_paginated(self):
        lock_2 = self.create_resource_lock(self.share['id'],
                                           cleanup_in_class=False)
        lock_3 = self.create_resource_lock(self.share['id'],
                                           cleanup_in_class=False)

        expected_order = [self.lock['id'], lock_2['id']]

        filters = {'sort_key': 'created_at', 'sort_dir': 'asc', 'limit': 2}
        body = self.shares_v2_client.list_resource_locks(filters=filters)
        # tempest/lib/common/rest_client.py's _parse_resp checks
        # for number of keys in response's dict, if there is only single
        # key, it returns directly this key, otherwise it returns
        # parsed body. If limit param is used, then API returns
        # multiple keys in response ('resource_locks' and
        # 'resource_lock_links')
        locks = body['resource_locks']
        self.assertIsInstance(locks, list)
        actual_order = [x['id'] for x in locks]
        self.assertEqual(2, len(actual_order))
        self.assertNotIn(lock_3['id'], actual_order)
        self.assertEqual(expected_order, actual_order)

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('22831edc-9d99-432d-a0b6-85af8853db98')
    def test_list_resource_locks_filtered(self):
        # Filter by resource_id, resource_action, lock_reason_like,
        # created_since, created_before
        share_2 = self.create_share(share_type_id=self.share_type_id)
        share_1_lock_2 = self.create_resource_lock(
            self.share['id'],
            lock_reason="clemson tigers rule",
            cleanup_in_class=False)
        share_2_lock = self.create_resource_lock(share_2['id'],
                                                 cleanup_in_class=False)

        # filter by resource_type
        expected_locks = sorted([
            self.lock['id'],
            share_1_lock_2['id'],
            share_2_lock['id']
        ])
        actual_locks = self.shares_v2_client.list_resource_locks(
            filters={'resource_type': 'share'})['resource_locks']
        self.assertEqual(expected_locks,
                         sorted([lock['id'] for lock in actual_locks]))

        # filter by resource_id
        expected_locks = sorted([self.lock['id'], share_1_lock_2['id']])
        actual_locks = self.shares_v2_client.list_resource_locks(
            filters={'resource_id': self.share['id']})['resource_locks']
        self.assertEqual(expected_locks,
                         sorted([lock['id'] for lock in actual_locks]))

        # filter by inexact lock reason
        actual_locks = self.shares_v2_client.list_resource_locks(
            filters={'lock_reason~': "clemson"})['resource_locks']
        self.assertEqual([share_1_lock_2['id']],
                         [lock['id'] for lock in actual_locks])

        # timestamp filters
        created_at_1 = timeutils.parse_strtime(self.lock['created_at'])
        created_at_2 = timeutils.parse_strtime(share_2_lock['created_at'])
        time_1 = created_at_1 - datetime.timedelta(seconds=1)
        time_2 = created_at_2 - datetime.timedelta(microseconds=1)
        filters_1 = {'created_since': str(time_1)}

        # should return all resource locks created by this test including
        # self.lock
        actual_locks = self.shares_v2_client.list_resource_locks(
            filters=filters_1)['resource_locks']
        actual_lock_ids = [lock['id'] for lock in actual_locks]
        self.assertGreaterEqual(len(actual_lock_ids), 3)
        self.assertIn(self.lock['id'], actual_lock_ids)
        self.assertIn(share_1_lock_2['id'], actual_lock_ids)

        for lock in actual_locks:
            time_diff_with_created_since = timeutils.delta_seconds(
                time_1, timeutils.parse_strtime(lock['created_at']))
            self.assertGreaterEqual(time_diff_with_created_since, 0)

        filters_2 = {
            'created_since': str(time_1),
            'created_before': str(time_2),
        }

        actual_locks = self.shares_v2_client.list_resource_locks(
            filters=filters_2)['resource_locks']
        self.assertIsInstance(actual_locks, list)
        actual_lock_ids = [lock['id'] for lock in actual_locks]
        self.assertGreaterEqual(len(actual_lock_ids), 2)
        self.assertIn(self.lock['id'], actual_lock_ids)
        self.assertIn(share_1_lock_2['id'], actual_lock_ids)
        self.assertNotIn(share_2_lock['id'], actual_lock_ids)

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('8cbf7331-f3a1-4c7b-ab1e-f8b938bf135e')
    def test_get_resource_lock(self):
        lock = self.shares_v2_client.get_resource_lock(
            self.lock['id'])['resource_lock']

        self.assertEqual(set(RESOURCE_LOCK_FIELDS), set(lock.keys()))
        self.assertTrue(uuidutils.is_uuid_like(lock['id']))
        self.assertEqual('share', lock['resource_type'])
        self.assertEqual(self.share['id'], lock['resource_id'])
        self.assertEqual('delete', lock['resource_action'])
        self.assertEqual('user', lock['lock_context'])
        self.assertEqual(self.shares_v2_client.user_id, lock['user_id'])
        self.assertEqual(self.shares_v2_client.project_id, lock['project_id'])

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('a7f0fb6a-05ac-4afa-b8d9-04d20549bbd1')
    def test_create_resource_lock(self):
        # testing lock creation by a different user in the same project
        project = self.os_admin.projects_client.show_project(
            self.shares_v2_client.project_id)['project']
        new_user_client = self.create_user_and_get_client(project)

        lock = self.create_resource_lock(
            self.share['id'],
            client=new_user_client.shares_v2_client,
            cleanup_in_class=False)

        self.assertEqual(set(RESOURCE_LOCK_FIELDS), set(lock.keys()))
        self.assertTrue(uuidutils.is_uuid_like(lock['id']))
        self.assertEqual('share', lock['resource_type'])
        self.assertEqual(self.share['id'], lock['resource_id'])
        self.assertEqual('delete', lock['resource_action'])
        self.assertEqual('user', lock['lock_context'])
        self.assertEqual(new_user_client.shares_v2_client.user_id,
                         lock['user_id'])
        self.assertEqual(self.shares_v2_client.project_id, lock['project_id'])

        # testing lock creation by admin
        lock = self.create_resource_lock(
            self.share['id'],
            client=self.admin_shares_v2_client,
            cleanup_in_class=False)
        self.assertEqual('admin', lock['lock_context'])

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    @decorators.idempotent_id('d7b51cde-ff4f-45ce-a237-401e8be5b4e5')
    def test_update_resource_lock(self):
        lock = self.shares_v2_client.update_resource_lock(
            self.lock['id'], lock_reason="new lock reason")['resource_lock']

        # update is synchronous
        self.assertEqual("new lock reason", lock['lock_reason'])

        # verify get
        lock = self.shares_v2_client.get_resource_lock(lock['id'])
        self.assertEqual("new lock reason",
                         lock['resource_lock']['lock_reason'])


class ResourceLockDeleteTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(ResourceLockDeleteTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(LOCKS_MIN_API_VERSION)

    @classmethod
    def resource_setup(cls):
        super(ResourceLockDeleteTest, cls).resource_setup()
        cls.share_type_id = cls.create_share_type()['id']

    @decorators.idempotent_id('835fd617-4600-40a0-9ba1-40e5e0097b01')
    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    def test_delete_lock(self):
        share = self.create_share(share_type_id=self.share_type_id)
        lock_1 = self.create_resource_lock(share['id'], cleanup_in_class=False)
        lock_2 = self.create_resource_lock(share['id'], cleanup_in_class=False)

        locks = self.shares_v2_client.list_resource_locks(
            filters={'resource_id': share['id']})['resource_locks']
        self.assertEqual(sorted([lock_1['id'], lock_2['id']]),
                         sorted([lock['id'] for lock in locks]))

        self.shares_v2_client.delete_resource_lock(lock_1['id'])
        locks = self.shares_v2_client.list_resource_locks(
            filters={'resource_id': share['id']})['resource_locks']
        self.assertEqual(1, len(locks))
        self.assertIn(lock_2['id'], [lock['id'] for lock in locks])

    @decorators.idempotent_id('a96e70c7-0afe-4335-9abc-4b45ef778bd7')
    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND])
    def test_delete_locked_resource(self):
        share = self.create_share(share_type_id=self.share_type_id)
        lock_1 = self.create_resource_lock(share['id'], cleanup_in_class=False)
        lock_2 = self.create_resource_lock(share['id'], cleanup_in_class=False)

        # share can't be deleted when a lock exists
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.delete_share,
                          share['id'])

        # admin can't do this either
        self.assertRaises(lib_exc.Forbidden,
                          self.admin_shares_v2_client.delete_share,
                          share['id'])
        # "the force" shouldn't work either
        self.assertRaises(lib_exc.Forbidden,
                          self.admin_shares_v2_client.delete_share,
                          share['id'],
                          params={'force': True})

        self.shares_v2_client.delete_resource_lock(lock_1['id'])

        # there's at least one lock, share deletion should still fail
        self.assertRaises(lib_exc.Forbidden,
                          self.shares_v2_client.delete_share,
                          share['id'])

        self.shares_v2_client.delete_resource_lock(lock_2['id'])

        # locks are gone, share deletion should be possible
        self.shares_v2_client.delete_share(share['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            share_id=share["id"])
