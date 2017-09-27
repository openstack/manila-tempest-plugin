Prerequisites
-------------

Before you install and configure the openstack service,
you must create a database, service credentials, and API endpoints.

#. To create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        $ mysql -u root -p

   * Create the ``manila-tempest-plugin`` database:

     .. code-block:: none

        CREATE DATABASE manila-tempest-plugin;

   * Grant proper access to the ``manila-tempest-plugin`` database:

     .. code-block:: none

        GRANT ALL PRIVILEGES ON manila-tempest-plugin.* TO 'manila-tempest-plugin'@'localhost' \
          IDENTIFIED BY 'MANILA-TEMPEST-PLUGIN_DBPASS';
        GRANT ALL PRIVILEGES ON manila-tempest-plugin.* TO 'manila-tempest-plugin'@'%' \
          IDENTIFIED BY 'MANILA-TEMPEST-PLUGIN_DBPASS';

     Replace ``MANILA-TEMPEST-PLUGIN_DBPASS`` with a suitable password.

   * Exit the database access client.

     .. code-block:: none

        exit;

#. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. To create the service credentials, complete these steps:

   * Create the ``manila-tempest-plugin`` user:

     .. code-block:: console

        $ openstack user create --domain default --password-prompt manila-tempest-plugin

   * Add the ``admin`` role to the ``manila-tempest-plugin`` user:

     .. code-block:: console

        $ openstack role add --project service --user manila-tempest-plugin admin

   * Create the manila-tempest-plugin service entities:

     .. code-block:: console

        $ openstack service create --name manila-tempest-plugin --description "openstack" openstack

#. Create the openstack service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
        openstack public http://controller:XXXX/vY/%\(tenant_id\)s
      $ openstack endpoint create --region RegionOne \
        openstack internal http://controller:XXXX/vY/%\(tenant_id\)s
      $ openstack endpoint create --region RegionOne \
        openstack admin http://controller:XXXX/vY/%\(tenant_id\)s
