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
from oslo_utils import uuidutils
import six
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from manila_tempest_tests.tests.api import base
from manila_tempest_tests import utils

CONF = config.CONF

MICROVERSION = '2.37'
QUERY_BY_TIMESTAMP_MICROVERSION = '2.52'


class UserMessageNegativeTest(base.BaseSharesMixedTest):

    @classmethod
    def skip_checks(cls):
        super(UserMessageNegativeTest, cls).skip_checks()
        utils.check_skip_if_microversion_not_supported(MICROVERSION)

    def setUp(self):
        super(UserMessageNegativeTest, self).setUp()
        self.message = self.create_user_message()

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @decorators.idempotent_id('cb6c0dbd-a3cb-404b-a358-7cec3596aff4')
    def test_show_message_of_other_tenants(self):
        self.assertRaises(lib_exc.NotFound,
                          self.alt_shares_v2_client.get_message,
                          self.message['id'])

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @decorators.idempotent_id('f493a1f9-43e1-4a85-a673-8520d5a81f68')
    def test_show_nonexistent_message(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.get_message,
                          six.text_type(uuidutils.generate_uuid()))

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @decorators.idempotent_id('2f5be1aa-974b-4f6a-ae3a-084578e64f82')
    def test_delete_message_of_other_tenants(self):
        self.assertRaises(lib_exc.NotFound,
                          self.alt_shares_v2_client.delete_message,
                          self.message['id'])

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @decorators.idempotent_id('9029cc9f-b904-4e58-b268-adf7a93cc1f1')
    def test_delete_nonexistent_message(self):
        self.assertRaises(lib_exc.NotFound,
                          self.shares_v2_client.delete_message,
                          six.text_type(uuidutils.generate_uuid()))

    @decorators.attr(type=[base.TAG_NEGATIVE, base.TAG_API])
    @utils.skip_if_microversion_not_supported(QUERY_BY_TIMESTAMP_MICROVERSION)
    @decorators.idempotent_id('03e80563-1a36-408e-baa8-0e3ed46f7a0a')
    def test_list_messages_with_invalid_time_format(self):
        params_key = ['created_since', 'created_before']
        for key in params_key:
            params = {key: 'invalid_time'}
            self.assertRaises(lib_exc.BadRequest,
                              self.shares_v2_client.list_messages,
                              params=params)
