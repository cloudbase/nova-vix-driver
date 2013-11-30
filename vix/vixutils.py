# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import ctypes
import os
import re
import shutil
import sys
import time

if sys.platform == 'win32':
    import _winreg
    import win32api

from nova.openstack.common.gettextutils import _
from vix import vixlib
from vix import utils

VIX_VMWARE_WORKSTATION = vixlib.VIX_SERVICEPROVIDER_VMWARE_WORKSTATION
VIX_VMWARE_PLAYER = vixlib.VIX_SERVICEPROVIDER_VMWARE_PLAYER

SUPPORTS_NESTED_VIRT_VMX = 1
SUPPORTS_NESTED_VIRT_EPT = 2

NETWORK_NAT = "__nat__"
NETWORK_HOST_ONLY = "__host_only__"


def _check_job_err_code(err):
    if err:
        msg = vixlib.Vix_GetErrorText(err, None)
        raise utils.VixException(msg)


def load_config_file_values(path):
    config = {}
    with open(path, 'rb') as f:
        for s in f.readlines():
            m = re.match(r'^([^\s=]+)\s*=\s*"(.*)"(\r)?$', s)
            if m:
                config[m.group(1)] = m.group(2)
    return config


def _get_player_preferences_file_path():
    # TODO: handle Linux case
    if sys.platform == "win32":
        app_data_dir = os.getenv('APPDATA')
        return os.path.join(app_data_dir, "VMWare", "preferences.ini")
    else:
        raise NotImplementedError()


def _get_install_dir():
    if sys.platform == "darwin":
        return "/Applications/VMware Fusion.app"
    elif sys.platform == "win32":
        with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                             "SOFTWARE\VMware, Inc.\VMware"
                             " Workstation") as key:
            return _winreg.QueryValueEx(key, "InstallPath")[0]
    else:
        #TODO: Add Linux support
        raise NotImplementedError()


def get_vix_bin_path():
    install_dir = _get_install_dir()

    if sys.platform == "darwin":
        return os.path.join(install_dir, "Contents/Library")
    elif sys.platform == "win32":
        return install_dir
    else:
        #TODO: Add Linux support
        raise NotImplementedError()


_host_type = None


def get_vix_host_type():
    global _host_type

    if not _host_type:
        if sys.platform == "darwin":
            if os.path.exists("/Applications/VMware Fusion.app"):
                _host_type = vixlib.VIX_SERVICEPROVIDER_VMWARE_WORKSTATION
            else:
                raise utils.VixException(_("VMWare Fusion not installed"))
        elif sys.platform == "win32":
            # Ref: http://kb.vmware.com/selfservice/microsites/search.do?
            #      language=en_US&cmd=displayKC&externalId=1308
            try:
                with _winreg.OpenKey(
                        _winreg.HKEY_CLASSES_ROOT,
                        "Installer\\UpgradeCodes\\"
                        "3F935F414A4C79542AD9C8D157A3CC39") as key:
                    product_code = _winreg.EnumValue(key, 0)[0]
                with _winreg.OpenKey(
                        _winreg.HKEY_CLASSES_ROOT,
                        "Installer\\products\\%s" % product_code) as key:
                    product_name = _winreg.QueryValueEx(key, "ProductName")[0]

                if product_name == "VMware Player":
                    _host_type = vixlib.VIX_SERVICEPROVIDER_VMWARE_PLAYER
                elif product_name == "VMware Workstation":
                    _host_type = vixlib.VIX_SERVICEPROVIDER_VMWARE_WORKSTATION
                else:
                    raise utils.VixException(_("Unsupported Vix product: %s") %
                                             product_name)
            except WindowsError:
                raise utils.VixException(_("Workstation or Player not "
                                           "installed"))
        else:
            #TODO: Add Linux support
            raise NotImplementedError()

    return _host_type


class VixVM(object):
    def __init__(self, vm_handle):
        self._vm_handle = vm_handle

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self._vm_handle:
            vixlib.Vix_ReleaseHandle(self._vm_handle)
            self._vm_handle = None

    def get_power_state(self):
        power_state = ctypes.c_int()
        err = vixlib.Vix_GetProperties(self._vm_handle,
                                       vixlib.VIX_PROPERTY_VM_POWER_STATE,
                                       ctypes.byref(power_state),
                                       vixlib.VIX_PROPERTY_NONE)
        _check_job_err_code(err)
        return power_state.value

    def power_on(self, show_gui=True):
        if show_gui:
            options = vixlib.VIX_VMPOWEROP_LAUNCH_GUI
        else:
            options = vixlib.VIX_VMPOWEROP_NORMAL

        job_handle = vixlib.VixVM_PowerOn(self._vm_handle,
                                          options,
                                          vixlib.VIX_INVALID_HANDLE,
                                          None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def pause(self):
        job_handle = vixlib.VixVM_Pause(self._vm_handle,
                                        0, vixlib.VIX_INVALID_HANDLE,
                                        None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def unpause(self):
        job_handle = vixlib.VixVM_Unpause(self._vm_handle,
                                          0, vixlib.VIX_INVALID_HANDLE,
                                          None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def suspend(self):
        job_handle = vixlib.VixVM_Suspend(self._vm_handle,
                                          0, None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def reboot(self, soft=False):
        if soft:
            power_op = vixlib.VIX_VMPOWEROP_FROM_GUEST
        else:
            power_op = vixlib.VIX_VMPOWEROP_NORMAL

        job_handle = vixlib.VixVM_Reset(self._vm_handle, power_op,
                                        None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def power_off(self, soft=False):
        if soft:
            power_op = vixlib.VIX_VMPOWEROP_FROM_GUEST
        else:
            power_op = vixlib.VIX_VMPOWEROP_NORMAL

        job_handle = vixlib.VixVM_PowerOff(self._vm_handle, power_op,
                                           None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def wait_for_tools_in_guest(self, timeout_seconds=600):
        job_handle = vixlib.VixVM_WaitForToolsInGuest(self._vm_handle,
                                                      timeout_seconds,
                                                      None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def get_guest_ip_address(self, timeout_seconds=600):
        start = time.time()

        self.wait_for_tools_in_guest(timeout_seconds)

        ip_address = None
        while not ip_address:
            job_handle = vixlib.VixVM_ReadVariable(
                self._vm_handle, vixlib.VIX_VM_GUEST_VARIABLE,
                "ip", 0, None, None)
            read_value = ctypes.c_char_p()
            err = vixlib.VixJob_Wait(
                job_handle,
                vixlib.VIX_PROPERTY_JOB_RESULT_VM_VARIABLE_STRING,
                ctypes.byref(read_value),
                vixlib.VIX_PROPERTY_NONE)
            vixlib.Vix_ReleaseHandle(job_handle)
            _check_job_err_code(err)

            ip_address = read_value.value
            vixlib.Vix_FreeBuffer(read_value)

            if not ip_address or ip_address.startswith('169.254.'):
                if (timeout_seconds >= 0 and time.time() -
                        start > timeout_seconds):
                    raise utils.VixException(_("Timeout exceeded: %d" %
                                             timeout_seconds))
                time.sleep(3)
                ip_address = None

        return ip_address

    def delete(self, delete_disk_files=True):
        if delete_disk_files:
            delete_options = vixlib.VIX_VMDELETE_DISK_FILES
        else:
            delete_options = 0

        job_handle = vixlib.VixVM_Delete(self._vm_handle, delete_options,
                                         None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

        self.close()

    def create_snapshot(self, include_memory=False, name=None,
                        description=None):
        if include_memory:
            options = vixlib.VIX_SNAPSHOT_INCLUDE_MEMORY
        else:
            options = 0

        job_handle = vixlib.VixVM_CreateSnapshot(self._vm_handle,
                                                 name, description, options,
                                                 vixlib.VIX_INVALID_HANDLE,
                                                 None, None)
        snapshot_handle = vixlib.VixHandle()
        err = vixlib.VixJob_Wait(job_handle,
                                 vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
                                 ctypes.byref(snapshot_handle),
                                 vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)
        vixlib.Vix_ReleaseHandle(snapshot_handle)


class VixConnection(object):
    def __init__(self):
        self._host_type = None
        self._host_handle = None
        self._software_version = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def unregister_vm_and_delete_files(self, vmx_path, destroy_disks=True):
        with self.open_vm(vmx_path) as vm:
            if vm.get_power_state() != vixlib.VIX_POWERSTATE_POWERED_OFF:
                vm.power_off()
        self.unregister_vm(vmx_path)
        if destroy_disks:
            self.delete_vm_files(vmx_path)

    def connect(self):
        job_handle = vixlib.VixHost_Connect(vixlib.VIX_API_VERSION,
                                            get_vix_host_type(),
                                            None, 0, None, None, 0,
                                            vixlib.VIX_INVALID_HANDLE,
                                            None, None)

        host_handle = vixlib.VixHandle()
        err = vixlib.VixJob_Wait(job_handle,
                                 vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
                                 ctypes.byref(host_handle),
                                 vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

        self._host_handle = host_handle

    def open_vm(self, vmx_path):
        job_handle = vixlib.VixVM_Open(self._host_handle, vmx_path, None, None)
        vm_handle = vixlib.VixHandle()
        err = vixlib.VixJob_Wait(job_handle,
                                 vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
                                 ctypes.byref(vm_handle),
                                 vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

        return VixVM(vm_handle)

    def create_vm(self, vmx_path,
                  display_name,
                  guest_os,
                  virtual_hw_version=10,
                  num_vcpus=1,
                  cores_per_socket=1,
                  mem_size_mb=1024,
                  disk_paths=None,
                  iso_paths=None,
                  floppy_path=None,
                  networks=None,
                  boot_order="hdd,cdrom,floppy",
                  nested_hypervisor=False,
                  additional_config=None):

        config = {
            "config.version": "8",
            "pciBridge0.present": "TRUE",
            "pciBridge4.present": "TRUE",
            "pciBridge4.virtualDev": "pcieRootPort",
            "pciBridge4.functions": "8",
            "pciBridge5.present": "TRUE",
            "pciBridge5.virtualDev": "pcieRootPort",
            "pciBridge5.functions": "8",
            "pciBridge6.present": "TRUE",
            "pciBridge6.virtualDev": "pcieRootPort",
            "pciBridge6.functions": "8",
            "pciBridge7.present": "TRUE",
            "pciBridge7.virtualDev": "pcieRootPort",
            "pciBridge7.functions": "8",
            "vmci0.present": "TRUE",
            "hpet0.present": "TRUE",
            "virtualHW.productCompatibility": "hosted",
            "powerType.powerOff": "soft",
            "powerType.powerOn": "hard",
            "powerType.suspend": "hard",
            "powerType.reset": "soft",
            "disk.EnableUUID": "TRUE",
            "cleanShutdown": "FALSE",
            "replay.supported": "FALSE",
            "softPowerOff": "FALSE",
            "tools.syncTime": "FALSE",
            "hard-disk.hostBuffer": "disabled",
        }

        config["virtualHW.version"] = str(virtual_hw_version)
        config["displayName"] = display_name
        config["numvcpus"] = str(num_vcpus)
        config["cpuid.coresPerSocket"] = str(cores_per_socket)
        config["memsize"] = str(mem_size_mb)
        config["guestOS"] = guest_os
        config["bios.bootOrder"] = boot_order

        if disk_paths:
            config.update(self._get_scsi_config(disk_paths))

        if iso_paths:
            config.update(self._get_ide_config(iso_paths))

        if floppy_path:
            config.update(self._get_floppy_config(floppy_path))

        if networks:
            config.update(self._get_networs_config(networks))

        if nested_hypervisor:
            config.update(self._get_nested_hypervisor_config())

        if additional_config:
            config.update(additional_config)

        vmx_dir = os.path.dirname(vmx_path)
        if not os.path.exists(vmx_dir):
            os.makedirs(vmx_dir)

        with open(vmx_path, 'wb') as f:
            for k, v in config.items():
                f.write('.encoding = "UTF-8"' + os.linesep)
                f.write('%(k)s = "%(v)s"' % {'k': k, 'v': v} + os.linesep)

    def update_vm(self, vmx_path,
                  display_name=None,
                  guest_os=None,
                  virtual_hw_version=None,
                  num_vcpus=None,
                  cores_per_socket=None,
                  mem_size_mb=None,
                  disk_paths=None,
                  iso_paths=None,
                  floppy_path=None,
                  networks=None,
                  boot_order=None,
                  nested_hypervisor=None,
                  additional_config=None):
        config = {}

        if display_name:
            config["displayName"] = display_name

        if guest_os:
            config["guestOS"] = guest_os

        if virtual_hw_version:
            config["virtualHW.version"] = str(virtual_hw_version)

        if num_vcpus:
            config["numvcpus"] = num_vcpus

        if cores_per_socket:
            config["cpuid.coresPerSocket"] = cores_per_socket

        if mem_size_mb:
            config["memsize"] = mem_size_mb

        if boot_order:
            config["bios.bootOrder"] = boot_order

        if disk_paths:
            config.update(self._get_scsi_config(disk_paths))

        if iso_paths:
            config.update(self._get_ide_config(iso_paths))

        if floppy_path:
            config.update(self._get_floppy_config(floppy_path))

        if nested_hypervisor:
            config.update(self._get_nested_hypervisor_config())

        if networks is not None:
            config.update(self._get_networs_config(networks))

        if additional_config:
            config.update(additional_config)

        if networks is not None:
            self.remove_vmx_value(vmx_path, r"ethernet[\d]+\.[a-zA-Z]+")

        for (k, v) in config.items():
            self.set_vmx_value(vmx_path, k, v)

    def _get_scsi_config(self, disk_paths):
        config = {}
        config["scsi0.present"] = "TRUE"
        config["scsi0.sharedBus"] = "none"
        config["scsi0.virtualDev"] = "lsisas1068"

        i = 0
        for disk_path in disk_paths:
            config.update(self._get_scsi_disk_config(0, i, disk_path))
            i += 1
        return config

    def _get_scsi_disk_config(self, ctrl_idx, disk_idx, path):
        config = {}
        prefix = "scsi%(ctrl_idx)d:%(disk_idx)d" % {"ctrl_idx": ctrl_idx,
                                                    "disk_idx": disk_idx}
        config["%s.present" % prefix] = "TRUE"
        config["%s.deviceType" % prefix] = "scsi-hardDisk"
        config["%s.fileName" % prefix] = path
        return config

    def _get_ide_config(self, iso_paths):
        config = {}
        i = 0
        for iso_path in iso_paths:
            config.update(self._get_ide_iso_config(1, i, iso_path))
            i += 1
        return config

    def _get_ide_iso_config(self, ctrl_idx, disk_idx, path):
        config = {}
        prefix = "ide%(ctrl_idx)d:%(disk_idx)d" % {"ctrl_idx": ctrl_idx,
                                                   "disk_idx": disk_idx}
        config["%s.present" % prefix] = "TRUE"
        config["%s.clientDevice" % prefix] = "FALSE"
        config["%s.deviceType" % prefix] = "cdrom-image"
        config["%s.startConnected" % prefix] = (path is not None and
                                                len(path) > 0)
        if path:
            config["%s.fileName" % prefix] = path

        return config

    def _get_floppy_config(self, floppy_path):
        config = {}
        config["floppy0.present"] = "TRUE"
        config["floppy0.fileType"] = "file"
        config["floppy0.clientDevice"] = "FALSE"
        config["floppy0.fileName"] = floppy_path
        return config

    def _get_nested_hypervisor_config(self):
        config = {}
        config["vcpu.hotadd"] = "FALSE"
        config["featMask.vm.hv.capable"] = "Min:1"
        config["vhv.enable"] = "TRUE"
        return config

    def _get_networs_config(self, networks):
        config = {}
        i = 0
        for network, mac_address in networks:
            config["ethernet%d.present" % i] = "TRUE"
            config["ethernet%d.virtualDev" % i] = "e1000e"
            if not mac_address:
                config["ethernet%d.addressType" % i] = "generated"
            else:
                config["ethernet%d.addressType" % i] = "static"
                config["ethernet%d.address" % i] = mac_address

            if network == NETWORK_NAT:
                config["ethernet%d.connectionType" % i] = "nat"
            elif network == NETWORK_HOST_ONLY:
                config["ethernet%d.connectionType" % i] = "hostonly"
            else:
                config["ethernet%d.networkName" % i] = network
            i += 1
        return config

    def register_vm(self, vmx_path):
        job_handle = vixlib.VixHost_RegisterVM(self._host_handle, vmx_path,
                                               None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def _unregister_vm_local(self, vmx_path):
        #TODO: VMs are not stored in
        # ~/Library/Preferences/VMware Fusion/preferences
        # Look for possible alternatives
        if sys.platform == "darwin":
            return

        pref_file_path = _get_player_preferences_file_path()
        with open(pref_file_path, 'rb') as f:
            lines = f.readlines()

        if sys.platform == 'win32' and os.path.exists(vmx_path):
            vmx_path_norm = win32api.GetLongPathName(vmx_path)
        else:
            vmx_path_norm = vmx_path
        vmx_path_norm = os.path.normcase(os.path.abspath(vmx_path_norm))

        index = -1
        for s in lines:
            m = re.match(r'^pref.mruVM(\d+)\.filename\s*=\s*"(.*)"(\r)?$', s)
            if m:
                path = os.path.normcase(os.path.abspath(m.group(2)))
                if vmx_path_norm == path:
                    index = int(m.group(1))
                    break

        if index >= 0:
            new_lines = []
            for s in lines:
                m = re.match(r'^pref.mruVM(\d+)\.([a-zA-Z]+)\s*=' +
                             r'\s*"(.+)"(\r)?$', s)
                if not m:
                    new_lines.append(s)
                else:
                    i = int(m.group(1))
                    if i < index:
                        new_lines.append(s)
                    elif i > index:
                        new_lines.append('pref.mruVM%(i)s.%(k)s = "%(v)s"' %
                                         {"i": i - 1,
                                          "k": m.group(2),
                                          'v': m.group(3)} + os.linesep)

            with open(pref_file_path, 'wb') as f:
                for s in new_lines:
                    f.write(s)

    def _unregister_vm_server(self, vmx_path):
        job_handle = vixlib.VixHost_UnregisterVM(self._host_handle, vmx_path,
                                                 None, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

    def unregister_vm(self, vmx_path):
        if get_vix_host_type() in [VIX_VMWARE_PLAYER, VIX_VMWARE_WORKSTATION]:
            self._unregister_vm_local(vmx_path)
        else:
            self._unregister_vm_server(vmx_path)

    def disconnect(self):
        if self._host_handle:
            vixlib.VixHost_Disconnect(self._host_handle)
            self._host_handle = None

    def vm_exists(self, vmx_path):
        return os.path.exists(vmx_path)

    def delete_vm_files(self, vmx_path):
        vmx_dir = os.path.dirname(vmx_path)
        if os.path.exists(vmx_dir):
            shutil.rmtree(vmx_dir)

    def list_running_vms(self):
        vmx_paths = []

        def callback(jobHandle, eventType, moreEventInfo, clientData):
            if vixlib.VIX_EVENTTYPE_FIND_ITEM != eventType:
                return

            url = ctypes.c_char_p()
            err = vixlib.Vix_GetProperties(
                moreEventInfo,
                vixlib.VIX_PROPERTY_FOUND_ITEM_LOCATION,
                ctypes.byref(url),
                vixlib.VIX_PROPERTY_NONE)

            vmx_paths.append(url.value)

            vixlib.Vix_FreeBuffer(url)
            _check_job_err_code(err)

        cb = vixlib.VixEventProc(callback)
        job_handle = vixlib.VixHost_FindItems(self._host_handle,
                                              vixlib.VIX_FIND_RUNNING_VMS,
                                              vixlib.VIX_INVALID_HANDLE,
                                              -1, cb, None)
        err = vixlib.VixJob_Wait(job_handle, vixlib.VIX_PROPERTY_NONE)
        vixlib.Vix_ReleaseHandle(job_handle)
        _check_job_err_code(err)

        return vmx_paths

    def get_tools_iso_path(self):
        install_dir = _get_install_dir()

        if sys.platform == "darwin":
            return os.path.join(install_dir, "Contents/Library/isoimages")
        elif sys.platform == "win32":
            return install_dir
        else:
            #TODO: Add Linux support
            raise NotImplementedError()

    def nested_virt_support(self):
        # TODO: match with HW capabilities as well
        return SUPPORTS_NESTED_VIRT_VMX | SUPPORTS_NESTED_VIRT_EPT

    def clone_vm(self, src_vmx_path, dest_vmx_path, linked_clone=False):
        if linked_clone:
            clone_type = vixlib.VIX_CLONETYPE_LINKED
        else:
            clone_type = vixlib.VIX_CLONETYPE_FULL

        with self.open_vm(src_vmx_path) as vm:
            job_handle = vixlib.VixVM_Clone(vm._vm_handle,
                                            vixlib.VIX_INVALID_HANDLE,
                                            clone_type,
                                            dest_vmx_path,
                                            0, vixlib.VIX_INVALID_HANDLE,
                                            None, None)

            cloned_vm_handle = vixlib.VixHandle()
            err = vixlib.VixJob_Wait(job_handle,
                                     vixlib.VIX_PROPERTY_JOB_RESULT_HANDLE,
                                     ctypes.byref(cloned_vm_handle),
                                     vixlib.VIX_PROPERTY_NONE)
            vixlib.Vix_ReleaseHandle(job_handle)
            _check_job_err_code(err)

            return VixVM(cloned_vm_handle)

    def remove_vmx_value(self, vmx_path, name):
        utils.remove_lines(vmx_path, r"^%s\s*=\s*.*$" % name)

    def set_vmx_value(self, vmx_path, name, value):
        found = utils.replace_text(vmx_path, r"^(%s\s*=\s*)(.*)$" % name,
                                   "\\1\"%s\"" % value)
        if not found:
            with open(vmx_path, "ab") as f:
                f.write("%(name)s = \"%(value)s\"" %
                        {'name': name, 'value': value} + os.linesep)

    def get_vmx_value(self, vmx_path, name):
        value = utils.get_text(vmx_path, r"^%s\s*=\s*\"(.*)\"$" % name)
        if value:
            return value[0]

    def get_software_version(self):
        if not self._software_version:
            version = ctypes.c_char_p()
            err = vixlib.Vix_GetProperties(
                self._host_handle,
                vixlib.VIX_PROPERTY_HOST_SOFTWARE_VERSION,
                ctypes.byref(version),
                vixlib.VIX_PROPERTY_NONE)
            _check_job_err_code(err)
            vixlib.Vix_FreeBuffer(version)

            self._software_version = version.value

        return self._software_version
