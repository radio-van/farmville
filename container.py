from backends.container import LxcContainerBackend
from backends.os import AlpineContainerMixin


class Container(LxcContainerBackend, AlpineContainerMixin):
    """
    Base Container class with unified API.
    """
    def __init__(self, name, base=None):
        self._interfaces = []
        super().__init__(base=base, name=name)

    @property
    def interfaces(self):
        return self._interfaces

    @property
    def ip(self):
        internal_interfaces = [iface for iface in self.interfaces if iface['type'] == 'internal']

        if len(internal_interfaces) != 1:
            raise Exception('Container must have one and only one internal interface')

        return internal_interfaces[0]['address']

    @property
    def name(self):
        return super().name

    @property
    def state(self):
        """
        Container's state, e.g. 'running' or 'stopped'.
        Defined by backend.
        """
        return super().state

    def add_interface(self, iface_type: str, ip: str, iface_link=None):
        """
        Creates network interface inside container.
        This process consist of two parts:
        - add interface to container's config. This is container's backend specific
          and should be defined in backend mixin
        - add interface configuration inside container. This is OS-specific
          and should be defined in OS-specific mixin

        "iface_type" could be 'internal' for connecting to bridge between host and container
        or 'external', in this case physical interface on host (specified by "iface_link")
        passthrough into container.

        "ip" defines static ip address of the interface inside container.
        """
        self._interfaces.append(
            super().add_interface(
                iface_link=iface_link,
                iface_type=iface_type,
                ip=ip,
            ))

    def install_packages(self, packages_list: list):
        """
        Installs list of packages into container.
        This proccess is OS-specific and should be defined in mixin.
        """
        super().install_packages(packages_list)

    def uninstall_packages(self, packages_list: list):
        """
        Uninstalls list of packages from container.
        This proccess is OS-specific and should be defined in mixin.
        """
        super().uninstall_packages(packages_list)

    def exec_inside_container(self, command: str):
        """
        Executes command inside container.
        This is OS-specific and should be defined in mixin.
        """
        super().exec_inside_container(command)
