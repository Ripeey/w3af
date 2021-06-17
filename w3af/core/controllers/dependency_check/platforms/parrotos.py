import distro, platform

from .ubuntu1204 import Ubuntu1204
from ..requirements import CORE, GUI

class ParrotOS(Ubuntu1204):
    SYSTEM_NAME = 'Parrot OS'
    PIP_CMD = 'pip3'
    del Ubuntu1204.CORE_SYSTEM_PACKAGES[0]
    del Ubuntu1204.GUI_SYSTEM_PACKAGES[0]

    # extra pip faulty addon
    Ubuntu1204.CORE_SYSTEM_PACKAGES.append('python3-esmre')
    # no work for now
    #Ubuntu1204.CORE_SYSTEM_PACKAGES.append('python3-darts.lib.utils.lru')

    SYSTEM_PACKAGES = {CORE: Ubuntu1204.CORE_SYSTEM_PACKAGES,
                       GUI: Ubuntu1204.GUI_SYSTEM_PACKAGES}
    @staticmethod
    def is_current_platform():
        dist_name, dist_version, _ = distro.linux_distribution()
        return 'debian' == dist_name and 'parrot' == dist_version
