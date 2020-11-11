from exceptions import ShellCommandException
from typing import Optional
from utils import exec_shell, get_default_gateway, parse_bstring_to_dict, write_file

# TODO read env settings
LXC_BASE_NAME = 'base'
LXC_BRIDGE_IFACE = 'lxcbr0'
LXC_PATH = '/home/farmer/lxc'


class LxcContainerManagementMixin:
    """
    Wrapper around low-level shell calls to LXC.
    """
    @staticmethod
    def container_exec(name: str, command: str):
        # TODO check state and start before trying to attach
        base_command = f'lxc-attach -n {name} --clear-env --'
        try:
            exec_shell(' '.join((base_command, command)))
        except ShellCommandException as exc:
            raise Exception('Failed to exec command inside container') from exc

    @staticmethod
    def container_start(name: str):
        try:
            # TODO check state before trying to start
            exec_shell(f'lxc-start -n {name}')
        except ShellCommandException as exc:
            raise Exception('Failed to start container') from exc

    @staticmethod
    def container_stop(name: str):
        try:
            # TODO check state before trying to stop
            exec_shell(f'lxc-stop -n {name}')
        except ShellCommandException as exc:
            raise Exception('Failed to start container') from exc

    @staticmethod
    def _container_clone(base: str, target: str):
        # TODO check state and stop before trying to copy
        # TODO maybe move to main class
        try:
            exec_shell(f'lxc-copy -n {base} -N {target} -B overlayfs -s')
        except ShellCommandException as exc:
            raise Exception('Failed to create base container clone') from exc

    def _container_state(self, name: str) -> str:
        info = self._container_info(name=name)
        return info.get('State')

    @staticmethod
    def _container_info(name: str) -> dict:
        """
        Low-level output of container info.
        Backend-specific, so should not be called directly.
        """
        try:
            container_info = exec_shell(f'lxc-info -n {name}')
        except ShellCommandException:
            # TODO check that error is 'doesnt exists' and return {} only in that case
            return {}
        return parse_bstring_to_dict(bstring=container_info)


class LxcContainerBackend(LxcContainerManagementMixin):
    def __init__(self, name: str):
        self._name = name

        if self.state == 'not exists':
            self._create()

    def _create(self):
        """
        Creates new container by cloning base one.
        """
        # TODO make base container singletone
        self._base = LxcBaseContainer()
        # TODO add check if OS/FS supports cloning
        self._container_clone(
            base=self.base.name,
            target=self.name,
        )
        self._configure_defaults()

    def add_interface(self, iface_link: Optional[str], iface_type: str, ip: str):
        """
        Writes interface specification into container's config.
        Writes according config into container's OS.
        """
        if iface_type not in ['external', 'internal']:
            raise TypeError('Interface can be external or internal')

        if iface_type == 'external' and iface_link is None:
            raise TypeError('Physical iface must be specified for external interface')

        if iface_type == 'internal' and not iface_link:
            iface_link = LXC_BRIDGE_IFACE

        interface = self._write_container_iface_config(
            ip=ip,
            iface_id=len(self.interfaces) + 1,
            iface_link=iface_link,
            iface_type=iface_type,
        )
        self._write_internal_interface_config(
            container_path=f'{LXC_PATH}/{self.name}/{self.rootfs}',
            iface_name=interface['name'],
        )
        return interface

    @property
    def base(self):
        return self._base

    @property
    def cloned(self):
        return bool(self.base)

    @property
    def interfaces(self):
        raise NotImplementedError('Set in subclass')

    @property
    def name(self):
        return self._name

    @property
    def rootfs(self):
        return 'overlay/delta' if self.cloned else 'rootfs'

    @property
    def state(self):
        """
        Unificate container's state among backends.
        """
        # TODO define states as enum
        if (state := self.container_state(name=self.name)) == 'RUNNING':
            return 'running'
        elif state == 'STOPPED':
            return 'stopped'
        elif state is None:
            return 'not exists'
        else:
            return 'error'

    def _configure_defaults(self):
        self._write_container_default_config()
        self._write_container_specific_config()

    def _write_container_default_config(self):
        """
        Writes defaults specified for all LXC containers
        """
        write_file(
            path=f'{LXC_PATH}/{self.name}/config',
            lines=[
                '# general\n',
                'lxc.include = /usr/share/lxc/config/nesting.conf\n',
                'lxc.arch = linux64\n',
            ])

    def _write_container_specific_config(self):
        """
        Writes per-container defaults
        """
        if self.cloned:
            rootfs_path = f'overlay:{LXC_PATH}/{LXC_BASE_NAME}/rootfs:{LXC_PATH}/{self.name}/overlay'
        else:
            rootfs_path = f'dir:{LXC_PATH}/{self.name}/rootfs'

        config = [
                '\n',
                '# container-specific\n',
                f'lxc.rootfs.path = {rootfs_path}\n',
                f'lxc.uts.name = {self.name}\n',
        ]
        write_file(
            append=True,
            path=f'{LXC_PATH}/{self.name}/config',
            lines=config,
        )

    def _write_container_iface_config(self, iface_gateway: Optional[str],
                                      ip: str, iface_id: int, iface_link: str, iface_type: str) -> dict:
        iface_name = f'eth{iface_id}'

        config = [
            '\n',
            f'# {iface_type} interface\n',
            f'lxc.net.{iface_id}.type = {"phys" if iface_type == "external" else "veth"}\n',
            f'lxc.net.{iface_id}.link = {iface_link}\n',
            f'lxc.net.{iface_id}.flags = up\n',
            f'lxc.net.{iface_id}.name = {iface_name}\n',
            f'lxc.net.{iface_id}.veth.pair = v{self.name.upper()[:10]}\n',
            f'lxc.net.{iface_id}.ipv4.address = {ip}\n',
        ]
        if iface_type == 'external':
            if iface_gateway is None:
                iface_gateway = get_default_gateway(ip)

            config.append(
                f'lxc.net.{iface_id}.ipv4.gateway = {iface_gateway}\n',
            )

        write_file(
            append=True,
            path=f'{LXC_PATH}/{self.name}/config',
            lines=config,
        )

        return {
            'address': ip,
            'link': iface_link,
            'name': iface_name,
            'type': iface_type,
        }

    def _write_internal_default_interface_config(container_path: str):
        """
        This is OS-specific and should be defined in OS mixin.
        """
        super()._write_internal_default_interface_config

    def _write_internal_interface_config(self, container_path: str, iface_name: str):
        """
        This is OS-specific and should be defined in OS mixin.
        """
        super()._write_internal_interface_config


class LxcBaseContainer(LxcContainerBackend):
    def __init__(self):
        super().__init__(LXC_BASE_NAME)

    def _create(self):
        self._base = None
        self.create_base_container()

    def create_base_container(self):
        """
        Base container creation comprises OS and base software installation.
        As this process is depends on user's needs, it should be defined in subclasses.

        In current implementation OS-specific part supposed to be defined in corresponding mixin,
        and software-specific part should be defined in subclass, with use of abstraction around the mixin's methods.
        """
        super()._create_base_container()
