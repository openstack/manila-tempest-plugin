# Copyright 2015 Deutsche Telekom AG
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

from oslo_log import log
import six
from six.moves.urllib.request import urlopen

from manila_tempest_tests.common import constants
from manila_tempest_tests.common import remote_client
from manila_tempest_tests.tests.api import base
from manila_tempest_tests.tests.scenario import manager
from manila_tempest_tests import utils

from tempest.common import waiters
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions

from tempfile import mkstemp

CONF = config.CONF
LOG = log.getLogger(__name__)


class ShareScenarioTest(manager.NetworkScenarioTest):
    """Provide harness to do Manila scenario tests."""

    credentials = ('admin', 'primary')
    protocol = None
    ip_version = 4

    @property
    def ipv6_enabled(self):
        return self.ip_version == 6

    @classmethod
    def setup_clients(cls):
        super(ShareScenarioTest, cls).setup_clients()

        # Manila clients
        cls.shares_client = cls.os_primary.share_v1.SharesClient()
        cls.shares_v2_client = cls.os_primary.share_v2.SharesV2Client()
        cls.shares_admin_client = cls.os_admin.share_v1.SharesClient()
        cls.shares_admin_v2_client = cls.os_admin.share_v2.SharesV2Client()

    @classmethod
    def skip_checks(cls):
        super(ShareScenarioTest, cls).skip_checks()
        if not CONF.service_available.manila:
            raise cls.skipException("Manila support is required")
        if cls.ip_version == 6 and not CONF.share.run_ipv6_tests:
            raise cls.skipException("IPv6 tests are disabled")
        if cls.protocol not in CONF.share.enable_protocols:
            message = "%s tests are disabled" % cls.protocol
            raise cls.skipException(message)

    def setUp(self):
        base.verify_test_has_appropriate_tags(self)
        super(ShareScenarioTest, self).setUp()

        self.image_id = None
        # Setup image and flavor the test instance
        # Support both configured and injected values
        self.floating_ips = {}
        self.storage_network_nic_ips = {}

        if not hasattr(self, 'flavor_ref'):
            self.flavor_ref = CONF.share.client_vm_flavor_ref

        if CONF.share.image_with_share_tools == 'centos':
            self.image_ref = self._create_centos_based_glance_image()
        elif CONF.share.image_with_share_tools:
            images = self.compute_images_client.list_images()["images"]
            for img in images:
                if img["name"] == CONF.share.image_with_share_tools:
                    self.image_id = img['id']
                    break
            if not self.image_id:
                msg = ("Image %s not found. Expecting an image including "
                       "required share tools." %
                       CONF.share.image_with_share_tools)
                raise exceptions.InvalidConfiguration(message=msg)
        self.ssh_user = CONF.share.image_username
        LOG.debug('Starting test for i:{image_id}, f:{flavor}. '
                  'user: {ssh_user}'.format(image_id=self.image_id,
                                            flavor=self.flavor_ref,
                                            ssh_user=self.ssh_user))

        self.security_group = self._create_security_group()
        self.network = self._create_network(namestart="manila-share")
        self.subnet = self._create_subnet(
            network=self.network,
            namestart="manila-share-sub",
            ip_version=self.ip_version,
            use_default_subnetpool=self.ipv6_enabled)
        router = self._get_router()
        self._create_router_interface(subnet_id=self.subnet['id'],
                                      router_id=router['id'])

        self.storage_network = (
            self._get_network_by_name_or_id(CONF.share.storage_network)
            if CONF.share.storage_network else None
        )
        self.storage_network_name = (
            self.storage_network['name'] if self.storage_network else None
        )

        if CONF.share.multitenancy_enabled:
            # Skip if DHSS=False
            self.share_network = self.create_share_network()

    def mount_share(self, location, remote_client, target_dir=None):
        raise NotImplementedError

    def allow_access(self, **kwargs):
        raise NotImplementedError

    def unmount_share(self, remote_client, target_dir=None):
        target_dir = target_dir or "/mnt"
        remote_client.exec_command("sudo umount %s" % target_dir)

    def create_share_network(self):
        share_network = self._create_share_network(
            neutron_net_id=self.network['id'],
            neutron_subnet_id=self.subnet['id'],
            name=data_utils.rand_name("sn-name"))
        return share_network

    def boot_instance(self, wait_until="ACTIVE"):
        # In case of multiple instances, use a single keypair to prevent a keys
        # mismatch.
        if not hasattr(self, 'keypair'):
            self.keypair = self.create_keypair()
        security_groups = [{'name': self.security_group['name']}]
        networks = [{'uuid': self.network['id']}]
        if self.storage_network:
            networks.append({'uuid': self.storage_network['id']})

        create_kwargs = {
            'key_name': self.keypair['name'],
            'security_groups': security_groups,
            'wait_until': wait_until,
            'networks': networks,
        }
        instance = self.create_server(
            image_id=self.image_id, flavor=self.flavor_ref, **create_kwargs)
        return instance

    def init_remote_client(self, instance):
        server_ip = None
        if self.ipv6_enabled:
            server_ip = self._get_server_ip(instance, ip_version=6)
        if not server_ip:
            ip_addr = self._get_server_ip(instance)
            # Obtain a floating IP
            floating_ip = self.create_floating_ip(instance, ip_addr=ip_addr)
            self.floating_ips[instance['id']] = floating_ip
            server_ip = floating_ip['floating_ip_address']

            if self.storage_network:
                storage_net_nic = instance['addresses'].get(
                    self.storage_network_name)
                if storage_net_nic:
                    self.storage_network_nic_ips[instance['id']] = (
                        storage_net_nic[0]['addr']
                    )
            # Attach a floating IP
            self.compute_floating_ips_client.associate_floating_ip_to_server(
                floating_ip['floating_ip_address'], instance['id'])

        self.assertIsNotNone(server_ip)
        # Check ssh
        remote_client = self.get_remote_client(
            server_or_ip=server_ip,
            username=self.ssh_user,
            private_key=self.keypair['private_key'])

        # NOTE(u_glide): Workaround for bug #1465682
        remote_client = remote_client.ssh_client

        self.share = self.shares_client.get_share(self.share['id'])
        return remote_client

    def write_data_to_mounted_share(self, escaped_string, remote_client,
                                    mount_point='/mnt/t1'):
        remote_client.exec_command("echo \"{escaped_string}\" "
                                   "| sudo tee {mount_point} && sudo sync"
                                   .format(escaped_string=escaped_string,
                                           mount_point=mount_point))

    def write_data_to_mounted_share_using_dd(self, remote_client,
                                             output_file,
                                             block_size,
                                             block_count,
                                             input_file='/dev/zero'):
        """Writes data to mounted share using dd command

        Example Usage for writing 512Mb to a file on /mnt/
        (remote_client, block_size=1024, block_count=512000,
        output_file='/mnt/512mb_of_zeros', input_file='/dev/zero')

        For more information, refer to the dd man page.

        :param remote_client: An SSH client connection to the Nova instance
        :param block_size: The size of an individual block in bytes
        :param block_count: The number of blocks to write
        :param output_file: Path to the file to be written
        :param input_file: Path to the file to read from
        """
        block_count = int(block_count)
        remote_client.exec_command(
            "sudo sh -c \"dd bs={} count={} if={} of={} conv=fsync"
            " iflag=fullblock\""
            .format(block_size, block_count, input_file, output_file))

    def read_data_from_mounted_share(self,
                                     remote_client,
                                     mount_point='/mnt/t1'):
        data = remote_client.exec_command("sudo cat {mount_point}"
                                          .format(mount_point=mount_point))
        return data.rstrip()

    def migrate_share(self, share_id, dest_host, status,
                      force_host_assisted=False):
        share = self._migrate_share(
            share_id, dest_host, status, force_host_assisted,
            self.shares_admin_v2_client)
        return share

    def migration_complete(self, share_id, dest_host):
        return self._migration_complete(share_id, dest_host)

    def create_share(self, **kwargs):
        kwargs.update({
            'share_protocol': self.protocol,
        })
        if not ('share_type_id' in kwargs or 'snapshot_id' in kwargs):
            default_share_type_id = self.get_share_type()['id']
            kwargs.update({'share_type_id': default_share_type_id})
        if CONF.share.multitenancy_enabled:
            kwargs.update({'share_network_id': self.share_network['id']})
        self.share = self._create_share(**kwargs)
        return self.share

    def get_remote_client(self, *args, **kwargs):
        if not CONF.share.image_with_share_tools:
            return super(ShareScenarioTest,
                         self).get_remote_client(*args, **kwargs)
        # NOTE(u_glide): We need custom implementation of this method until
        # original implementation depends on CONF.compute.ssh_auth_method
        # option.
        server_or_ip = kwargs['server_or_ip']
        if isinstance(server_or_ip, six.string_types):
            ip = server_or_ip
        else:
            addr = server_or_ip['addresses'][
                CONF.validation.network_for_ssh][0]
            ip = addr['addr']

        # NOTE(u_glide): Both options (pkey and password) are required here to
        # support service images without Nova metadata support
        client_params = {
            'username': kwargs['username'],
            'password': CONF.share.image_password,
            'pkey': kwargs.get('private_key'),
        }

        linux_client = remote_client.RemoteClient(ip, **client_params)
        try:
            linux_client.validate_authentication()
        except Exception:
            LOG.exception('Initializing SSH connection to %s failed', ip)
            self._log_console_output()
            raise

        return linux_client

    def allow_access_ip(self, share_id, ip=None, instance=None,
                        access_level="rw", cleanup=True, snapshot=None,
                        client=None):
        client = client or self.shares_v2_client
        if instance and not ip:
            try:
                net_addresses = instance['addresses']
                first_address = list(net_addresses.values())[0][0]
                ip = first_address['addr']
            except Exception:
                LOG.debug("Instance has no valid IP address: %s", instance)
                # In case on an error ip will be still none
                LOG.exception("Instance has no valid IP address. "
                              "Falling back to default")
        if not ip:
            ip = '::/0' if self.ipv6_enabled else '0.0.0.0/0'

        if snapshot:
            self._allow_access_snapshot(snapshot['id'], access_type='ip',
                                        access_to=ip, cleanup=cleanup,
                                        client=client)
        else:
            return self._allow_access(share_id, access_type='ip',
                                      access_level=access_level, access_to=ip,
                                      cleanup=cleanup,
                                      client=client)

    def deny_access(self, share_id, access_rule_id, client=None):
        """Deny share access

        :param share_id: id of the share
        :param access_rule_id: id of the rule that will be deleted
        """
        client = client or self.shares_client
        client.delete_access_rule(share_id, access_rule_id)
        self.shares_v2_client.wait_for_share_status(
            share_id, "active", status_attr='access_rules_status')

    def provide_access_to_auxiliary_instance(self, instance, share=None,
                                             snapshot=None, access_level='rw',
                                             client=None):
        share = share or self.share
        client = client or self.shares_v2_client
        if not CONF.share.multitenancy_enabled:
            if self.ipv6_enabled and not self.storage_network:
                server_ip = self._get_server_ip(instance, ip_version=6)
            else:
                server_ip = (
                    CONF.share.override_ip_for_nfs_access
                    or self.storage_network_nic_ips.get(instance['id'])
                    or self.floating_ips[instance['id']]['floating_ip_address']
                )

            self.assertIsNotNone(server_ip)
            return self.allow_access_ip(
                share['id'], ip=server_ip,
                instance=instance, cleanup=False, snapshot=snapshot,
                access_level=access_level, client=client)
        else:
            return self.allow_access_ip(
                share['id'], instance=instance, cleanup=False,
                snapshot=snapshot, access_level=access_level, client=client)

    def provide_access_to_client_identified_by_cephx(self, share=None,
                                                     access_level='rw',
                                                     access_to=None,
                                                     remote_client=None,
                                                     locations=None,
                                                     client=None,
                                                     oc_size=20971520):
        share = share or self.share
        client = client or self.shares_v2_client
        access_to = access_to or data_utils.rand_name(
            self.__class__.__name__ + '-cephx-id')
        # Check if access is already granted to the client
        access = self.shares_v2_client.list_access_rules(
            share['id'], metadata={'metadata': {'access_to': access_to}})
        access = access[0] if access else None

        if not access:
            access = self._allow_access(
                share['id'], access_level=access_level, access_to=access_to,
                access_type="cephx", cleanup=False, client=client)
            # Set metadata to access rule to be filtered if necessary.
            # This is necessary to prevent granting access to a client who
            # already has.
            self.shares_v2_client.update_access_metadata(
                metadata={"access_to": "{}".format(access_to)},
                access_id=access['id'])
        get_access = self.shares_v2_client.get_access(access['id'])
        # Set 'access_key' and 'access_to' attributes for being use in mount
        # operation.
        setattr(self, 'access_key', get_access['access_key'])
        setattr(self, 'access_to', access_to)

        remote_client.exec_command(
            "sudo crudini --set {access_to}.keyring client.{access_to} key "
            "{access_key}"
            .format(access_to=access_to, access_key=self.access_key))
        remote_client.exec_command(
            "sudo crudini --set ceph.conf client \"client quota\" true")
        remote_client.exec_command(
            "sudo crudini --set ceph.conf client \"client oc size\" {}"
            .format(oc_size))
        if not isinstance(locations, list):
            locations = [locations]
        remote_client.exec_command(
            "sudo crudini --set ceph.conf client \"mon host\" {}"
            .format(locations[0].split(':/')[0]))
        return access

    def wait_for_active_instance(self, instance_id):
        waiters.wait_for_server_status(
            self.os_primary.servers_client, instance_id, "ACTIVE")
        return self.os_primary.servers_client.show_server(
            instance_id)["server"]

    def get_share_type(self):
        if CONF.share.default_share_type_name:
            return self.shares_client.get_share_type(
                CONF.share.default_share_type_name)['share_type']
        return self._create_share_type(
            data_utils.rand_name("share_type"),
            extra_specs={
                'snapshot_support': CONF.share.capability_snapshot_support,
                'driver_handles_share_servers': CONF.share.multitenancy_enabled
            },)['share_type']

    def get_share_export_locations(self, share):
        if utils.is_microversion_lt(CONF.share.max_api_microversion, "2.9"):
            locations = share['export_locations']
        else:
            exports = self.shares_v2_client.list_share_export_locations(
                share['id'])
            locations = [x['path'] for x in exports]
        return locations

    def _get_snapshot_export_locations(self, snapshot):
        exports = (self.shares_v2_client.
                   list_snapshot_export_locations(snapshot['id']))
        locations = [x['path'] for x in exports]

        return locations

    def _get_server_ip(self, instance, ip_version=4):
        ip_addrs = []
        for network_name, nic_list in instance['addresses'].items():
            if network_name == self.storage_network_name:
                continue
            for nic_data in nic_list:
                if nic_data['version'] == ip_version:
                    ip_addrs.append(nic_data['addr'])
        return ip_addrs[0] if ip_addrs else None

    def _create_share(self, share_protocol=None, size=None, name=None,
                      snapshot_id=None, description=None, metadata=None,
                      share_network_id=None, share_type_id=None,
                      client=None, cleanup=True):
        """Create a share

        :param share_protocol: NFS or CIFS
        :param size: size in GB
        :param name: name of the share (otherwise random)
        :param snapshot_id: snapshot as basis for the share
        :param description: description of the share
        :param metadata: adds additional metadata
        :param share_network_id: id of network to be used
        :param share_type_id: type of the share to be created
        :param client: client object
        :param cleanup: default: True
        :returns: a created share
        """
        client = client or self.shares_client
        description = description or "Tempest's share"
        if not name:
            name = data_utils.rand_name("manila-scenario")
        if CONF.share.multitenancy_enabled:
            share_network_id = (share_network_id or client.share_network_id)
        else:
            share_network_id = None
        metadata = metadata or {}
        kwargs = {
            'share_protocol': share_protocol,
            'size': size or CONF.share.share_size,
            'name': name,
            'snapshot_id': snapshot_id,
            'description': description,
            'metadata': metadata,
            'share_network_id': share_network_id,
            'share_type_id': share_type_id,
        }
        share = self.shares_client.create_share(**kwargs)

        if cleanup:
            self.addCleanup(client.wait_for_resource_deletion,
                            share_id=share['id'])
            self.addCleanup(client.delete_share,
                            share['id'])

        client.wait_for_share_status(share['id'], 'available')
        return share

    def _create_snapshot(self, share_id, client=None, **kwargs):
        client = client or self.shares_v2_client
        snapshot = client.create_snapshot(share_id, **kwargs)
        self.addCleanup(
            client.wait_for_resource_deletion, snapshot_id=snapshot['id'])
        self.addCleanup(client.delete_snapshot, snapshot['id'])
        client.wait_for_snapshot_status(snapshot["id"], "available")
        return snapshot

    def _wait_for_share_server_deletion(self, sn_id, client=None):
        """Wait for a share server to be deleted

        :param sn_id: shared network id
        :param client: client object
        """
        client = client or self.shares_admin_client
        servers = client.list_share_servers(
            search_opts={"share_network": sn_id})
        for server in servers:
            client.delete_share_server(server['id'])
        for server in servers:
            client.wait_for_resource_deletion(server_id=server['id'])

    def _create_share_network(self, client=None, **kwargs):
        """Create a share network

        :param client: client object
        :returns: a created share network
        """

        client = client or self.shares_client
        sn = client.create_share_network(**kwargs)

        self.addCleanup(client.wait_for_resource_deletion,
                        sn_id=sn['id'])
        self.addCleanup(client.delete_share_network,
                        sn['id'])
        self.addCleanup(self._wait_for_share_server_deletion,
                        sn['id'])
        return sn

    def _allow_access(self, share_id, client=None, access_type="ip",
                      access_level="rw", access_to="0.0.0.0", cleanup=True):
        """Allow share access

        :param share_id: id of the share
        :param client: client object
        :param access_type: "ip", "user" or "cert"
        :param access_level: "rw" or "ro"
        :param access_to
        :returns: access object
        """
        client = client or self.shares_v2_client
        access = client.create_access_rule(share_id, access_type, access_to,
                                           access_level)

        client.wait_for_share_status(
            share_id, "active", status_attr='access_rules_status')

        if cleanup:
            self.addCleanup(client.delete_access_rule, share_id, access['id'])
        return access

    def _allow_access_snapshot(self, snapshot_id, access_type="ip",
                               access_to="0.0.0.0/0", cleanup=True,
                               client=None):
        """Allow snapshot access

        :param snapshot_id: id of the snapshot
        :param access_type: "ip", "user" or "cert"
        :param access_to
        :param client: shares client, normal/admin
        :returns: access object
        """
        client = client or self.shares_v2_client
        access = client.create_snapshot_access_rule(
            snapshot_id, access_type, access_to)

        if cleanup:
            self.addCleanup(client.delete_snapshot_access_rule,
                            snapshot_id, access['id'])

        client.wait_for_snapshot_access_rule_status(
            snapshot_id, access['id'])

        return access

    def _create_router_interface(self, subnet_id, client=None, router_id=None):
        """Create a router interface

        :param subnet_id: id of the subnet
        :param client: client object
        """
        if not client:
            client = self.routers_client
        if not router_id:
            router_id = self._get_router()['id']
        client.add_router_interface(router_id, subnet_id=subnet_id)
        self.addCleanup(
            client.remove_router_interface, router_id, subnet_id=subnet_id)

    def _migrate_share(self, share_id, dest_host, status, force_host_assisted,
                       client=None):
        client = client or self.shares_admin_v2_client
        client.migrate_share(
            share_id, dest_host, writable=False, preserve_metadata=False,
            nondisruptive=False, preserve_snapshots=False,
            force_host_assisted_migration=force_host_assisted)
        share = client.wait_for_migration_status(share_id, dest_host, status)
        return share

    def _migration_complete(self, share_id, dest_host, client=None, **kwargs):
        client = client or self.shares_admin_v2_client
        client.migration_complete(share_id, **kwargs)
        share = client.wait_for_migration_status(
            share_id, dest_host, constants.TASK_STATE_MIGRATION_SUCCESS,
            **kwargs)
        return share

    def _create_share_type(self, name, is_public=True, **kwargs):
        share_type = self.shares_admin_v2_client.create_share_type(name,
                                                                   is_public,
                                                                   **kwargs)
        self.addCleanup(self.shares_admin_v2_client.delete_share_type,
                        share_type['share_type']['id'])
        return share_type

    def _create_centos_based_glance_image(self):
        imagepath = mkstemp(suffix='.qcow2')[1]
        imagefile = open(imagepath, 'wb+')
        image_response = urlopen('http://cloud.centos.org/centos/7/images/' +
                                 'CentOS-7-x86_64-GenericCloud.qcow2')

        LOG.info('Downloading CentOS7 image')
        while True:
            imagecopy = image_response.read(100 * 1024 * 1024)
            if imagecopy == '':
                break
            imagefile.write(imagecopy)

        imagefile.close()

        LOG.info('Creating Glance image using the downloaded image file')
        return self._image_create('centos', 'bare', imagepath, 'qcow2')

    def get_share_export_location_for_mount(self, share):
        exports = self.get_user_export_locations(
            share=share,
            error_on_invalid_ip_version=True)
        return exports[0]

    def get_user_export_locations(self, share=None, snapshot=None,
                                  error_on_invalid_ip_version=False):
        locations = None
        if share:
            locations = self.get_share_export_locations(share)
        elif snapshot:
            locations = self._get_snapshot_export_locations(snapshot)

        self.assertNotEmpty(locations)
        if self.protocol != 'cephfs':
            locations = self._get_export_locations_according_to_ip_version(
                locations, error_on_invalid_ip_version)
            self.assertNotEmpty(locations)

        return locations

    def _get_export_locations_according_to_ip_version(
            self, all_locations, error_on_invalid_ip_version):
        locations = [
            x for x in all_locations
            if self.get_ip_and_version_from_export_location(
                x)[1] == self.ip_version]

        if len(locations) == 0 and not error_on_invalid_ip_version:
            message = ("Configured backend does not support "
                       "ip_version %s" % self.ip_version)
            raise self.skipException(message)
        return locations

    def get_ip_and_version_from_export_location(self, export):
        export = export.replace('[', '').replace(']', '')
        if self.protocol == 'nfs' and ':/' in export:
            ip = export.split(':/')[0]
            version = 6 if ip.count(':') > 1 else 4
        elif self.protocol == 'cifs' and export.startswith(r'\\'):
            ip = export.split('\\')[2]
            version = 6 if (ip.count(':') > 1 or
                            ip.endswith('ipv6-literal.net')) else 4
        else:
            message = ("Protocol %s is not supported" % self.protocol)
            raise self.skipException(message)
        return ip, version


class BaseShareCEPHFSTest(ShareScenarioTest):

    def allow_access(self, access_level='rw', **kwargs):
        return self.provide_access_to_client_identified_by_cephx(
            remote_client=kwargs['remote_client'],
            locations=kwargs['locations'], access_level=access_level)

    def _fuse_client(self, mountpoint, remote_client, target_dir, access_to):
        remote_client.exec_command(
            "sudo ceph-fuse {target_dir} --id={access_to} --conf=ceph.conf "
            "--keyring={access_to}.keyring --client-mountpoint={mountpoint}"
            .format(target_dir=target_dir, access_to=access_to,
                    mountpoint=mountpoint))

    def mount_share(self, location, remote_client, target_dir=None,
                    access_to=None):
        target_dir = target_dir or "/mnt"
        access_to = access_to or self.access_to
        mountpoint = location.split(':')[-1]
        if getattr(self, 'mount_client', None):
            return self._fuse_client(mountpoint, remote_client, target_dir,
                                     access_to=access_to)
        remote_client.exec_command(
            "sudo mount -t ceph {location} {target_dir} -o name={access_to},"
            "secret={access_key}"
            .format(location=location, target_dir=target_dir,
                    access_to=access_to, access_key=self.access_key))

    def unmount_share(self, remote_client, target_dir=None):
        target_dir = target_dir or "/mnt"
        if getattr(self, 'mount_client', None):
            return remote_client.exec_command(
                "sudo fusermount -uz %s" % target_dir)
        super(BaseShareCEPHFSTest, self).unmount_share(remote_client)
