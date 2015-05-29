#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import winrm

from cloudify.exceptions import CommandExecutionException
from cloudify.exceptions import CommandExecutionError
from cloudify.utils import CommandExecutionResponse
from cloudify.utils import setup_logger

from cloudify_agent.installer import utils
from cloudify_agent.api import utils as api_utils

DEFAULT_WINRM_PORT = '5985'
DEFAULT_WINRM_URI = 'wsman'
DEFAULT_WINRM_PROTOCOL = 'http'


def validate(session_config):

    if 'host' not in session_config:
        raise ValueError('Missing host in session_config')
    if session_config['host'] == '':
        raise ValueError('host is empty in session_config')
    if 'user' not in session_config:
        raise ValueError('Missing user in session_config')
    if 'password' not in session_config:
        raise ValueError('Missing password in session_config')


class WinRMRunner(object):

    def __init__(self,
                 protocol=DEFAULT_WINRM_PROTOCOL,
                 host=None,
                 port=DEFAULT_WINRM_PORT,
                 uri=DEFAULT_WINRM_URI,
                 user=None,
                 password=None,
                 validate_connection=True,
                 logger=None):

        logger = logger or setup_logger('WinRMRunner')

        self.session_config = {
            'protocol': protocol,
            'host': host,
            'port': port,
            'uri': uri,
            'user': user,
            'password': password
        }

        # Validations - [host, user, password]
        validate(self.session_config)

        self.session = self._create_session()
        self.logger = logger

        if validate_connection:
            self.validate_connection()

    def validate_connection(self):
        self.logger.debug('Validating WinRM connection')
        self.ping()
        self.logger.debug('WinRM connection is ready')

    def _create_session(self):

        winrm_url = '{0}://{1}:{2}/{3}'.format(
            self.session_config['protocol'],
            self.session_config['host'],
            self.session_config['port'],
            self.session_config['uri'])
        return winrm.Session(
            target=winrm_url,
            auth=(self.session_config['user'],
                  self.session_config['password']))

    def home_dir(self, _):
        self.run('echo $HOME')

    def run(self, command, raise_on_failure=True, execution_env=None):

        """
        :param command: The command to execute.
        :type command: str
        :param raise_on_failure:
            by default, this will raise an exception
            if the command fails. You can use raise_on_failure=False to
            just log the error and not raise an exception.
        :type raise_on_failure: bool
        :param execution_env: environment variables to be applied before
                              running the command
        :type execution_env: dict

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        if execution_env is None:
            execution_env = {}

        remote_env_file = None
        if execution_env:
            env_file = utils.env_to_file(execution_env, posix=False)
            remote_env_file = self.put_file(src=env_file,
                                            dst='{0}.bat'.format(
                                                self.mktemp()))

        def _chk(res):
            if res.status_code == 0:
                self.logger.debug(
                    '[{0}] out: {1}'.format(
                        self.session_config['host'],
                        res.std_out))
            else:
                error = WinRMCommandExecutionException(
                    command=command,
                    code=res.status_code,
                    error=res.std_err,
                    output=res.std_out)
                if raise_on_failure:
                    raise error
                self.logger.error(error)

        self.logger.debug(
            '[{0}] run: {1}'.format(
                self.session_config['host'],
                command))

        if remote_env_file:
            command = 'call {0} & {1}'.format(command)
        try:
            response = self.session.run_cmd(command)
        except BaseException as e:
            raise WinRMCommandExecutionError(
                command=command,
                error=str(e)
            )
        _chk(response)
        return WinRMCommandExecutionResponse(
            command=command,
            output=response.std_err,
            code=response.status_code)

    def ping(self):

        """
        Tests that the winrm connection is working.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        return self.run('echo')

    def download(self, url, output_path=None):

        """
        :param url: URL to the resource to download.
        :param output_path: Local path the resource will be saved as.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        if output_path is None:
            output_path = self.mktemp()

        self.logger.info('Downloading {0}'.format(url))
        self.run(
            '''@powershell -Command "(new-object System.Net.WebClient)
            .Downloadfile('{0}','{1}')"'''
            .format(url, output_path))
        return output_path

    def move(self, src, dst):

        """
        Moves item at <src> to <dst>.

        :param src: Path to the source item.
        :param dst: Path to the destination item.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        return self.run(
            '''@powershell -Command "Move-Item {0} {1}"'''
            .format(src, dst))

    def copy(self, src, dst, force=False):

        """
        Copies item at <src> to <dst>.

        :param src: Path to the source item.
        :param dst: Path to the destination item.
        :param force: Creates missing path if needed.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        if force:
            return self.run(
                '''@powershell -Command "Copy-Item -Recurse -Force {0} {1}"'''
                .format(src, dst))
        return self.run(
            '''@powershell -Command "Copy-Item -Recurse {0} {1}"'''  # NOQA
            .format(src, dst))

    def exists(self, path):

        """
        Test if the given path exists.

        :param path: The path to tests.

        :rtype boolean
        :raise WinRMCommandExecutionException
        """

        response = self.run(
            '''@powershell -Command "Test-Path {0}"'''  # NOQA
            .format(path))
        return response.output == 'True\r\n'

    def delete(self, path, ignore_missing=False):

        """
        Deletes the resource in the given path.

        :param path:

           The path do delete.
           Can be either a file or a folder.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        return self.run(
            '''@powershell -Command "Remove-Item -Recurse -Force {0}"'''
            .format(path), raise_on_failure=not ignore_missing)

    def mktemp(self):

        """
        Creates a temporary path.

        :return: the temporary path
        :rtype: str

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        temp = self.run(
            '''@powershell -Command "[System.IO.Path]::GetTempFileName()"'''
        ).output
        return self.new_file(temp)

    def new_dir(self, path):

        """
        Creates the path as a new directory.

        :param path: The directory path to create.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        return self.run(
            '''@powershell -Command "New-Item {0} -type directory"'''
            .format(path))

    def new_file(self, path):

        """
        Creates the path as a new file.

        :param path: The file path to create.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        return self.run(
            '''@powershell -Command "New-Item {0} -type file"'''
            .format(path))

    def service_state(self, service_name):

        """
        Queries the state of the given service.

        :param service_name: The service name to query.

        :return

            The state of the service.
                - 'Running'
                - 'Stopped'
                - 'Start Pending'
                - 'Continue Pending'
                - 'Pause Pending'
                - 'Paused'
                - 'Unknown'

        :rtype string.
        :raise WinRMCommandExecutionException.
        """

        response = self.run(
            '''@powershell -Command "(Get-Service -Name {0}).Status"'''  # NOQA
            .format(service_name))
        return response.output.strip()

    def machine_distribution(self):

        """
        Retrieves the distribution information of the host.

        :return: dictionary of the platform distribution as returned from
        'platform.dist()'

        :rtype: dict
        :raise: worker_installer.fabric_runner.FabricCommandExecutionException

        """

        response = self.python(
            imports_line='import platform, json',
            command='json.dumps(platform.dist())'
        )
        return api_utils.json_loads(response)

    def python(self, imports_line, command):

        """
        Run a python command and return the output.

        To overcome the situation where additional info is printed
        to stdout when a command execution occurs, a string is
        appended to the output. This will then search for the string
        and the following closing brackets to retrieve the original output.

        :param imports_line: The imports needed for the command.
        :type imports_line: str
        :param command: The python command to run.
        :type command: str

        :return: the string representation of the return value of
                 the python command
        :rtype: str
        :raise: worker_installer.fabric_runner.FabricCommandExecutionException
        """

        start = '###CLOUDIFYCOMMANDOPEN'
        end = 'CLOUDIFYCOMMANDCLOSE###'

        stdout = self.run('python -c "import sys; {0}; '
                          'sys.stdout.write(\'{1}{2}{3}\\n\''
                          '.format({4}))"'
                          .format(imports_line,
                                  start,
                                  '{0}',
                                  end,
                                  command)).output
        result = stdout[stdout.find(start) - 1 + len(end):
                        stdout.find(end)]
        return result

    def put(self, contents, path):

        """
        Writes the contents to a file in the given path.

        :param contents: The contents to write. string based.
        :param path:

            Path to a file.
            The file must be inside an existing directory.

        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        return self.run(
            '''@powershell -Command "Add-Content {0} '{1}'"'''
            .format(path, contents))

    def get(self, path):

        """
        Reads the contents of the file in the given path.

        :param path: Path to a file.

        :rtype string.
        :raise WinRMCommandExecutionException.
        """

        return self.run(
            '''@powershell -Command "Get-Content {0}"'''
            .format(path)).output

    def unzip(self, archive, destination):

        """
        Un-tars an archive. internally this will use the 'tar' command line,
        so any archive supported by it is ok.

        :param archive: path to the archive.
        :type archive: str
        :param destination: destination directory
        :type destination: str

        :return: a response object containing information
                 about the execution
        :rtype WinRMCommandExecutionResponse.
        :raise WinRMCommandExecutionException.
        """

        self.run(
            '''@powershell -Command "Add-Type -assembly
            "system.io.compression.filesystem""'''
        )
        return self.run(
            '''@powershell -Command
            "[io.compression.zipfile]::ExtractToDirectory({0}, {1})"'''
            .format(archive, destination))

    def put_file(self, src, dst=None):

        """
        Copies a file from the src path on the host machine to the dst path
        on the target machine

        :param src: Path to a local file.
        :type src: str
        :param dst: The remote path the file will copied to.
        :type dst: str

        :return: the destination path
        :rtype: str
        """

        with open(src) as f:
            content = f.read()

        if not dst:
            dst = self.mktemp()
        return self.put(contents=content, path=dst)

    def close(self):
        pass


class WinRMCommandExecutionError(CommandExecutionError):

    """
    Indicates a failure occurred while trying to execute the command.

    """

    pass


class WinRMCommandExecutionException(CommandExecutionException):

    """
    Indicates a failure to execute a command over WinRM.

    """
    pass


class WinRMCommandExecutionResponse(CommandExecutionResponse):

    """
    Wrapper for indicating the command was originated from a winrm session.
    """
    pass
