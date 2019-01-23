import json
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from ethpm.constants import IPFS_GATEWAY_PREFIX
from ethpm.utils.ipfs import extract_ipfs_path_from_uri, create_ipfs_uri
from ethpm.exceptions import ValidationError
from eth_utils import is_address, to_checksum_address, to_dict, to_tuple
from web3.auto.infura import w3 as mainnet_w3
from web3.auto.infura.ropsten import w3 as ropsten_w3_auto
from web3.pm import PM
from web3 import Web3
from web3.providers.auto import load_provider_from_uri
from web3.middleware import construct_sign_and_send_raw_middleware
from ens import ENS

from django.views.decorators.csrf import csrf_protect

from .models import Registry, get_package_versions, Manifest
from .constants import CHAIN_DATA


# still need to test things
# todo test with non-checksummed
# better handling of bad returns (b'')/ wrong txs

# todo: later
# async ipfs search
# prepare for infura webpoint deprecation
# ens reverse lookup on registry owner
# preview github c-a uri manifests


@csrf_protect
def get_package_data(request):
    if request.method == "POST":
        chain_id = request.POST.get("chain_id")
        w3 = get_w3(chain_id)
        registry_address = to_checksum_address(request.POST.get("registry_address"))
        package_name = request.POST.get("package_name")
        package_data = get_package_versions(registry_address, w3, package_name)
        html = construct_html(package_data)
        return HttpResponse(html)


def construct_html(releases_data):
    html_data = [generate_release_html(rls) for rls in releases_data]
    li_data = [f"<li>{rls[0]}{rls[1]}</li>" for rls in html_data]
    return "".join(li_data)


@to_tuple
def generate_release_html(rls):
    yield f"<h5 class='version_list'>version: <span style='font-weight:900;'>{rls.version}</span></h5>"
    if rls.hyperlink:
        ipfs_hash = rls.hyperlink.split("/")[-1]
        yield f"""
            <h5 class='version_list'>manifest uri: 
                <span style='font-weight:900;'>{rls.manifest_uri}</span>
            </h5>
            <a href='manifest/{ipfs_hash}' target='_blank' style="font-size:1.3em;margin-top:-50px;float:right;">preview</a>
            """
    else:
        yield f"<h5 class='version_list'>manifest uri: <span style='font-weight:900;'>{rls.manifest_uri}</span></h5>"


def index(request):
    template = loader.get_template("registry/index.html")
    if request.method == "POST":
        context = generate_context_for_post(request.POST)
    else:
        context = generate_context_for_get()
    return HttpResponse(template.render(context, request))


def manifest(request, manifest_uri):
    template = loader.get_template("registry/manifest_preview.html")
    try:
        manifest = Manifest(manifest_uri)
    except (ValidationError, json.JSONDecodeError) as exc:
        context = {
            "manifest_uri": create_ipfs_uri(manifest_uri),
            "manifest_data": None,
            "hyperlink": None,
        }
        return HttpResponse(template.render(context, request))

    context = {
        "manifest_uri": create_ipfs_uri(manifest_uri),
        "manifest_data": manifest,
        "hyperlink": f"{IPFS_GATEWAY_PREFIX}{manifest_uri}",
    }
    return HttpResponse(template.render(context, request))


@to_dict
def generate_context_for_post(request):
    # Validate address
    address = request.get("registry_addr")
    chain_id = request.get("chain_id")
    w3 = get_w3(chain_id)
    yield "chain_id", chain_id
    if chain_id == "1":
        ens = ENS(w3.provider)
    yield "chain_name", CHAIN_DATA[chain_id][0]
    yield "connection_info", get_connection_info(w3)
    if is_address(address):
        yield "active_registry", Registry(to_checksum_address(address), w3)
    elif chain_id == "1" and address and ens.address(address):
        yield "active_registry", Registry(address, w3)
    else:
        yield "active_registry", None


@to_dict
def generate_context_for_get():
    # defaults to ropsten
    chain_id = "3"
    w3 = get_w3(chain_id)
    yield "chain_id", chain_id
    yield "chain_name", CHAIN_DATA[chain_id][0]
    yield "connection_info", get_connection_info(w3)
    yield "active_registry", None


def get_w3(chain_id: str):
    if chain_id not in CHAIN_DATA:
        raise Exception("invalid chain_id")
    url = CHAIN_DATA[chain_id][1]
    w3 = Web3(load_provider_from_uri(url))
    w3.enable_unstable_package_management_api()
    return w3


def get_connection_info(w3):
    return w3.isConnected()
