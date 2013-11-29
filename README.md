nova-vix-driver
===============

OpenStack Nova compute driver for VMware Workstation or Player and Fusion. 

The main goal of this project is to enable developers, testers and sysadmins to be able to easily deploy
virtual workloads on their workstation and laptops using familiar OpenStack tools.

Reasons for choosing VMware Workstation / Player / Fusion over other solutions 
(e.g. VirtualBox):


1) Support for nested virtualization (VMX, EPT).

This is a mandatory feature for running KVM, Hyper-V or other hypervisors in a virtual machine. 

2) Multiplatform

Workstation and Player are supported on Windows and Linux, while Fusion works on Mac OS X.

3) Free option

VMware player is free for non commercial use. Refer to the related license for details.


Setup
=====

Deploy OpenStack Havana on your physical laptop / workstation / server or in 
a virtual machine (e.g. using RDO or DevStack).

Install nova-vix-driver on the machine running VMware Workstation, Player or Fusion:

    python setup.py install

Create a Nova configuration file (e.g. by copying nova.conf from another compute node) and set 
the proper compute driver class:

    [DEFAULT]
    compute_driver=vix.compute.driver.VixDriver
    
Start nova-compute, making sure to have the Vix dll or shared module in the path.

    nova-compute --config-file /path/to/your/nova.conf
    
Note: Since VMware Player does not come with the Vix components, they can be downloaded as part of the
Vix SDK: 

https://my.vmware.com/web/vmware/free#desktop_end_user_computing/vmware_player/6_0|PLAYER-600-A|drivers_tools

    
Usage
=====

Beside the feature that you'd expect from other Nova drivers, there are a few options specific to this project

Glance image options
--------------------

The following Glance image properties are recognized by the Vix Nova compute driver.

    vix_guestos
    
The virtual machine OS as specified in the VMware VIX configuration file (.e.g.: "rhel6-64" or "winhyperv").

    vix_nested_hypervisor
    
Wether the instances should support nested virtualization. Note: this is implicit if the guest OS is "winhyperv"

    vix_iso_images
    
Comma separated list of Glance images ids to be attached as virtual DVDRom drives to instances.

    vix_floppy_image
    
Glance image id, to be attached as virtual floppy drive.

    vix_tools_iso
    
VMware tools ISO image to be attached as a virtual DVDRom drive (e.g. "linux", "windows", etc).

    vix_boot_order
    
Device boot order. Default: "hdd,cdrom,floppy"


Nova compute options
--------------------

Options that can be specified in the Nova configuration file in the [vix] section:
    show_gui=True
    
If true, instance consoles windows will be displayed in WMware Workstation, Player or Fusion.

    default_guestos=otherLinux64
    
The guest OS to be used in case a value is not provided by the Glance image.


Example
=======

Here's an example about how to create a CentOS template image by providing a CentOS DVD and a 
kickstart file in a floppy image:

    glance image-create --property hypervisor_type=vix --name CentOS-64-ks --container-format bare \
    --disk-format iso < CentOS-6.4-x86_64-bin-DVD1-ks.iso
    
    image-create --name Kickstart --container-format bare --disk-format raw < ks.flp

    ISO_IMG_ID=`glance image-show CentOS-64-ks | awk '{if (NR == 9) {print $4}}'`
    FLOPPY_IMG_ID=`glance image-show Kickstart | awk '{if (NR == 9) {print $4}}'`
    
    qemu-img create -f vmdk empty.vmdk 2G
    glance image-create --name CentOS-64-template --container-format bare --disk-format vmdk \
    --property hypervisor_type=vix \
    --property vix_tools=linux \
    --property vix_iso_images=$ISO_IMG_ID \
    --property vix_floppy_image=$FLOPPY_IMG_ID < empty.vmdk
    rm empty.vmdk

Now simply boot the image, the "hypervisor_type" property in the image makes sure that it won't be
spawned on other hypervisors.

    nova boot  --flavor 1 --image CentOS-64-template --key-name key1 centos-64-template1


Limitations
===========

Due to the nature of this project, live-migration is not supported as it wouldn't make particularly sense.



