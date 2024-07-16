# Copyright 2014 Mirantis Inc.
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

from oslo_config import cfg
from oslo_config import types

service_option = cfg.BoolOpt("manila",
                             default=True,
                             help="Whether or not manila is expected to be "
                                  "available")

manila_scope_enforcement = cfg.BoolOpt('manila',
                                       default=False,
                                       help="Does the Share service API "
                                            "policies enforce scope? "
                                            "This configuration value should "
                                            "be same as manila.conf: "
                                            "[oslo_policy].enforce_scope "
                                            "option.")

share_group = cfg.OptGroup(name="share", title="Share Service Options")

ShareGroup = [
    cfg.StrOpt("min_api_microversion",
               default="2.0",
               help="The minimum api microversion is configured to be the "
                    "value of the minimum microversion supported by Manila. "
                    "This value is only used to validate the versions "
                    "response from Manila."),
    cfg.StrOpt("max_api_microversion",
               default="2.85",
               help="The maximum api microversion is configured to be the "
                    "value of the latest microversion supported by Manila."),
    cfg.StrOpt("region",
               default="",
               help="The share region name to use. If empty, the value "
                    "of identity.region is used instead. If no such region "
                    "is found in the service catalog, the first found one is "
                    "used."),
    cfg.StrOpt("catalog_type",
               default="share",
               help="Catalog type of the Share service."),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for the share service."),
    cfg.BoolOpt("multitenancy_enabled",
                default=True,
                help="This option used to determine backend driver type, "
                     "multitenant driver uses share-networks, but "
                     "single-tenant doesn't."),
    cfg.BoolOpt("create_networks_when_multitenancy_enabled",
                default=True,
                help="This option is used only when other "
                     "'multitenancy_enabled' option is set to 'True'. "
                     "If this one is set to True, then tempest will create "
                     "neutron networks for each new manila share-network "
                     "it creates. Else it will use manila share-networks with "
                     "empty values (case of StandAloneNetworkPlugin and "
                     "NeutronSingleNetworkPlugin)."),
    cfg.ListOpt("enable_protocols",
                default=["nfs", "cifs"],
                help="First value of list is protocol by default, "
                     "items of list show enabled protocols at all."),
    cfg.ListOpt("enable_ip_rules_for_protocols",
                default=["nfs", "cifs", ],
                help="Selection of protocols, that should "
                     "be covered with ip rule tests"),
    cfg.ListOpt("enable_user_rules_for_protocols",
                default=[],
                help="Selection of protocols, that should "
                     "be covered with user rule tests"),
    cfg.ListOpt("enable_cert_rules_for_protocols",
                default=["glusterfs", ],
                help="Protocols that should be covered with cert rule tests."),
    cfg.ListOpt("enable_cephx_rules_for_protocols",
                default=["cephfs", ],
                help="Protocols to be covered with cephx rule tests."),
    cfg.StrOpt("username_for_user_rules",
               default="Administrator",
               help="Username, that will be used in user tests."),
    cfg.StrOpt("override_ip_for_nfs_access",
               help="Forces access rules to be as specified on NFS scenario"
                    " tests. This can used for working around multiple "
                    "NATs between the VMs and the storage controller."),
    cfg.StrOpt("storage_network",
               help="Name or UUID of a neutron network that is used to access "
                    "shared file systems over. If specified, test virtual "
                    "machines are created with two NICs, the primary NIC is "
                    "attached to the private project network and the "
                    "secondary NIC is attached to the specified storage "
                    "network. If using NFS, access control is done with the "
                    "help of the IP address assigned to the virtual machine's "
                    "storage network NIC."),
    cfg.ListOpt("enable_ro_access_level_for_protocols",
                default=["nfs", ],
                help="List of protocols to run tests with ro access level."),

    # Capabilities
    cfg.StrOpt("capability_storage_protocol",
               deprecated_name="storage_protocol",
               default="NFS_CIFS",
               help="Backend protocol to target when creating volume types."),
    cfg.BoolOpt("capability_snapshot_support",
                help="Defines extra spec that satisfies specific back end "
                     "capability called 'snapshot_support' and will be used "
                     "for setting up custom share type. Defaults to value of "
                     "other config option 'run_snapshot_tests'."),
    cfg.BoolOpt("capability_create_share_from_snapshot_support",
                help="Defines extra spec that satisfies specific back end "
                     "capability called 'create_share_from_snapshot_support' "
                     "and will be used for setting up a custom share type. "
                     "Defaults to the value of run_snapshot_tests. Set it to "
                     "False if the driver being tested does not support "
                     "creating shares from snapshots."),
    cfg.BoolOpt("capability_revert_to_snapshot_support",
                deprecated_for_removal=True,
                deprecated_reason="Redundant configuration option. Please use "
                                  "'run_revert_to_snapshot_tests' config "
                                  "option instead.",
                help="Defines extra spec that satisfies specific back end "
                     "capability called 'revert_to_snapshot_support' "
                     "and will be used for setting up custom share type. "
                     "Defaults to the value of run_revert_to_snapshot_tests."),
    cfg.StrOpt("capability_sg_consistent_snapshot_support",
               choices=["host", "pool", None],
               help="Backend capability to create consistent snapshots of "
                    "share group members. Will be used with creation "
                    "of new share group types as group spec."),
    cfg.BoolOpt("capability_thin_provisioned",
                default=False,
                help="Defines whether to create shares as thin provisioned, "
                     "adding the extra spec 'thin_provisioning' as 'True' for "
                     "setting up the custom share types. It may be useful to "
                     "run tempest with  back end storage systems without much "
                     "space. Take care enabling it, the manila scheduler "
                     "capability filter will request this capability in all "
                     "share types and the the capacity filter will allow "
                     "oversubscription."),
    cfg.StrOpt("share_network_id",
               default="",
               help="Some backend drivers requires share network "
                    "for share creation. Share network id, that will be "
                    "used for shares. If not set, it won't be used. Setting "
                    "this option to a valid share network ID will mean that "
                    "the value of create_networks_when_multitenancy_enabled "
                    "should be False."),
    cfg.StrOpt("alt_share_network_id",
               default="",
               help="Share network id, that will be used for shares"
                    " in alt tenant. If not set, it won't be used. Setting "
                    "this option to a valid share network ID will mean that "
                    "the value of create_networks_when_multitenancy_enabled "
                    "should be False."),
    cfg.StrOpt("admin_share_network_id",
               default="",
               help="Share network id, that will be used for shares"
                    " in admin tenant. If not set, it won't be used. Setting "
                    "this option to a valid share network ID will mean that "
                    "the value of create_networks_when_multitenancy_enabled "
                    "should be False."),
    cfg.BoolOpt("multi_backend",
                default=False,
                help="Runs Manila multi-backend tests."),
    cfg.ListOpt("backend_names",
                default=[],
                help="Names of share backends, that will be used with "
                     "multibackend tests. Tempest will use first two values."),
    cfg.IntOpt("share_creation_retry_number",
               default=0,
               help="Defines number of retries for share creation. "
                    "It is useful to avoid failures caused by unstable "
                    "environment."),
    cfg.IntOpt("build_interval",
               default=3,
               help="Time in seconds between share availability checks."),
    cfg.IntOpt("build_timeout",
               default=500,
               help="Timeout in seconds to wait for a share to become"
                    "available."),
    cfg.BoolOpt("suppress_errors_in_cleanup",
                default=False,
                help="Whether to suppress errors with clean up operation "
                     "or not. There are cases when we may want to skip "
                     "such errors and catch only test errors."),
    cfg.MultiOpt("security_service",
                 item_type=types.Dict(),
                 secret=True,
                 help="This option enables specifying security service "
                      "parameters needed to create security services "
                      "dynamically in order to run the tempest tests. "
                      "The configured security service must be reachable by "
                      "the project share networks created by the tests. So, "
                      "ideally project networks must be able to route to the "
                      "network where the pre-existing security services has "
                      "been deployed. The set of parameters that can be "
                      "configured is the same used in the security service "
                      "creation. You can repeat this option many times, and "
                      "each entry takes the standard dict config parameters: "
                      "security_service = "
                      "ss_type:<ldap, kerberos or active_directory>, "
                      "ss_dns_ip:value, ss_user:value, ss_password=value, "
                      "ss_domain:value, ss_server:value"),

    # Switching ON/OFF test suites filtered by features
    cfg.BoolOpt("run_quota_tests",
                default=True,
                help="Defines whether to run quota tests or not."),
    cfg.BoolOpt("run_extend_tests",
                default=True,
                help="Defines whether to run share extend tests or not. "
                     "Disable this feature if used driver doesn't "
                     "support it."),
    cfg.BoolOpt("run_shrink_tests",
                default=True,
                help="Defines whether to run share shrink tests or not. "
                     "Disable this feature if used driver doesn't "
                     "support it."),
    cfg.BoolOpt("run_snapshot_tests",
                default=True,
                help="Defines whether to run tests that use share snapshots "
                     "or not. Disable this feature if used driver doesn't "
                     "support it."),
    cfg.BoolOpt("run_revert_to_snapshot_tests",
                default=False,
                help="Defines whether to run tests that revert shares "
                     "to snapshots or not. Enable this feature if used "
                     "driver supports it."),
    cfg.BoolOpt("run_share_group_tests",
                default=True,
                deprecated_name="run_consistency_group_tests",
                help="Defines whether to run share group tests or not."),
    cfg.BoolOpt("run_replication_tests",
                default=False,
                help="Defines whether to run replication tests or not. "
                     "Enable this feature if the driver is configured "
                     "for replication."),
    cfg.BoolOpt("run_multiple_share_replicas_tests",
                default=True,
                help="Defines whether to run multiple replicas creation test "
                     "or not. Enable this if the driver can create more than "
                     "one replica for a share."),
    cfg.BoolOpt("run_host_assisted_migration_tests",
                deprecated_name="run_migration_tests",
                default=False,
                help="Enable or disable host-assisted migration tests."),
    cfg.BoolOpt("run_driver_assisted_migration_tests",
                deprecated_name="run_migration_tests",
                default=False,
                help="Enable or disable driver-assisted migration tests."),
    cfg.BoolOpt("run_migration_with_preserve_snapshots_tests",
                default=False,
                help="Enable or disable migration with "
                     "preserve_snapshots tests set to True."),
    cfg.BoolOpt("run_driver_assisted_backup_tests",
                default=False,
                help="Enable or disable share backup tests."),
    cfg.BoolOpt("run_manage_unmanage_tests",
                default=False,
                help="Defines whether to run manage/unmanage tests or not. "
                     "These test may leave orphaned resources, so be careful "
                     "enabling this opt."),
    cfg.BoolOpt("run_manage_unmanage_snapshot_tests",
                default=False,
                help="Defines whether to run manage/unmanage snapshot tests "
                     "or not. These tests may leave orphaned resources, so be "
                     "careful enabling this opt."),
    cfg.BoolOpt("run_mount_snapshot_tests",
                default=False,
                help="Enable or disable mountable snapshot tests."),
    cfg.BoolOpt("run_create_share_from_snapshot_in_another_pool_or_az_tests",
                default=False,
                help="Defines whether to run tests that create share from "
                     "snapshots in another pool or az. Enable this "
                     "option if the used driver supports it."),
    cfg.BoolOpt("run_share_server_migration_tests",
                default=False,
                help="Defines whether to run share servers migration tests. "
                     "Enable this option if the used driver supports it."),
    cfg.BoolOpt("run_share_server_multiple_subnet_tests",
                default=False,
                help="Defines whether to run the share server multiple "
                     "subnets tests. Enable this option if the used driver "
                     "supports it."),
    cfg.BoolOpt("run_network_allocation_update_tests",
                default=False,
                help="Defines whether to run the network allocation update "
                     "tests. Enable this option if the used driver "
                     "supports it."),

    cfg.StrOpt("image_with_share_tools",
               default="manila-service-image-master",
               help="Image name for vm booting with nfs/smb clients tool."),
    cfg.StrOpt("image_username",
               default="manila",
               help="Image username."),
    cfg.StrOpt("image_password",
               help="Image password. Should be used for "
                    "'image_with_share_tools' without Nova Metadata support."),
    cfg.StrOpt("client_vm_flavor_ref",
               default="100",
               help="Flavor used for client vm in scenario tests."),
    cfg.IntOpt("migration_timeout",
               default=1500,
               help="Time to wait for share migration before "
                    "timing out (seconds)."),
    cfg.IntOpt("share_backup_timeout",
               default=1500,
               help="Time to wait for share backup before "
                    "timing out (seconds)."),
    cfg.IntOpt("share_server_migration_timeout",
               default="1500",
               help="Time to wait for share server migration before "
                    "timing out (seconds)."),
    cfg.StrOpt("default_share_type_name",
               help="Default share type name to use in tempest tests."),
    cfg.StrOpt("backend_replication_type",
               default='none',
               choices=['none', 'writable', 'readable', 'dr'],
               help="Specify the replication type supported by the backend."),
    cfg.IntOpt("share_size",
               default=1,
               help="Default size in GB for shares created by share tests."),
    cfg.IntOpt("additional_overflow_blocks",
               default=0,
               help="Additional blocks to be written "
                    "to share in scenario tests."),
    cfg.IntOpt("share_resize_sync_delay",
               default=0,
               help="Time to wait before the changes to the share size"
                    " are propagated to the storage system."),
    cfg.IntOpt("share_growth_size",
               default=1,
               help="The default increase in size sought by tests"
                    " when validating share resizing within scenario tests."),
    cfg.BoolOpt("run_ipv6_tests",
                default=False,
                help="Enable or disable running IPv6 NFS scenario tests. "
                     "These tests validate that IPv6 export locations work, "
                     "and that access can be provided to IPv6 clients. When "
                     "you do not specify a storage_network, the tests will "
                     "attempt to create an IPv6 subnet on the project network "
                     "they create for ping and SSH to the client test VM "
                     "where data path testing is performed."),
    cfg.StrOpt("dd_input_file",
               default="/dev/zero",
               help="The input file (if) in the dd command specifies the "
                    "source of data that dd will read and process, which can "
                    "be a device, a regular file, or even standard input "
                    "(stdin). dd copies, transforms, or performs actions on "
                    "this data based on provided options and then writes it "
                    "to an output file or device (of). When using /dev/zero "
                    "in storage systems with default compression, although "
                    "it generates highly compressible null bytes (zeros), "
                    "writing data from /dev/zero might not yield significant "
                    "space savings as these systems are already optimized for "
                    "efficient compression."),
    cfg.DictOpt("driver_assisted_backup_test_driver_options",
                default={'dummy': True},
                help="Share backup driver options specified as dict."),
]
