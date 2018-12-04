import json
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from eth_utils import is_address
from web3.auto.infura.ropsten import w3

from .forms import RegistryForm
from .models import Registry, get_package_versions

from django.views.decorators.csrf import csrf_protect

# handle multiple w3's
# display address who published package

@csrf_protect
def get_package_data(request):
    template = loader.get_template('registry/package_data.html')
    if request.method == 'POST':
        registry_address = request.POST.get("registry_address")
        package_name = request.POST.get("package_name")
        package_data = get_package_versions(registry_address, w3, package_name)
        html = construct_html(package_data)
        return HttpResponse(html)

def construct_html(package_data):
    html = ""
    for version in package_data:
        html = html + (f"<li>version: {version[0]} // manifest uri: {version[1]}")
    return html

def index(request):
    template = loader.get_template('registry/index.html')
    
    if request.method == 'POST':
        address = request.POST.get('registry_addr')
        if is_address(address):
            context = {
                'connection_info': get_connection_info(),
                'chain_id': get_chain_id(),
                'active_registry': Registry(request.POST.get('registry_addr'), w3),
            }    
        else:
            context = {
                'connection_info': get_connection_info(),
                'chain_id': get_chain_id(),
                'active_registry': None,
            }
    else:
        context = {
            'connection_info': get_connection_info(),
            'chain_id': get_chain_id(),
            'active_registry': None,
        }
    return HttpResponse(template.render(context, request))

def get_connection_info():
    return w3.isConnected()

def get_chain_id():
    return w3.net.version
