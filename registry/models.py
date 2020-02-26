from django.db import models
from django.forms import ModelForm
from typing import Any, Dict
import json

from eth_utils import to_tuple, to_dict
from eth_utils import to_canonical_address, to_text
from ens import ENS
from ethpm._utils.chains import parse_BIP122_uri
from ethpm._utils.ipfs import is_ipfs_uri, extract_ipfs_path_from_uri, create_ipfs_uri
from ethpm.constants import IPFS_GATEWAY_PREFIX
from ethpm.uri import resolve_uri_contents
from ethpm.validation.manifest import (
    validate_raw_manifest_format,
    validate_manifest_against_schema,
)
from web3._utils.validation import validate_address
from web3.exceptions import BadFunctionCallOutput

from .constants import CHAIN_DATA
from .utils import humanize_address


def get_package_versions(registry_address, w3, package_name):
    registry = Registry(registry_address, w3)
    return registry.get_package_versions(package_name)


def get_etherscan_link(chain_id, address):
    if chain_id not in ["1", "3", "4", "42"]:
        raise Exception("invalid chain_id")
    link = f"https://{CHAIN_DATA[chain_id][2]}/search?q={address}"
    return link


class Registry(models.Model):
    package_count = models.IntegerField()
    chain_id = models.CharField(max_length=3, null=True)
    owner = models.CharField(max_length=200, null=True)
    address = models.CharField(max_length=200, null=True)
    humanized_addr = models.CharField(max_length=200, null=True)
    ens_domain = models.CharField(max_length=200, null=True)
    owner_link = models.CharField(max_length=200, null=True)
    registry_link = models.CharField(max_length=200, null=True)

    def __init__(self, address, w3):
        super().__init__()
        self.w3 = w3
        self.chain_id = self.w3.net.version
        ens = ENS(self.w3.provider)
        if self.chain_id == "1" and ens.address(address):
            self.address = ens.address(address)
            self.humanized_addr = humanize_address(self.address)
            self.ens_domain = address
        else:
            validate_address(to_canonical_address(address))
            self.address = address
            self.humanized_addr = humanize_address(self.address)
            self.ens_domain = None

        w3.pm.set_registry(self.address)
        try:
            # no owner is required for a valid ERC1319 registry
            try:
                owner_addr = w3.pm.registry.registry.functions.owner().call()
                self.owner = humanize_address(owner_addr)
                self.owner_link = get_etherscan_link(self.chain_id, owner_addr)
            except BadFunctionCallOutput:
                self.owner = "0x"
            self.package_count = w3.pm.get_package_count()
            self.registry_link = get_etherscan_link(self.chain_id, self.address)
        except BadFunctionCallOutput:
            self.owner = gen_invalid_registry_address(address, self.chain_id)
            self.owner_link = None
            self.registry_link = get_etherscan_link(self.chain_id, self.address)
            self.package_count = 0
        else:
            try:
                package_names = w3.pm.get_all_package_names()
                self.packages = [
                    Package(name, w3.pm.get_release_count(name))
                    for name in package_names
                ]
            except BadFunctionCallOutput:	
                self.owner = gen_invalid_registry_address(address, self.chain_id)	
                self.owner_link = None	
                self.registry_link = None	
                self.package_count = 0

    def get_package_versions(self, package_name):
        versions_data = self.w3.pm.get_all_package_releases(package_name)
        if self.chain_id == "1":
            ethpm_uri_prefix = f"ethpm://{self.address}/"
        else:
            ethpm_uri_prefix = f"ethpm://{self.address}:{self.chain_id}/"
        releases = [Release(package_name, data[0], data[1], ethpm_uri_prefix) for data in versions_data]
        return releases


def gen_invalid_registry_address(address, chain_id):
    return f"Contract found @ {address} on {CHAIN_DATA[chain_id][0]} does not look like it conforms to ERC1319."


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
    ethpm_uri_prefix = models.CharField(max_length=500, null=True)

    def __init__(self, package_name, version, manifest_uri, ethpm_uri_prefix):
        self.package_name = package_name
        self.version = version
        self.manifest_uri = manifest_uri
        self.hyperlink = generate_hyperlink(manifest_uri)
        self.ethpm_uri_prefix = ethpm_uri_prefix

    @property
    def ethpm_uri(self):
        return f"{self.ethpm_uri_prefix}{self.package_name}@{self.version}"


def generate_hyperlink(manifest_uri):
    if is_ipfs_uri(manifest_uri):
        ipfs_hash = extract_ipfs_path_from_uri(manifest_uri)
        return f"{IPFS_GATEWAY_PREFIX}{ipfs_hash}"
    return None


class Manifest(models.Model):
    package_name = models.CharField(max_length=200, null=True)
    version = models.CharField(max_length=200, null=True)
    manifest_version = models.CharField(max_length=200, null=True)
    authors = models.CharField(max_length=1000, null=True)
    description = models.CharField(max_length=10000, null=True)
    license = models.CharField(max_length=200, null=True)
    keywords = models.CharField(max_length=1000, null=True)
    links = models.CharField(max_length=1000, null=True)
    sources = models.CharField(max_length=1000, null=True)
    contract_types = models.CharField(max_length=1000, null=True)
    deployments = models.CharField(max_length=1000, null=True)
    build_dependencies = models.CharField(max_length=1000, null=True)

    def __init__(self, ipfs_hash):
        manifest_uri = create_ipfs_uri(ipfs_hash)
        contents = to_text(resolve_uri_contents(manifest_uri))
        # validate_raw_manifest_format(contents)
        validate_manifest_against_schema(json.loads(contents))
        # validate_manifest_deployments(contents)
        manifest = json.loads(contents)
        self.package_name = manifest["package_name"]
        self.version = manifest["version"]
        self.manifest_version = manifest["manifest_version"]
        self.authors = None
        self.description = None
        self.license = None
        self.keywords = None
        self.links = None
        self.sources = None
        self.contract_types = None
        self.deployments = None
        self.build_dependencies = None
        if "meta" in manifest:
            meta = manifest["meta"]
            if "authors" in meta:
                self.authors = ", ".join(meta["authors"])
            if "description" in meta:
                self.description = f"<span>{meta['description']}</span>"
            if "license" in meta:
                self.license = f"<span>{meta['license']}</span>"
            if "keywords" in meta:
                self.keywords = ", ".join(meta["keywords"])
            if "links" in meta:
                self.links = links_to_table(meta["links"])
        if "sources" in manifest:
            self.sources = simple_dict_to_table(manifest["sources"])
        if "contract_types" in manifest:
            self.contract_types = contract_types_to_table(manifest["contract_types"])
        if "deployments" in manifest:
            self.deployments = deployments_to_table(manifest["deployments"])
        if "build_dependencies" in manifest:
            self.build_dependencies = simple_dict_to_table(
                manifest["build_dependencies"]
            )


def deployments_to_table(deps):
    chain_data = [process_chain(dep) for dep in deps.items()]
    dep_html = [f"<dl class='row'>{html[0]}{html[1]}</dl>" for html in chain_data]
    return "".join(dep_html)


def escape_angles(string):
    return string.replace(">", "&gt;").replace("<", "&lt;")


@to_tuple
def process_chain(chain):
    chain_uri, deployments = chain
    chain_type = identify_blockchain_uri(chain_uri)
    if chain_type:
        yield f"<dd class='col-sm-12 text' style='font-size:1.5em;text-decoration:underline;'><span style='border-bottom:1px solid grey;'>{chain_type}<br><span style='font-size:0.4em;'>{chain_uri}</span></span></dd>"
    else:
        yield f"<dd class='col-sm-12'>{chain_uri}</dd>"
    deps = [process_deployment(dep, chain_type) for dep in deployments.items()]

    deps_html_list = [
        f"<dd class='col-sm-12'>{dep[0]}</dd><dd class='col-sm-12'><pre>{dep[1]}</pre></dd>"
        for dep in deps
    ]
    deps_html_insert = "".join(deps_html_list)

    yield f"{deps_html_insert}"


def identify_blockchain_uri(uri):
    genesis, _, _ = parse_BIP122_uri(uri)
    for chain in CHAIN_DATA.values():
        if chain[3] == genesis:
            return chain[0]
    return None


@to_dict
def process_deployment_data(data, chain_type):
    chain_id = [
        info for info in CHAIN_DATA.keys() if CHAIN_DATA[info][0] == chain_type
    ][0]
    if "address" in data:
        yield "address", f"<a href='https://{CHAIN_DATA[chain_id][2]}/address/{data['address']}' target='_blank'>{data['address']}</a>"
    if "block" in data:
        yield "block", f"<a href='https://{CHAIN_DATA[chain_id][2]}/block/{data['block']}' target='_blank'>{data['block']}</a>"
    if "transaction" in data:
        yield "transaction", f"<a href='https://{CHAIN_DATA[chain_id][2]}/tx/{data['transaction']}' target='_blank'>{data['transaction']}</a>"
    if "contract_type" in data:
        yield "contract_type", data["contract_type"]
    if "runtime_bytecode" in data:
        yield "runtime_bytecode", data["runtime_bytecode"]


@to_tuple
def process_deployment(dep, chain_type=None):
    name, data = dep
    yield name
    if chain_type:
        yield json.dumps(
            process_deployment_data(data, chain_type), indent=4, sort_keys=True
        )
    else:
        yield json.dumps(data, indent=4, sort_keys=True)


def contract_types_to_table(types):
    type_data = [process_type(ct) for ct in types.items()]
    type_html = [
        f"<dl class='row' style='font-size:0.9em'>{html[0]}{html[1]}</dl>"
        for html in type_data
    ]
    return "".join(type_html)


@to_tuple
def process_type(ct):
    name, data = ct
    safe_id = name.translate({ord(c): None for c in "./-"})
    yield f"<dt class='col-sm-6 text'><span>{name}</span></dt><dd class='col-sm-6'><i class='info far fa-eye' id='{safe_id}' style='cursor:pointer;color:black;'></i></dd>"
    json_data = json.dumps(data)
    yield f"<dd class='col-sm-12'><pre class='source_contract contract_type' id='{safe_id}'>{escape_angles(json_data)}</pre></dd>"


def links_to_table(links):
    data_html = [gen_link_html(link) for link in links.items()]
    html_list = [
        f"<dl class='row' style='font-size:0.9em'>{html[0]}{html[1]}</dl>"
        for html in data_html
    ]
    return "".join(html_list)


@to_tuple
def gen_link_html(data):
    name, uri = data
    yield f"<dt class='col-sm-3'>{name}</dt>"
    if is_ipfs_uri(uri):
        link = generate_hyperlink(uri)
        yield f"<dd class='col-sm-9'><span><a href='{link}' target='_blank'>{uri}</a></span></dd>"
    else:
        yield f"<dd class='col-sm-9'><span><a href='{uri}' target='_blank'>{uri}</a></span></dd>"


def simple_dict_to_table(data):
    data_html = [gen_data_html(item) for item in data.items()]
    html_list = [
        f"<dl class='row' style='font-size:0.9em'>{html[0]}{html[1]}</dl>"
        for html in data_html
    ]
    return "".join(html_list)


@to_tuple
def gen_data_html(data):
    name, uri = data
    if is_ipfs_uri(uri):
        yield f"<dd class='col-sm-3 text'><span>{name}</span></dt>"
        link = generate_hyperlink(uri)
        yield f"<dd class='col-sm-9 text'><span><a href='{link}' target='_blank'>{uri}</a></span></dd>"
    else:
        safe_id = name.translate({ord(c): None for c in "./-"})
        yield f"<dt class='col-sm-6'>{name}</dt><dd class='col-sm-6'><i class='info far fa-eye' id='{safe_id}' style='cursor:pointer;color:black;'></i></dd>"
        yield f"<dd class='col-sm-12'><pre class='source_contract' id='{safe_id}'><code>{escape_angles(uri)}</code></pre></dd>"
