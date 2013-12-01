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
from nova.compute import task_states
from nova import exception
from nova import utils as nova_utils
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
CONF.import_opt('vnc_enabled', 'nova.vnc')


class VixDriver(driver.ComputeDriver):
    _power_state_map = {
        vixlib.VIX_POWERSTATE_POWERED_ON: power_state.RUNNING,
        vixlib.VIX_POWERSTATE_POWERING_ON: power_state.RUNNING,
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

    def _clone_vmdk_vm(self, src_vmdk, root_vmdk_path, dest_vmx_path):
        src_vmdk_base_path = os.path.splitext(src_vmdk)[0]
        src_vmx_path = src_vmdk_base_path + ".vmx"

        @nova_utils.synchronized(src_vmx_path)
        def create_base_vmx():
            if not self._pathutils.exists(src_vmx_path):
                display_name = os.path.basename(src_vmdk_base_path)

                self._conn.create_vm(vmx_path=src_vmx_path,
                                     display_name=display_name,
                                     guest_os="otherLinux64",
                                     disk_paths=[src_vmdk])
        create_base_vmx()

        self._conn.clone_vm(src_vmx_path, dest_vmx_path, True)

        # The cloned VM vmdk name differs from the standard naming
        # (e.g. root.vmdk). Rename the disk and update the
        # configuration files
        vmdk_filename = vixutils.get_vmx_value(dest_vmx_path,
                                               "scsi0:0.fileName")
        vm_dir = os.path.dirname(dest_vmx_path)
        vmdk_path = os.path.join(vm_dir, vmdk_filename)

        self._pathutils.rename(vmdk_path, root_vmdk_path)

        root_vmdk_filename = os.path.basename(root_vmdk_path)
        vixutils.set_vmx_value(dest_vmx_path, "scsi0:0.fileName",
                               root_vmdk_filename)

        dest_vmsd_path = os.path.splitext(dest_vmx_path)[0] + ".vmsd"
        vixutils.set_vmx_value(dest_vmsd_path, "sentinel0",
                               root_vmdk_filename)

    def _check_cow_player(self, cow):
        if (cow and
                vixutils.get_vix_host_type() == vixutils.VIX_VMWARE_PLAYER):
            raise NotImplementedError(_("CoW images are not supported on "
                                        "VMware Player. \"use_cow_images\" "
                                        "must be set to false"))

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):

        instance_name = instance['name']
        root_image_id = instance['image_ref']

        image_info = self._image_cache.get_image_info(
            context, root_image_id)
        properties = image_info.get("properties", {})

        guest_os = properties.get("vix_guestos", CONF.vix.default_guestos)
        nested_hypervisor = properties.get("vix_nested_hypervisor", False)
        iso_image_ids = properties.get("vix_iso_images", "").split(",")
        floppy_image_id = properties.get("vix_floppy_image")
        tools_iso = properties.get("vix_tools_iso")
        boot_order = properties.get("vix_boot_order", "hdd,cdrom,floppy")

        cow_str = properties.get("cow", str(CONF.use_cow_images))
        cow = cow_str.lower() in ["true", "1", "yes"]

        LOG.info(_("CoW image: %s" % cow))

        self._check_cow_player(cow)

        self._delete_existing_instance(instance_name)

        try:
            self._pathutils.create_instance_dir(instance_name)

            user_id = instance['user_id']
            project_id = instance['project_id']

            base_vmdk_path = self._image_cache.get_cached_image(context,
                                                                root_image_id,
                                                                user_id,
                                                                project_id)
            root_vmdk_path = self._pathutils.get_root_vmdk_path(instance_name)

            vmx_path = self._pathutils.get_vmx_path(instance_name)

            if cow:
                self._clone_vmdk_vm(base_vmdk_path, root_vmdk_path, vmx_path)
            else:
                self._pathutils.copy(base_vmdk_path, root_vmdk_path)

            iso_paths = []
            for image_id in iso_image_ids:
                if image_id:
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

            if CONF.vnc_enabled:
                vnc_port = utils.get_free_port()
            else:
                vnc_port = None

            display_name = instance.get("display_name")

            networks = []
            for vif in network_info:
                LOG.debug(_('Creating nic for instance: %s'), instance_name)
                # TODO: Add network mapping
                networks.append((vixutils.NETWORK_NAT,
                                 vif['address']))

            if cow:
                self._conn.update_vm(vmx_path=vmx_path,
                                     display_name=display_name,
                                     guest_os=guest_os,
                                     num_vcpus=instance['vcpus'],
                                     mem_size_mb=instance['memory_mb'],
                                     #disk_paths=[root_vmdk_path],
                                     iso_paths=iso_paths,
                                     floppy_path=floppy_path,
                                     networks=networks,
                                     boot_order=boot_order,
                                     vnc_enabled=CONF.vnc_enabled,
                                     vnc_port=vnc_port,
                                     nested_hypervisor=nested_hypervisor)
            else:
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
                                     vnc_enabled=CONF.vnc_enabled,
                                     vnc_port=vnc_port,
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
        for state in self._power_state_map:
            if vm_state & state:
                return {'state': self._power_state_map[state]}

    def attach_volume(self, context, connection_info, instance, mountpoint,
                      encryption=None):
        raise NotImplementedError(_("Unsupported feature"))

    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        raise NotImplementedError(_("Unsupported feature"))

    def get_volume_connector(self, instance):
        raise NotImplementedError(_("Unsupported feature"))

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
        if (vixutils.get_vix_host_type() == vixutils.VIX_VMWARE_PLAYER):
            raise NotImplementedError(_("VMware Player does not support "
                                        "snapshots"))

        # TODO(alexpilotti): Consider raising an exception when a snapshot
        # of a CoW instance is attemped

        instance_name = instance['name']
        vmx_path = self._pathutils.get_vmx_path(instance_name)

        update_task_state(task_state=task_states.IMAGE_PENDING_UPLOAD)

        with self._conn.open_vm(vmx_path) as vm:
            with vm.create_snapshot(name="Nova snapshot") as snapshot:
                try:
                    root_vmdk_path = self._pathutils.get_root_vmdk_path(
                        instance_name)

                    update_task_state(
                        task_state=task_states.IMAGE_UPLOADING,
                        expected_state=task_states.IMAGE_PENDING_UPLOAD)

                    self._image_cache.save_glance_image(context, name,
                                                        root_vmdk_path)
                finally:
                    vm.remove_snapshot(snapshot)

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
        raise NotImplementedError(_("Unsupported feature"))

    def pre_live_migration(self, context, instance, block_device_info,
                           network_info, disk, migrate_data=None):
        raise NotImplementedError(_("Unsupported feature"))

    def post_live_migration_at_destination(self, ctxt, instance_ref,
                                           network_info,
                                           block_migr=False,
                                           block_device_info=None):
        raise NotImplementedError(_("Unsupported feature"))

    def check_can_live_migrate_destination(self, ctxt, instance_ref,
                                           src_compute_info, dst_compute_info,
                                           block_migration=False,
                                           disk_over_commit=False):
        raise NotImplementedError(_("Unsupported feature"))

    def check_can_live_migrate_destination_cleanup(self, ctxt,
                                                   dest_check_data):
        raise NotImplementedError(_("Unsupported feature"))

    def check_can_live_migrate_source(self, ctxt, instance_ref,
                                      dest_check_data):
        raise NotImplementedError(_("Unsupported feature"))

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
        return CONF.my_ip

    def get_vnc_console(self, instance):
        vmx_path = self._pathutils.get_vmx_path(instance['name'])
        with self._conn.open_vm(vmx_path) as vm:
            vnc_enabled, vnc_port = vm.get_vnc_settings()

        if not vnc_enabled:
            raise utils.VixException(_("VNC is not enabled for this instance"))

        host = self.get_host_ip_addr()

        return {'host': host, 'port': vnc_port, 'internal_access_path': None}

    def get_console_output(self, instance):
        LOG.debug(_("get_console_output called"), instance=instance)
        return ''
