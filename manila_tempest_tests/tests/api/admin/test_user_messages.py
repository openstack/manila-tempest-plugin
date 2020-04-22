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

import datetime

from oslo_utils import timeutils
from oslo_utils import uuidutils
from tempest import config
from tempest.lib import decorators

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF

MICROVERSION = '2.37'
QUERY_BY_TIMESTAMP_MICROVERSION = '2.52'
MESSAGE_KEYS = (
    'created_at',
    'action_id',
    'detail_id',
    'expires_at',
    'id',
    'message_level',
    'request_id',
    'resource_type',
    'resource_id',
    'user_message',
    'project_id',
    'links',
)


class UserMessageTest(base.BaseSharesAdminTest):

    @classmethod
    def skip_checks(cls):
        super(UserMessageTest, cls).skip_checks()
        utils.check_skip_if_microversion_lt(MICROVERSION)

    def setUp(self):
        super(UserMessageTest, self).setUp()
        self.message = self.create_user_message()

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API])
    def test_list_messages(self):
        body = self.shares_v2_client.list_messages()
        self.assertIsInstance(body, list)
        self.assertTrue(self.message['id'], [x['id'] for x in body])
        message = body[0]
        self.assertEqual(set(MESSAGE_KEYS), set(message.keys()))

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API])
    def test_list_messages_sorted_and_paginated(self):
        self.create_user_message()
        self.create_user_message()
        params = {'sort_key': 'resource_id', 'sort_dir': 'asc', 'limit': 2}
        body = self.shares_v2_client.list_messages(params=params)
        # tempest/lib/common/rest_client.py's _parse_resp checks
        # for number of keys in response's dict, if there is only single
        # key, it returns directly this key, otherwise it returns
        # parsed body. If limit param is used, then API returns
        # multiple keys in response ('messages' and 'message_links')
        messages = body['messages']
        self.assertIsInstance(messages, list)
        ids = [x['resource_id'] for x in messages]
        self.assertEqual(2, len(ids))
        self.assertEqual(ids, sorted(ids))

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API])
    def test_list_messages_filtered(self):
        self.create_user_message()
        params = {'resource_id': self.message['resource_id']}
        body = self.shares_v2_client.list_messages(params=params)
        self.assertIsInstance(body, list)
        ids = [x['id'] for x in body]
        self.assertEqual([self.message['id']], ids)

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API])
    def test_show_message(self):
        self.addCleanup(self.shares_v2_client.delete_message,
                        self.message['id'])

        message = self.shares_v2_client.get_message(self.message['id'])

        self.assertEqual(set(MESSAGE_KEYS), set(message.keys()))
        self.assertTrue(uuidutils.is_uuid_like(message['id']))
        self.assertEqual('001', message['action_id'])
        # don't check specific detail_id which may vary
        # depending on order of filters, we can still check
        # user_message
        self.assertIn(
            'No storage could be allocated for this share request',
            message['user_message'])
        self.assertEqual('SHARE', message['resource_type'])
        self.assertTrue(uuidutils.is_uuid_like(message['resource_id']))
        self.assertEqual('ERROR', message['message_level'])
        created_at = timeutils.parse_strtime(message['created_at'])
        expires_at = timeutils.parse_strtime(message['expires_at'])
        self.assertGreater(expires_at, created_at)
        self.assertEqual(set(MESSAGE_KEYS), set(message.keys()))

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API])
    def test_delete_message(self):
        self.shares_v2_client.delete_message(self.message['id'])
        self.shares_v2_client.wait_for_resource_deletion(
            message_id=self.message['id'])

    @decorators.attr(type=[base.TAG_POSITIVE, base.TAG_API])
    @base.skip_if_microversion_not_supported(QUERY_BY_TIMESTAMP_MICROVERSION)
    def test_list_messages_with_since_and_before_filters(self):
        new_message = self.create_user_message()
        created_at_1 = timeutils.parse_strtime(self.message['created_at'])
        created_at_2 = timeutils.parse_strtime(new_message['created_at'])
        time_1 = created_at_1 - datetime.timedelta(seconds=1)
        time_2 = created_at_2 - datetime.timedelta(seconds=1)

        params1 = {'created_since': str(time_1)}
        # should return all user messages created by this test including
        # self.message
        messages = self.shares_v2_client.list_messages(params=params1)
        ids = [x['id'] for x in messages]
        self.assertGreaterEqual(len(ids), 2)
        self.assertIn(self.message['id'], ids)
        self.assertIn(new_message['id'], ids)
        for message in messages:
            time_diff_with_created_since = timeutils.delta_seconds(
                time_1, timeutils.parse_strtime(message['created_at']))
            self.assertGreaterEqual(time_diff_with_created_since, 0)

        params2 = {'created_since': str(time_1),
                   'created_before': str(time_2)}
        # should not return new_message, but return a list that is equal to 1
        # and include self.message
        messages = self.shares_v2_client.list_messages(params=params2)
        self.assertIsInstance(messages, list)
        ids = [x['id'] for x in messages]
        self.assertGreaterEqual(len(ids), 1)
        self.assertIn(self.message['id'], ids)
        self.assertNotIn(new_message['id'], ids)
        for message in messages:
            time_diff_with_created_since = timeutils.delta_seconds(
                time_1, timeutils.parse_strtime(message['created_at']))
            time_diff_with_created_before = timeutils.delta_seconds(
                time_2, timeutils.parse_strtime(message['created_at']))
            self.assertGreaterEqual(time_diff_with_created_since, 0)
            self.assertGreaterEqual(0, time_diff_with_created_before)

        params3 = {'created_before': str(time_2)}
        # should not include self.message
        messages = self.shares_v2_client.list_messages(params=params3)
        ids = [x['id'] for x in messages]
        self.assertGreaterEqual(len(ids), 1)
        self.assertNotIn(new_message['id'], ids)
        self.assertIn(self.message['id'], ids)
        for message in messages:
            time_diff_with_created_before = timeutils.delta_seconds(
                time_2, timeutils.parse_strtime(message['created_at']))
            self.assertGreaterEqual(0, time_diff_with_created_before)
