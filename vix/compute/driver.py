# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Cloudbase Solutions Srl
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

"""
A VIX Nova Compute driver.
"""
import os
import platform

from nova.openstack.common.gettextutils import _
from nova.openstack.common import excutils
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.compute import power_state
from nova import exception
from nova.virt import driver
from oslo.config import cfg

from vix.compute import image_cache
from vix.compute import pathutils
from vix import utils
from vix import vixlib
from vix import vixutils

LOG = logging.getLogger(__name__)

vix_opts = [
    cfg.BoolOpt('show_gui',
                default=True,
                help='Shows the instance console in a window when the '
                     'instance is booted'),
    cfg.BoolOpt('default_guestos',
                default="otherLinux64",
                help='The default guest os to be set in the instance vmx '
                     'file if not specified by the image "vix_guestos" '
                     'property'),
]

CONF = cfg.CONF
CONF.register_opts(vix_opts, 'vix')
CONF.import_opt('use_cow_images', 'nova.virt.driver')


class VixDriver(driver.ComputeDriver):
    _power_state_map = {
        vixlib.VIX_POWERSTATE_POWERED_ON: power_state.RUNNING,
        vixlib.VIX_POWERSTATE_PAUSED: power_state.PAUSED,
        vixlib.VIX_POWERSTATE_SUSPENDED: power_state.SUSPENDED,
        vixlib.VIX_POWERSTATE_POWERED_OFF: power_state.SHUTDOWN,
    }

    def __init__(self, virtapi):
        super(VixDriver, self).__init__(virtapi)
        self._conn = vixutils.VixConnection()
        self._conn.connect()
        self._image_cache = image_cache.ImageCache()
        self._pathutils = pathutils.PathUtils()
        self._stats = None

    def init_host(self, host):
        pass

    def list_instances(self):
        return self._conn.list_running_vms()

    def _delete_existing_instance(self, instance_name, destroy_disks=True):
        vmx_path = self._pathutils.get_vmx_path(instance_name)
        if self._conn.vm_exists(vmx_path):
            self._conn.unregister_vm_and_delete_files(vmx_path, destroy_disks)

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):

        instance_name = instance['name']
        self._delete_existing_instance(instance_name)

        try:
            self._pathutils.create_instance_dir(instance_name)

            root_image_id = instance['image_ref']
            user_id = instance['user_id']
            project_id = instance['project_id']

            base_vmdk_path = self._image_cache.get_cached_image(context,
                                                                root_image_id,
                                                                user_id,
                                                                project_id)
            root_vmdk_path = self._pathutils.get_root_vmdk_path(instance_name)

            # TODO: replace with a linked clone in the CoW case
            self._pathutils.copy(base_vmdk_path, root_vmdk_path)

            image_info = self._image_cache.get_image_info(
                context, root_image_id)
            properties = image_info.get("properties", {})

            guest_os = properties.get("vix_guestos", CONF.vix.default_guestos)
            nested_hypervisor = properties.get("vix_nested_hypervisor", False)
            iso_image_ids = properties.get("vix_iso_images", "").split(",")
            floppy_image_id = properties.get("vix_floppy_image")
            tools_iso = properties.get("vix_tools_iso")
            boot_order = properties.get("vix_boot_order", "hdd,cdrom,floppy")

            iso_paths = []
            for image_id in iso_image_ids:
                iso_path = self._image_cache.get_cached_image(context,
                                                              image_id,
                                                              user_id,
                                                              project_id)
                iso_paths.append(iso_path)

            if tools_iso:
                tools_iso_path = os.path.join(self._conn.get_tools_iso_path(),
                                              "%s.iso" % tools_iso)
                iso_paths.append(tools_iso_path)

            # Make sure that the vm will have a disconnected DVD drive
            # just in case the user will want to install the tools
            if not iso_paths:
                iso_paths.append("")

            if floppy_image_id:
                floppy_image_path = self._image_cache.get_cached_image(
                    context, floppy_image_id, user_id, project_id)
                floppy_path = self._pathutils.get_floppy_path(instance_name)
                self._pathutils.copy(floppy_image_path, floppy_path)
            else:
                floppy_path = None

            display_name = instance.get("display_name")

            networks = []
            for vif in network_info:
                LOG.debug(_('Creating nic for instance: %s'), instance_name)
                # TODO: Add network mapping
                networks.append((vixutils.NETWORK_NAT,
                                 vif['address']))

            vmx_path = self._pathutils.get_vmx_path(instance_name)

            self._conn.create_vm(vmx_path=vmx_path,
                                 display_name=display_name,
                                 guest_os=guest_os,
                                 num_vcpus=instance['vcpus'],
                                 mem_size_mb=instance['memory_mb'],
                                 disk_paths=[root_vmdk_path],
                                 iso_paths=iso_paths,
                                 floppy_path=floppy_path,
                                 networks=networks,
                                 boot_order=boot_order,
                                 nested_hypervisor=nested_hypervisor)

            with self._conn.open_vm(vmx_path) as vm:
                vm.power_on(CONF.vix.show_gui)
        except Exception:
            with excutils.save_and_reraise_exception():
                self._delete_existing_instance(instance_name)

    def _exec_vm_action(self, instance, action):
        vmx_path = self._pathutils.get_vmx_path(instance['name'])

        if not self._conn.vm_exists(vmx_path):
            raise exception.InstanceNotFound(instance_id=instance['uuid'])

        with self._conn.open_vm(vmx_path) as vm:
            return action(vm)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        #TODO: pass reboot_type
        self._exec_vm_action(instance, lambda vm: vm.reboot())

    def destroy(self, instance, network_info, block_device_info=None,
                destroy_disks=True, context=None):
        self._delete_existing_instance(instance['name'], destroy_disks)

    def get_info(self, instance):
        vm_state = self._exec_vm_action(instance,
                                        lambda vm: vm.get_power_state())
        for power_state in self._power_state_map:
            if vm_state & power_state:
                return {'state': self._power_state_map[power_state]}

    def attach_volume(self, context, connection_info, instance, mountpoint,
                      encryption=None):
        pass

    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        pass

    def get_volume_connector(self, instance):
        pass

    def _get_host_memory_info(self):
        (total_mem, free_mem) = utils.get_host_memory_info()
        total_mem_mb = total_mem / (1024 * 1024)
        free_mem_mb = free_mem / (1024 * 1024)

        return (total_mem_mb, free_mem_mb, total_mem_mb - free_mem_mb)

    def _get_local_hdd_info_gb(self):
        (total_disk, free_disk) = utils.get_disk_info(
            self._pathutils.get_instances_dir())
        total_dik_gb = total_disk / (1024 * 1024 * 1024)
        free_disk_gb = free_disk / (1024 * 1024 * 1024)

        return (total_dik_gb, free_disk_gb, total_dik_gb - free_disk_gb)

    def _get_hypervisor_version(self):
        return self._conn.get_software_version()

    def get_available_resource(self, nodename):
        (total_mem_mb,
         free_mem_mb,
         used_mem_mb) = self._get_host_memory_info()

        (total_hdd_gb,
         free_hdd_gb,
         used_hdd_gb) = self._get_local_hdd_info_gb()

        # Todo(alexpilotti): add CPU info
        cpu_info = []
        vcpus = utils.get_cpu_count()

        dic = {'vcpus': vcpus,
               'memory_mb': total_mem_mb,
               'memory_mb_used': used_mem_mb,
               'local_gb': total_hdd_gb,
               'local_gb_used': used_hdd_gb,
               'hypervisor_type': "vix",
               'hypervisor_version': self._get_hypervisor_version(),
               'hypervisor_hostname': platform.node(),
               'vcpus_used': 0,
               'cpu_info': jsonutils.dumps(cpu_info),
               'supported_instances': jsonutils.dumps([('i686', 'vix', 'hvm'),
                                                       ('x86_64', 'vix',
                                                        'hvm')])
               }

        return dic

    def _update_stats(self):
        (total_mem_mb,
         free_mem_mb,
         used_mem_mb) = self._get_host_memory_info()

        (total_hdd_gb,
         free_hdd_gb,
         used_hdd_gb) = self._get_local_hdd_info_gb()

        data = {}
        data["disk_total"] = total_hdd_gb
        data["disk_used"] = used_hdd_gb
        data["disk_available"] = free_hdd_gb
        data["host_memory_total"] = total_mem_mb
        data["host_memory_overhead"] = used_mem_mb
        data["host_memory_free"] = free_mem_mb
        data["host_memory_free_computed"] = free_mem_mb
        data["supported_instances"] = [('i686', 'vix', 'hvm'),
                                       ('x86_64', 'vix', 'hvm')]
        data["hypervisor_hostname"] = platform.node()

        self._stats = data

    def get_host_stats(self, refresh=False):
        if refresh or not self._stats:
            self._update_stats()
        return self._stats

    def host_power_action(self, host, action):
        pass

    def snapshot(self, context, instance, name, update_task_state):
        pass

    def pause(self, instance):
        self._exec_vm_action(instance, lambda vm: vm.pause())

    def unpause(self, instance):
        self._exec_vm_action(instance, lambda vm: vm.unpause())

    def suspend(self, instance):
        self._exec_vm_action(instance, lambda vm: vm.suspend())

    def resume(self, instance, network_info, block_device_info=None):
        self._exec_vm_action(instance,
                             lambda vm: vm.power_on(CONF.vix.show_gui))

    def power_off(self, instance):
        self._exec_vm_action(instance, lambda vm: vm.power_off())

    def power_on(self, context, instance, network_info,
                 block_device_info=None):
        self._exec_vm_action(instance,
                             lambda vm: vm.power_on(CONF.vix.show_gui))

    def live_migration(self, context, instance_ref, dest, post_method,
                       recover_method, block_migration=False,
                       migrate_data=None):
        pass

    def pre_live_migration(self, context, instance, block_device_info,
                           network_info, disk, migrate_data=None):
        pass

    def post_live_migration_at_destination(self, ctxt, instance_ref,
                                           network_info,
                                           block_migr=False,
                                           block_device_info=None):
        pass

    def check_can_live_migrate_destination(self, ctxt, instance_ref,
                                           src_compute_info, dst_compute_info,
                                           block_migration=False,
                                           disk_over_commit=False):
        pass

    def check_can_live_migrate_destination_cleanup(self, ctxt,
                                                   dest_check_data):
        pass

    def check_can_live_migrate_source(self, ctxt, instance_ref,
                                      dest_check_data):
        pass

    def plug_vifs(self, instance, network_info):
        LOG.debug(_("plug_vifs called"), instance=instance)

    def unplug_vifs(self, instance, network_info):
        LOG.debug(_("unplug_vifs called"), instance=instance)

    def ensure_filtering_rules_for_instance(self, instance_ref, network_info):
        LOG.debug(_("ensure_filtering_rules_for_instance called"),
                  instance=instance_ref)

    def unfilter_instance(self, instance, network_info):
        LOG.debug(_("unfilter_instance called"), instance=instance)

    def migrate_disk_and_power_off(self, context, instance, dest,
                                   instance_type, network_info,
                                   block_device_info=None):
        pass

    def confirm_migration(self, migration, instance, network_info):
        pass

    def finish_revert_migration(self, instance, network_info,
                                block_device_info=None, power_on=True):
        pass

    def finish_migration(self, context, migration, instance, disk_info,
                         network_info, image_meta, resize_instance=False,
                         block_device_info=None, power_on=True):
        pass

    def get_host_ip_addr(self):
        pass

    def get_console_output(self, instance):
        LOG.debug(_("get_console_output called"), instance=instance)
        return ''
