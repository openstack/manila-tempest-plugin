# Copyright 2025 Cloudifcation GmbH.  All rights reserved.
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

import base64
import secrets

from oslo_log import log as logging
from tempest import config
from tempest.lib.services import clients
from tempest import test

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BarbicanClientManager(test.BaseTestCase):
    """Class for interacting with the barbican service.

    This class is an abstraction for interacting with the barbican service.
    """

    credentials = ['primary',]

    @classmethod
    def setup_clients(cls, tempest_client_mgr):
        super(BarbicanClientManager, cls).setup_clients()
        if CONF.identity.auth_version == 'v3':
            auth_uri = CONF.identity.uri_v3
        else:
            auth_uri = CONF.identity.uri
        service_clients = clients.ServiceClients(
            tempest_client_mgr.credentials,
            auth_uri)
        cls.secret_client = service_clients.secret_v1.SecretClient(
            service='key-manager')

    @classmethod
    def ref_to_uuid(cls, href):
        return href.split('/')[-1]

    def store_secret(self):
        """Store a secret in barbican.

        :returns: The barbican secret_ref.
        """

        key = secrets.token_bytes(32)

        manila_secret = self.secret_client.create_secret(
            algorithm='AES',
            bit_length=256,
            secret_type='symmetric',
            payload=base64.b64encode(key).decode(),
            payload_content_type='application/octet-stream',
            payload_content_encoding='base64',
            mode='CBC'
        )
        LOG.debug('Manila Secret has ref %s', manila_secret.get('secret_ref'))
        return manila_secret.get('secret_ref')

    def delete_secret(self, secret_ref):
        self.secret_client.delete_secret(secret_ref)
