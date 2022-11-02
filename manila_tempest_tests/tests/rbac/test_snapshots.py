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


class ShareRbacSnapshotsTests(rbac_base.ShareRbacBaseTests,
                              metaclass=abc.ABCMeta):

    @classmethod
    def skip_checks(cls):
        super(ShareRbacSnapshotsTests, cls).skip_checks()
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    @classmethod
    def setup_clients(cls):
        super(ShareRbacSnapshotsTests, cls).setup_clients()
        cls.persona = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.client = cls.persona.share_v2.SharesV2Client()
        cls.alt_project_share_v2_client = (
            cls.os_project_alt_member.share_v2.SharesV2Client())

    @abc.abstractmethod
    def test_get_snapshot(self):
        pass

    @abc.abstractmethod
    def test_list_snapshot(self):
        pass

    @abc.abstractmethod
    def test_create_snapshot(self):
        pass

    @abc.abstractmethod
    def test_delete_snapshot(self):
        pass

    @abc.abstractmethod
    def test_force_delete_snapshot(self):
        pass

    @abc.abstractmethod
    def test_rename_snapshot(self):
        pass

    @abc.abstractmethod
    def test_reset_snapshot(self):
        pass


class TestProjectAdminTestsNFS(ShareRbacSnapshotsTests, base.BaseSharesTest):

    credentials = ['project_admin', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def setup_clients(cls):
        super(TestProjectAdminTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.persona, project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @classmethod
    def resource_setup(cls):
        super(TestProjectAdminTestsNFS, cls).resource_setup()
        share_type = cls.get_share_type()
        cls.share = cls.create_share(cls.client, share_type['id'])
        cls.alt_share = cls.create_share(
            cls.alt_project_share_v2_client, share_type['id'])

    @decorators.idempotent_id('e55b1a01-0fcb-42aa-8cc4-b041fc75f1e4')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot(self):
        snapshot = self.create_snapshot(
            self.share_member_client, self.share['id'])
        self.do_request(
            'get_snapshot', expected_status=200, snapshot_id=snapshot['id'])

        alt_snapshot = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'get_snapshot', expected_status=200,
            snapshot_id=alt_snapshot['id'])

    @decorators.idempotent_id('3b209017-f5ad-4daa-8932-582a75975bbe')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshot(self):
        snap = self.create_snapshot(
            self.share_member_client, self.share['id'])
        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])

        params = {"all_tenants": 1}
        snapshot_list = self.do_request(
            'list_snapshots', expected_status=200, params=params)['snapshots']
        snapshot_id_list = [
            s['id'] for s in snapshot_list
        ]

        self.assertIn(snap['id'], snapshot_id_list)
        self.assertIn(alt_snap['id'], snapshot_id_list)

    @decorators.idempotent_id('2b90d3e9-ec71-468a-86e9-e8955139ad48')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_snapshot(self):
        snapshot = self.do_request(
            'create_snapshot', expected_status=202,
            share_id=self.share['id'])['snapshot']
        waiters.wait_for_resource_status(
            self.client, snapshot['id'], 'available', resource_name='snapshot')
        self.addCleanup(self.delete_resource, self.client,
                        snapshot_id=snapshot['id'])

    @decorators.idempotent_id('6de91ee0-d27e-409a-957b-75489d4e7291')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_snapshot(self):
        snap = self.create_snapshot(
            self.share_member_client, self.share['id'])
        self.do_request(
            'delete_snapshot', expected_status=202, snap_id=snap['id'])
        self.client.wait_for_resource_deletion(snapshot_id=snap['id'])

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'delete_snapshot', expected_status=202,
            snap_id=alt_snap['id'])
        self.client.wait_for_resource_deletion(snapshot_id=alt_snap['id'])

    @decorators.idempotent_id('3ac10dfb-3445-4052-855a-a17056d16a9c')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_snapshot(self):
        snap = self.create_snapshot(
            self.share_member_client, self.share['id'])
        self.do_request(
            'force_delete', expected_status=202, s_id=snap['id'],
            s_type='snapshots')
        self.client.wait_for_resource_deletion(snapshot_id=snap['id'])

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'force_delete', expected_status=202,
            s_id=alt_snap['id'], s_type='snapshots')
        self.client.wait_for_resource_deletion(snapshot_id=alt_snap['id'])

    @decorators.idempotent_id('513c8fef-9597-4e6c-a811-fb89b456d457')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_rename_snapshot(self):
        snap = self.create_snapshot(
            self.share_member_client, self.share['id'])
        name = data_utils.rand_name("updated_snapshot")
        self.do_request(
            'rename_snapshot', expected_status=200, snapshot_id=snap['id'],
            name=name)

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'rename_snapshot', expected_status=200,
            snapshot_id=alt_snap['id'], name=name)

    @decorators.idempotent_id('a5e99bfb-8767-4680-9e39-bde767e4b8f8')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_snapshot(self):
        snap = self.create_snapshot(
            self.share_member_client, self.share['id'])
        self.do_request(
            'snapshot_reset_state', expected_status=202,
            snapshot_id=snap['id'], status='error')

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'snapshot_reset_state', expected_status=202,
            snapshot_id=alt_snap['id'], status='error')


class TestProjectMemberTestsNFS(ShareRbacSnapshotsTests, base.BaseSharesTest):

    credentials = ['project_member', 'project_alt_member']
    protocol = 'nfs'

    @classmethod
    def resource_setup(cls):
        super(TestProjectMemberTestsNFS, cls).resource_setup()
        share_type = cls.get_share_type()
        share_client = getattr(cls, 'share_member_client', cls.client)
        cls.share = cls.create_share(share_client, share_type['id'])
        cls.alt_share = cls.create_share(
            cls.alt_project_share_v2_client, share_type['id'])

    @decorators.idempotent_id('4ba65029-5c8b-4e96-940a-094d9f662cf6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot(self):
        share_client = getattr(self, 'share_member_client', self.client)
        snapshot = self.create_snapshot(share_client, self.share['id'])
        self.do_request(
            'get_snapshot', expected_status=200, snapshot_id=snapshot['id'])

        alt_snapshot = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'get_snapshot', expected_status=lib_exc.NotFound,
            snapshot_id=alt_snapshot['id'])

    @decorators.idempotent_id('0dcc1f68-86e2-432e-ad50-51c3cb78b986')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshot(self):
        share_client = getattr(self, 'share_member_client', self.client)
        snap = self.create_snapshot(share_client, self.share['id'])
        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])

        # We expect this key to be ignored since project_member isn't an admin
        params = {"all_tenants": 1}
        snapshot_list = self.do_request(
            'list_snapshots', expected_status=200, params=params)['snapshots']
        snapshot_id_list = [
            s['id'] for s in snapshot_list
        ]

        self.assertIn(snap['id'], snapshot_id_list)
        self.assertNotIn(alt_snap['id'], snapshot_id_list)

    @decorators.idempotent_id('d880b3f0-9027-4141-b28a-13e797919af7')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_create_snapshot(self):
        snapshot = self.do_request(
            'create_snapshot', expected_status=202,
            share_id=self.share['id'])['snapshot']
        waiters.wait_for_resource_status(
            self.client, snapshot['id'], 'available', resource_name='snapshot')
        self.addCleanup(self.delete_resource, self.client,
                        snapshot_id=snapshot['id'])

    @decorators.idempotent_id('e3fdd270-971f-4478-9e64-9bd11166bab6')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_snapshot(self):
        snap = self.create_snapshot(self.client, self.share['id'])
        self.do_request(
            'delete_snapshot', expected_status=202, snap_id=snap['id'])
        self.client.wait_for_resource_deletion(snapshot_id=snap['id'])

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'delete_snapshot', expected_status=lib_exc.NotFound,
            snap_id=alt_snap['id'])

    @decorators.idempotent_id('a93d6946-1d86-40a1-af01-90e843f8f575')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_snapshot(self):
        share_client = getattr(self, 'share_member_client', self.client)
        snap = self.create_snapshot(share_client, self.share['id'])
        self.do_request(
            'force_delete', expected_status=lib_exc.Forbidden, s_id=snap['id'],
            s_type='snapshots')

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'force_delete', expected_status=lib_exc.Forbidden,
            s_id=alt_snap['id'], s_type='snapshots')

    @decorators.idempotent_id('6da7bf79-25ab-4475-a5e0-1046781e9bc7')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_rename_snapshot(self):
        snap = self.create_snapshot(self.client, self.share['id'])
        name = data_utils.rand_name("updated_snapshot")
        self.do_request(
            'rename_snapshot', expected_status=200, snapshot_id=snap['id'],
            name=name)

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'rename_snapshot', expected_status=lib_exc.NotFound,
            snapshot_id=alt_snap['id'], name=name)

    @decorators.idempotent_id('22ba2e2e-6788-4075-9e92-af140d3b1238')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_snapshot(self):
        share_client = getattr(self, 'share_member_client', self.client)
        snap = self.create_snapshot(share_client, self.share['id'])
        self.do_request(
            'snapshot_reset_state', expected_status=lib_exc.Forbidden,
            snapshot_id=snap['id'], status='error')

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'snapshot_reset_state', expected_status=lib_exc.Forbidden,
            snapshot_id=alt_snap['id'], status='error')


class TestProjectReaderTestsNFS(TestProjectMemberTestsNFS):
    """Test suite for basic share snapshot operations by reader user

    In order to test certain share operations we must create a share snapshot
    resource for this. Since reader user is limited in resources creation, we
    are forced to use admin credentials, so we can test other share
    operations. In this class we use admin user to create a member user within
    reader project. That way we can perform a reader actions on this resource.
    """

    credentials = ['project_reader', 'project_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super(TestProjectReaderTestsNFS, cls).setup_clients()
        project_member = cls.setup_user_client(
            cls.os_project_admin,
            project_id=cls.persona.credentials.project_id)
        cls.share_member_client = project_member.share_v2.SharesV2Client()

    @classmethod
    def resource_setup(cls):
        super(TestProjectReaderTestsNFS, cls).resource_setup()
        share_type = cls.get_share_type()
        cls.share = cls.create_share(cls.share_member_client, share_type['id'])
        cls.alt_share = cls.create_share(
            cls.alt_project_share_v2_client, share_type['id'])

    @decorators.idempotent_id('46a09178-0264-4f56-9a5f-9a0583e72e4d')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_get_snapshot(self):
        super(TestProjectReaderTestsNFS, self).test_get_snapshot()

    @decorators.idempotent_id('fef4285a-a489-4fec-97af-763c2e33282e')
    @tc.attr(base.TAG_POSITIVE, base.TAG_API_WITH_BACKEND)
    def test_list_snapshot(self):
        super(TestProjectReaderTestsNFS, self).test_list_snapshot()

    @decorators.idempotent_id('17a80156-8cd6-420e-8ffe-97103edef4c3')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_create_snapshot(self):
        self.do_request(
            'create_snapshot', expected_status=lib_exc.Forbidden,
            share_id=self.share['id'])

    @decorators.idempotent_id('b0ca5483-ebdb-484c-a975-525e4d7deca2')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_delete_snapshot(self):
        snap = self.create_snapshot(self.share_member_client, self.share['id'])
        self.do_request(
            'delete_snapshot', expected_status=lib_exc.Forbidden,
            snap_id=snap['id'])

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'delete_snapshot', expected_status=lib_exc.NotFound,
            snap_id=alt_snap['id'])

    @decorators.idempotent_id('ed0af390-e3d0-432b-9147-c0d569181b92')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_force_delete_snapshot(self):
        super(TestProjectReaderTestsNFS, self).test_force_delete_snapshot()

    @decorators.idempotent_id('21db863f-c2a4-4d07-b435-2a000255ea3b')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_rename_snapshot(self):
        snap = self.create_snapshot(self.share_member_client, self.share['id'])
        name = data_utils.rand_name("updated_snapshot")
        self.do_request(
            'rename_snapshot', expected_status=lib_exc.Forbidden,
            snapshot_id=snap['id'], name=name)

        alt_snap = self.create_snapshot(
            self.alt_project_share_v2_client, self.alt_share['id'])
        self.do_request(
            'rename_snapshot', expected_status=lib_exc.NotFound,
            snapshot_id=alt_snap['id'], name=name)

    @decorators.idempotent_id('b8c9c9a4-3b2a-4b1c-80d8-2ec87d708111')
    @tc.attr(base.TAG_NEGATIVE, base.TAG_API_WITH_BACKEND)
    def test_reset_snapshot(self):
        super(TestProjectReaderTestsNFS, self).test_reset_snapshot()


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
