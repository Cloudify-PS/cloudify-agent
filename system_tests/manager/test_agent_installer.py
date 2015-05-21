########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from cloudify.utils import setup_logger

from system_tests import resources
from cosmo_tester.framework import testenv


import os
os.environ['HANDLER_CONFIGURATION'] = '/home/elip/dev/system-tests-handlers/lab-openstack-eli-handler.yaml'


class AgentInstallerTest(testenv.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.logger = setup_logger(
            'cloudify_agent.system_tests.manager.test_agent_installer')

    def test_agent_installer(self):

        self.blueprint_yaml = resources.get_resource(
            'agents-matrix-blueprint/'
            'agents-matrix-blueprint.yaml')
        self.upload_deploy_and_execute_install(
            inputs={
                'image': self.env.ubuntu_image_id,
                'flavor': self.env.small_flavor_id
            }
        )
        self.execute_uninstall()
