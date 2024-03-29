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

from tempest.lib import exceptions


class ShareBuildErrorException(exceptions.TempestException):
    message = "Share %(resource_id)s failed to build and is in ERROR status"


class ShareInstanceBuildErrorException(exceptions.TempestException):
    message = ("Share instance %(resource_id)s failed to build and is in "
               "ERROR status")


class ShareGroupBuildErrorException(exceptions.TempestException):
    message = ("Share group %(resource_id)s failed to build and "
               "is in ERROR status")


class AccessRuleBuildErrorException(exceptions.TempestException):
    message = "Share's rule with id %(resource_id)s is in ERROR status"


class SnapshotBuildErrorException(exceptions.TempestException):
    message = "Snapshot %(resource_id)s failed to build and is in ERROR status"


class SnapshotInstanceBuildErrorException(exceptions.TempestException):
    message = ("Snapshot instance %(resource_id)s failed to build and is in "
               "ERROR status.")


class ShareGroupSnapshotBuildErrorException(exceptions.TempestException):
    message = ("Share Group Snapshot %(resource_id)s failed "
               "to build and is in ERROR status")


class ShareProtocolNotSpecified(exceptions.TempestException):
    message = "Share can not be created, share protocol is not specified"


class ShareNetworkNotSpecified(exceptions.TempestException):
    message = "Share can not be created, share network not specified"


class NoAvailableNetwork(exceptions.TempestException):
    message = "No available network for service VM"


class InvalidResource(exceptions.TempestException):
    message = "Provided invalid resource: %(message)s"


class ShareMigrationException(exceptions.TempestException):
    message = ("Share %(share_id)s failed to migrate from "
               "host %(src)s to host %(dest)s.")


class ResourceReleaseFailed(exceptions.TempestException):
    message = "Failed to release resource '%(res_type)s' with id '%(res_id)s'."


class ShareReplicationTypeException(exceptions.TempestException):
    message = ("Option backend_replication_type is set to incorrect value: "
               "%(replication_type)s")


class ShareServerBuildErrorException(exceptions.TempestException):
    message = ("Share server %(server_id)s failed to build and is in ERROR "
               "status")


class ShareServerMigrationException(exceptions.TempestException):
    message = ("Share server %(server_id)s failed to migrate and is in ERROR "
               "status")


class ShareBackupBuildErrorException(exceptions.TempestException):
    message = ("Share backup %(backup_id)s failed and is in ERROR status")
