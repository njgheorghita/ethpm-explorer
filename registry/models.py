from django.db import models
from django.forms import ModelForm

from ethpm.constants import IPFS_GATEWAY_PREFIX
from ethpm.utils.ipfs import is_ipfs_uri, extract_ipfs_path_from_uri 
from eth_utils import to_canonical_address
from web3.pm import PM, SolidityReferenceRegistry
from web3.exceptions import BadFunctionCallOutput

from .constants import CHAIN_DATA


def get_package_versions(registry_address, w3, package_name):
    registry = Registry(registry_address, w3)
    return registry.get_package_versions(package_name)


def get_etherscan_link(chain_id, address):
    if chain_id not in ['1', '3', '4', '42']:
        raise Exception('invalid chain_id')
    return f"https://{CHAIN_DATA[chain_id]}/search?q={address}"


class Registry(models.Model):
    address = models.CharField(max_length=200, null=True)
    owner = models.CharField(max_length=200, null=True)
    registry_link = models.CharField(max_length=200, null=True)
    owner_link = models.CharField(max_length=200, null=True)
    package_count = models.IntegerField()

    def __init__(self, address, w3):
        # validate address ...
        self.address = address
        self.w3 = w3
        w3.pm.set_registry(address)
        chain_id = self.w3.net.version
        try:
            # implementation agnostic
            self.owner = w3.pm.registry.owner()
            self.package_count = w3.pm.get_package_count()
            self.registry_link = get_etherscan_link(chain_id, self.address)
            self.owner_link = get_etherscan_link(chain_id, self.owner)
        except BadFunctionCallOutput:
            self.owner = f"contract found @ {address} does not look like it conforms to ERC1319"
            self.owner_link = None
            self.registry_link = get_etherscan_link(chain_id, self.address)
            self.package_count = 0
        else:
            # assert package_count > 0 ???
            try:
                package_names = w3.pm.get_all_package_names()
                self.packages = [Package(name, w3.pm.get_release_count(name)) for name in package_names]
            except BadFunctionCallOutput:
                try:
                    sol_registry = SolidityReferenceRegistry(self.address, self.w3)
                    self.w3.pm.registry = sol_registry
                    package_names = w3.pm.get_all_package_names()
                    self.packages = [Package(name, w3.pm.get_release_count(name)) for name in package_names]
                except BadFunctionCallOutput:
                    self.owner = f"contract found @ {address} does not look like it conforms to ERC1319"
                    self.owner_link = None
                    self.address_link = None
                    self.package_count = 0


    def get_package_versions(self, package_name):
        versions_data = self.w3.pm.get_all_package_releases(package_name)
        releases = [Release(package_name, data[0], data[1]) for data in versions_data]
        return releases


class Package(models.Model):
    name = models.CharField(max_length=200, null=True)
    release_count = models.IntegerField(default=0)

    def __init__(self, name, release_count):
        self.name = name
        self.release_count = release_count


class Release(models.Model):
    package_name = models.CharField(max_length=200, null=True)
    version = models.CharField(max_length=200, null=True)
    manifest_uri = models.CharField(max_length=1000, null=True)
    hyperlink = models.CharField(max_length=500, null=True)

    def __init__(self, package_name, version, manifest_uri):
        self.package_name = package_name
        self.version = version
        self.manifest_uri = manifest_uri
        self.hyperlink = self.generate_hyperlink(manifest_uri)

    def generate_hyperlink(self, manifest_uri):
        if is_ipfs_uri(manifest_uri):
            ipfs_hash = extract_ipfs_path_from_uri(manifest_uri)
            return f"{IPFS_GATEWAY_PREFIX}{ipfs_hash}"
        return None
