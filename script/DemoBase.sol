// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {BUSD} from "../src/BUSD.sol";
import {CCNFT} from "../src/CCNFT.sol";

/// @notice Parámetros compartidos por Anvil y Sepolia; no contiene claves privadas.
abstract contract DemoBase is Script {
    uint256 public constant START_BALANCE = 1000 ether;
    uint256 public constant RESERVE = 10 ether;
    uint256 public constant NOMINAL = 100 ether;
    uint256 public constant OTHER_NOMINAL = 500 ether;
    uint256 public constant LIMIT = 10_000 ether;
    uint16 public constant BATCH = 10;
    uint16 public constant BUY_FEE = 200;
    uint16 public constant TRADE_FEE = 100;
    uint32 public constant PROFIT = 500;
    uint256 public constant PRICE = 120 ether;
    uint256 public constant BUY_PAYMENT = 204 ether;
    uint256 public constant TRADE_PAYMENT = 121.2 ether;
    uint256 public constant CLAIM_PAYMENT = 105 ether;
    string public constant URI = "ipfs://bafkreihjmwkav7thv25yhsosaemqlvn5necgydfkofak7dl5zel3zuw5t4";

    struct Actors {
        address admin;
        address a;
        address b;
        address funds;
        address fees;
    }

    function actors() internal view returns (Actors memory p) {
        bool sepolia = keccak256(bytes(vm.envOr("DEMO_PROFILE", string("anvil")))) == keccak256("sepolia");
        if (sepolia) {
            require(block.chainid == 11155111, "Demo: chain must be Sepolia");
        } else {
            require(
                keccak256(bytes(vm.envOr("DEMO_PROFILE", string("anvil")))) == keccak256("anvil"),
                "Demo: invalid profile"
            );
            require(block.chainid == 31337, "Demo: chain must be 31337");
        }
        p = Actors(
            vm.envAddress("DEMO_ADMIN"),
            vm.envAddress("DEMO_A"),
            vm.envAddress("DEMO_B"),
            vm.envAddress("DEMO_FUNDS"),
            vm.envAddress("DEMO_FEES")
        );
        address[5] memory accounts = [p.admin, p.a, p.b, p.funds, p.fees];
        for (uint256 i; i < accounts.length; ++i) {
            require(accounts[i] != address(0) && accounts[i].code.length == 0, "Demo: invalid actor");
            for (uint256 j; j < i; ++j) {
                require(accounts[i] != accounts[j], "Demo: duplicate actors");
            }
        }
        if (sepolia) {
            string[5] memory keys = [
                "SEPOLIA_ADMIN_PRIVATE_KEY",
                "SEPOLIA_A_PRIVATE_KEY",
                "SEPOLIA_B_PRIVATE_KEY",
                "SEPOLIA_FUNDS_PRIVATE_KEY",
                "SEPOLIA_FEES_PRIVATE_KEY"
            ];
            for (uint256 i; i < accounts.length; ++i) {
                require(vm.addr(vm.envUint(keys[i])) == accounts[i], "Demo: incorrect signer");
            }
        }
    }

    function begin(address sender) internal {
        if (block.chainid == 11155111) {
            uint256 key = vm.envUint("DEMO_SIGNING_KEY");
            require(vm.addr(key) == sender, "Demo: incorrect signer");
            vm.startBroadcast(key);
        } else {
            vm.startBroadcast(sender);
        }
    }

    function deployed(Actors memory p) internal view returns (BUSD busd, CCNFT nft) {
        busd = BUSD(vm.envAddress("DEMO_BUSD"));
        nft = CCNFT(vm.envAddress("DEMO_CCNFT"));
        require(keccak256(address(busd).code) == keccak256(type(BUSD).runtimeCode), "Demo: incorrect BUSD code");
        require(keccak256(address(nft).code) == keccak256(type(CCNFT).runtimeCode), "Demo: incorrect CCNFT code");
        require(nft.owner() == p.admin, "Demo: incorrect owner");
    }

    function configured(Actors memory p, BUSD busd, CCNFT nft) internal view {
        require(
            address(nft.fundsToken()) == address(busd) && nft.fundsCollector() == p.funds
                && nft.feesCollector() == p.fees,
            "Demo: incorrect payment configuration"
        );
        require(nft.validValues(NOMINAL) && nft.validValues(OTHER_NOMINAL), "Demo: missing nominals");
        require(nft.buyFee() == BUY_FEE && nft.tradeFee() == TRADE_FEE && nft.profitToPay() == PROFIT, "Demo: rates");
        require(nft.maxBatchCount() == BATCH && nft.maxValueToRaise() == LIMIT, "Demo: limits");
    }

    function enabled(CCNFT nft) internal view {
        require(nft.canBuy() && nft.canTrade() && nft.canClaim(), "Demo: operations disabled");
    }

    function empty(CCNFT nft) internal view {
        require(nft.totalSupply() == 0 && nft.totalValue() == 0, "Demo: expected empty collection");
    }

    function fresh(CCNFT nft) internal view {
        empty(nft);
        require(!nft.canBuy() && !nft.canTrade() && !nft.canClaim(), "Demo: operations already enabled");
    }
}
