from django.db import models

from eth_utils import to_canonical_address
from web3.pm import PM


def get_package_versions(registry_address, w3, package_name):
    registry = Registry(registry_address, w3)
    return registry.get_package_versions(package_name)

class Registry(models.Model):
    # todo:
    # ens address
    address = models.CharField(max_length=200, null=True)
    owner = models.CharField(max_length=200, null=True)
    package_count = models.IntegerField()

    def __init__(self, address, w3):
        # validate address ...
        self.address = address
        self.pm = PM(w3)
        self.pm.set_registry(self.address)
        try:
            self.owner = self.pm.registry.owner()
        except Exception:
            raise Exception()
        self.package_count = self.pm.get_package_count()
        # if package_count > 0 ...
        package_names = self.pm.get_all_package_names()
        # package_data = [(name, self.pm.get_all_package_releases(name)) for name in package_names]
        self.packages = [Package(name, self.pm.get_release_count(name)) for name in package_names]
        # for pkg in package_data:
            # release_count = self.pm.get_release_count(pkg[0])
            # for version in pkg[1]:
                # self.packages.append(Package(pkg[0], release_count, *version))

    def get_package_versions(self, package_name):
        versions = self.pm.get_all_package_releases(package_name)
        return versions


class Package(models.Model):
    name = models.CharField(max_length=200, null=True)
    release_count = models.IntegerField(default=0)

    def __init__(self, name, release_count):
        self.name = name
        self.release_count = release_count


class Release(models.Model):
    version = models.CharField(max_length=200, null=True)
    manifest = models.CharField(max_length=500, null=True)

