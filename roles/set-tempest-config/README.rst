set-tempest-config
==================

This is a workaround for the `merge_config_file <https://opendev
.org/openstack/devstack/src/commit/76d7d7c90c3979c72404fddd31ee884c8bfdb1ec
/inc/meta-config#L82>`_ routine that doesn't working correctly on jobs based on
the "devstack-minimal" profile.

**Role Variables**

.. zuul:rolevar:: devstack_base_dir
   :default: /opt/stack

   The devstack base directory.

.. zuul:rolevar:: devstack_local_conf_path
   :default: "{{ devstack_base_dir }}/devstack/local.conf"

   Where to find the local.conf file
