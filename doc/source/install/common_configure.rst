2. Edit the ``/etc/manila-tempest-plugin/manila-tempest-plugin.conf`` file and complete the following
   actions:

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://manila-tempest-plugin:MANILA-TEMPEST-PLUGIN_DBPASS@controller/manila-tempest-plugin
