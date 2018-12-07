import json
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from eth_utils import is_address, to_checksum_address, to_dict, to_tuple
from web3.auto.infura import w3 as mainnet_w3
from web3.auto.infura.ropsten import w3 as ropsten_w3_auto
from web3.pm import PM
from web3 import Web3
from web3.providers.auto import load_provider_from_uri
from web3.middleware import construct_sign_and_send_raw_middleware
from ens import ENS

from django.views.decorators.csrf import csrf_protect

from .models import Registry, get_package_versions
from .constants import CHAIN_DATA

# buy plane tix
# and calender dates
# tODO INVOICE DUDE DO IT TOMORROW

# todo better ens support
# todo register the registry address on ens & test
# todo all registries all releases
# deploy to heroku
# instructions / links on how to deploy/build your own
# better handling of bad returns (b'')/ wrong txs


@csrf_protect
def get_package_data(request):
    if request.method == 'POST':
        chain_id = request.POST.get('chain_id')
        w3 = get_w3(chain_id)
        registry_address = to_checksum_address(request.POST.get("registry_address"))
        package_name = request.POST.get("package_name")
        package_data = get_package_versions(registry_address, w3, package_name)
        html = construct_html(package_data)
        return HttpResponse(html)


def construct_html(releases_data):
    html_data = [generate_release_html(rls) for rls in releases_data]
    li_data = [f"<li>{rls[0]}{rls[1]}</li>" for rls in html_data]
    return ''.join(li_data)


@to_tuple
def generate_release_html(rls):
    yield f"<h5 class='version_list'>version: <span style='font-weight:900;'>{rls.version}</span></h5>"
    if rls.hyperlink:
        yield f"<h5 class='version_list'>manifest uri: <a href='{rls.hyperlink}' target='_blank'><span style='font-weight:900;'>{rls.manifest_uri}</span></a></h5>"
    else:
        yield f"<h5 class='version_list'>manifest uri: <span style='font-weight:900;'>{rls.manifest_uri}</span></h5>"


def index(request):
    template = loader.get_template('registry/index.html')
    if request.method == 'POST':
        context = generate_context_for_post(request.POST)
    else:
        context = generate_context_for_get()
    return HttpResponse(template.render(context, request))


@to_dict
def generate_context_for_post(request):
    # Validate address
    address = request.get('registry_addr')
    chain_id = request.get('chain_id')
    w3 = get_w3(chain_id)
    yield 'chain_id', chain_id
    yield 'chain_name', CHAIN_DATA[chain_id][0]
    yield 'connection_info', get_connection_info(w3)
    if is_address(address):
        yield 'active_registry', Registry(to_checksum_address(address), w3)
    else:
        yield 'active_registry', None


@to_dict
def generate_context_for_get():
    # defaults to ropsten
    chain_id = '3'
    w3 = get_w3(chain_id)
    yield 'chain_id', chain_id
    yield 'chain_name', CHAIN_DATA[chain_id][0]
    yield 'connection_info', get_connection_info(w3)
    yield 'active_registry', None


def get_w3(chain_id: str):
    if chain_id not in CHAIN_DATA:
        raise Exception("invalid chain_id")
    url = CHAIN_DATA[chain_id][1]
    w3 = Web3(load_provider_from_uri(url))
    PM.attach(w3, 'pm')
    return w3


def get_connection_info(w3):
    return w3.isConnected()
