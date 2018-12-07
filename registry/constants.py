from web3.auto.infura.endpoints import build_infura_url


INFURA_KOVAN_DOMAIN = 'kovan.infura.io'
INFURA_RINKEBY_DOMAIN = 'rinkeby.infura.io'
INFURA_MAINNET_DOMAIN = 'mainnet.infura.io'
INFURA_ROPSTEN_DOMAIN = 'ropsten.infura.io'

KOVAN_URL = build_infura_url(INFURA_KOVAN_DOMAIN)
RINKEBY_URL = build_infura_url(INFURA_RINKEBY_DOMAIN)
MAINNET_URL = build_infura_url(INFURA_MAINNET_DOMAIN)
ROPSTEN_URL = build_infura_url(INFURA_ROPSTEN_DOMAIN)

CHAIN_DATA = {
    '1': ('mainnet', MAINNET_URL, 'etherscan.io'),
    '3': ('ropsten', ROPSTEN_URL, 'ropsten.etherscan.io'),
    '4': ('rinkeby', RINKEBY_URL, 'rinkeby.etherscan.io'),
    '42': ('kovan', KOVAN_URL, 'kovan.etherscan.io'),
}
