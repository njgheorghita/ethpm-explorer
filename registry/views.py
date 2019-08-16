import csv
import json
from pathlib import Path
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

from ens import ENS
from ethpm.constants import IPFS_GATEWAY_PREFIX
from ethpm._utils.ipfs import create_ipfs_uri
from ethpm.exceptions import EthPMValidationError
from eth_utils import is_address, to_checksum_address, to_dict, to_tuple, humanize_ipfs_uri
from web3.auto.infura import w3 as mainnet_w3
from web3.auto.infura.ropsten import w3 as ropsten_w3_auto
from web3.pm import PM
from web3 import Web3
from web3.providers.auto import load_provider_from_uri
from web3.middleware import construct_sign_and_send_raw_middleware

from django.views.decorators.csrf import csrf_protect

from .models import Registry, get_package_versions, Manifest
from .constants import CHAIN_DATA

DIRECTORY_STORE_PATH = Path(__file__).parent / "directory_store.json"


# todo:
# Manifest validation in preview
# Async ipfs search
# Prepare for infura webpoint deprecation
# ENS reverse lookup on registry owner
# Preview github c-a uri manifests


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
    li_data = [f"{rls[0]}" for rls in html_data]
    version_data = "".join(li_data)
    return f"<dl class='row' style='font-size:.8em;'><dt class='col-sm-3' style='text-decoration:underline;'>Version</dt><dt class='col-sm-9' style='text-decoration:underline;'>Manifest URI</dt>{version_data}</dl>"


@to_tuple
def generate_release_html(rls):
    if rls.hyperlink:
        ipfs_hash = rls.hyperlink.split("/")[-1]
        yield f"""
            <dd class="col-sm-3">{rls.version}</dd>
            <dd class="col-sm-7 text"><span>{humanize_ipfs_uri(rls.manifest_uri)}</span></dd>
            <dd class="col-sm-2"><a href='/manifest/{ipfs_hash}' target='_blank' style="float:right;">Details</a></dd>
            """
    else:
        yield f"<dd class='col-sm-3'>{rls.version}</dd><dd class='col-sm-9'>{rls.manifest_uri}</dd>"


def directory(request):
    registries = json.loads(DIRECTORY_STORE_PATH.read_text())
    template = loader.get_template("registry/directory.html")
    context = {"registries": registries}
    return HttpResponse(template.render(context, request))


def index(request):
    template = loader.get_template("registry/index.html")
    if request.POST:
        chain_id = request.POST.get("chain_id")
        chain_name = CHAIN_DATA[chain_id][0]
        return HttpResponseRedirect(f"/browse/{chain_name}")
        # context = generate_context_for_index(request.POST.get("chain_id"))
    else:
        context = generate_context_for_index(None)
    return HttpResponse(template.render(context, request))


def find_registry(request, chain_name):
    registry_addr = request.POST.get("registry_addr")
    if registry_addr:
        return HttpResponseRedirect(f"/browse/{chain_name}/{registry_addr}")
    return browse(request, chain_name, registry_addr)


def browse(request, chain_name, registry_addr):
    template = loader.get_template("registry/index.html")
    context = generate_context_for_post(chain_name, registry_addr)
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
def generate_context_for_post(chain_name, registry_addr):
    # Validate address
    chain_lookup = [
        cid for cid in CHAIN_DATA.keys() if CHAIN_DATA[cid][0] == chain_name
    ]
    if len(chain_lookup) is not 1:
        raise Exception("go to 404")
    chain_id = chain_lookup[0]
    w3 = get_w3(chain_id)
    yield "chain_id", chain_id
    if chain_id == "1":
        ens = ENS(w3.provider)
    yield "chain_name", CHAIN_DATA[chain_id][0]
    yield "connection_info", get_connection_info(w3)
    if is_address(registry_addr):
        yield "active_registry", Registry(to_checksum_address(registry_addr), w3)
    elif chain_id == "1" and registry_addr and ens.address(registry_addr):
        yield "active_registry", Registry(registry_addr, w3)
    else:
        yield "active_registry", None


@to_dict
def generate_context_for_index(chain_id):
    # defaults to ropsten
    if not chain_id:
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
