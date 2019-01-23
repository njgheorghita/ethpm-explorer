from web3.auto.infura.endpoints import build_infura_url


INFURA_KOVAN_DOMAIN = "kovan.infura.io"
INFURA_RINKEBY_DOMAIN = "rinkeby.infura.io"
INFURA_MAINNET_DOMAIN = "mainnet.infura.io"
INFURA_ROPSTEN_DOMAIN = "ropsten.infura.io"

KOVAN_URL = build_infura_url(INFURA_KOVAN_DOMAIN)
RINKEBY_URL = build_infura_url(INFURA_RINKEBY_DOMAIN)
MAINNET_URL = build_infura_url(INFURA_MAINNET_DOMAIN)
ROPSTEN_URL = build_infura_url(INFURA_ROPSTEN_DOMAIN)

CHAIN_DATA = {
    # name, url, etherscan_prefix, genesis_block
    "1": (
        "mainnet",
        MAINNET_URL,
        "etherscan.io",
        "0xd4e56740f876aef8c010b86a40d5f56745a118d0906a34e69aec8c0db1cb8fa3",
    ),
    "3": (
        "ropsten",
        ROPSTEN_URL,
        "ropsten.etherscan.io",
        "0x41941023680923e0fe4d74a34bdac8141f2540e3ae90623718e47d66d1ca4a2d",
    ),
    "4": (
        "rinkeby",
        RINKEBY_URL,
        "rinkeby.etherscan.io",
        "0x6341fd3daf94b748c72ced5a5b26028f2474f5f00d824504e4fa37a75767e177",
    ),
    "42": (
        "kovan",
        KOVAN_URL,
        "kovan.etherscan.io",
        "0xa3c565fc15c7478862d50ccd6561e3c06b24cc509bf388941c25ea985ce32cb9",
    ),
}
