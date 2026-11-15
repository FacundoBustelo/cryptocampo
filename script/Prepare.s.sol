// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {DemoBase, BUSD, CCNFT} from "./DemoBase.sol";

contract Fund is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        fresh(nft);
        require(busd.balanceOf(p.a) == 0 && busd.balanceOf(p.b) == 0 && busd.balanceOf(p.funds) == 0, "Demo: funded");
        require(busd.balanceOf(p.admin) >= 2 * START_BALANCE + RESERVE, "Demo: admin balance");
        vm.startBroadcast(p.admin);
        require(busd.transfer(p.a, START_BALANCE), "Demo: fund A");
        require(busd.transfer(p.b, START_BALANCE), "Demo: fund B");
        require(busd.transfer(p.funds, RESERVE), "Demo: fund collector");
        vm.stopBroadcast();
    }
}

contract Approve is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        fresh(nft);
        address sender = vm.envAddress("DEMO_APPROVER");
        require(sender == p.a || sender == p.b || sender == p.funds, "Demo: invalid approver");
        uint256 amount = sender == p.a ? BUY_PAYMENT : sender == p.b ? TRADE_PAYMENT : CLAIM_PAYMENT;
        // El colector recibe el principal de la compra antes de pagar el reclamo.
        uint256 balance = sender == p.funds ? RESERVE : START_BALANCE;
        require(busd.balanceOf(sender) == balance, "Demo: funding prerequisite");
        require(busd.allowance(sender, address(nft)) == 0, "Demo: already approved");
        vm.startBroadcast(sender);
        require(busd.approve(address(nft), amount), "Demo: approval");
        vm.stopBroadcast();
    }
}

contract Enable is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        fresh(nft);
        require(
            busd.balanceOf(p.a) == START_BALANCE && busd.balanceOf(p.b) == START_BALANCE
                && busd.balanceOf(p.funds) == RESERVE && busd.balanceOf(p.fees) == 0,
            "Demo: funding prerequisite"
        );
        require(
            busd.allowance(p.a, address(nft)) == BUY_PAYMENT && busd.allowance(p.b, address(nft)) == TRADE_PAYMENT
                && busd.allowance(p.funds, address(nft)) == CLAIM_PAYMENT,
            "Demo: approval prerequisite"
        );
        vm.startBroadcast(p.admin);
        nft.setCanBuy(true);
        nft.setCanTrade(true);
        nft.setCanClaim(true);
        vm.stopBroadcast();
    }
}
