# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cloudbase Solutions Srl
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

import setuptools

setuptools.setup(name='nova-vix-driver',
                 version='0.1',
                 description='OpenStack Vix Nova driver',
                 author='Cloudbase Solutions Srl',
                 author_email='apilotti@cloudbasesolutions.com',
                 url='http://www.cloudbase.it/',
                 classifiers=['Environment :: OpenStack',
                              'Intended Audience :: Information Technology',
                              'Intended Audience :: System Administrators',
                              'License :: OSI Approved :: Apache Software '
                              'License',
                              'Operating System :: Microsoft :: Windows',
                              'Operating System :: POSIX :: Linux',
                              'Operating System :: MacOS :: MacOS X',
                              'Programming Language :: Python',
                              'Programming Language :: Python :: 2',
                              'Programming Language :: Python :: 2.6'],
                 packages=setuptools.find_packages(),
                 install_requires=["nova==2013.2",
                                   "oslo.config",
                                   "psutil"],
                 include_package_data=True,
                 setup_requires=['setuptools_git>=0.4'])
