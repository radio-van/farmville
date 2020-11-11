import os
from utils import write_file


class AlpineContainerMixin:
    """
    Manages container's internal OS.
    OS-specific due to files layout.
    """
    def _create_base_container(self):
        # TODO
        # alpine installation via template
        # apk update
        # root passwd
        # nameserver
        pass

    def container_exec(self, command: str):
        """
        Runs command inside container.
        Container-backend specific and should be defined in mixin.
        """
        super().container_exec(command)

    def install_packages(self, packages_list: list):
        commands = [
            'apk update',
            f'apk add --no-cache {packages_list}',
        ]
        self.container_exec(' && '.join(commands))

    def uninstall_packages(self, packages_list: list):
        self.container_exec(f'apk del --purge {packages_list}')

    def compile_and_install(self, binfile: str, dest: str, makefile: str, source: str):
        """
        Compiles sotware in "source", according to "makefile".
        Moves compiled "binfile" to "dest" and wipes "source".

        Creepy one. Probably too case-related.
        """
        commands = [
            f'make -C {source} -f {makefile}',
            f'mv {source}/bin/{binfile} {dest}',
            f'chmod +x {source}/{binfile}',
            f'rm -rf {source}',
        ]
        self.container_exec(' && '.join(commands))

    @staticmethod
    def _write_internal_default_interface_config(config_path: str):
        write_file(
            path='/'.join((config_path, 'interfaces')),
            lines=[
                'hostname $(hostname)\n',
                '\n',
                'auto lo\n',
                'iface lo inet loopback',
            ])

    def _write_internal_interface_config(self, container_path: str, iface_name: str):
        config_path = f'{container_path}/etc/network'
        if not os.path.exists(config_path):
            os.makedirs(config_path)
            self._write_internal_default_interface_config(config_path=config_path)

        write_file(
            append=True,
            path='/'.join((config_path, 'interfaces')),
            lines=[
                '\n',
                f'auto {iface_name}\n',
                f'iface {iface_name} inet manual',
            ])
