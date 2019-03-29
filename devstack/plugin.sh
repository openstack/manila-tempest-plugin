# Directory where this plugin.sh file is
MANILA_TEMPEST_PLUGIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# install_manila_tempest_plugin
function install_manila_tempest_plugin {
    setup_dev_lib "manila-tempest-plugin"
}

if [[ "$1" == "stack" ]]; then
    case "$2" in
        install)
            echo_summary "Installing manila-tempest-plugin"
            install_manila_tempest_plugin
            ;;
    esac
fi
