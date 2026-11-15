// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {DemoBase, BUSD, CCNFT} from "./DemoBase.sol";

contract Buy is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        enabled(nft);
        empty(nft);
        require(busd.allowance(p.a, address(nft)) == BUY_PAYMENT, "Demo: buy approval");
        require(busd.balanceOf(p.a) >= BUY_PAYMENT, "Demo: buy balance");
        vm.startBroadcast(p.a);
        nft.buy(NOMINAL, 2);
        vm.stopBroadcast();
    }
}

contract List is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        enabled(nft);
        require(nft.balanceOf(p.a) == 2 && nft.totalValue() == 2 * NOMINAL, "Demo: buy prerequisite");
        uint256 id = nft.tokenOfOwnerByIndex(p.a, 0);
        (bool onSale,) = nft.tokensOnSale(id);
        require(!onSale && nft.values(id) == NOMINAL, "Demo: listing prerequisite");
        vm.startBroadcast(p.a);
        nft.putOnSale(id, PRICE);
        vm.stopBroadcast();
    }
}

contract Trade is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        enabled(nft);
        require(nft.balanceOf(p.a) == 2 && nft.balanceOf(p.b) == 0, "Demo: seller prerequisite");
        uint256 id = nft.listTokensOnSale(0);
        (bool onSale, uint256 price) = nft.tokensOnSale(id);
        require(onSale && price == PRICE && nft.ownerOf(id) == p.a, "Demo: sale prerequisite");
        require(busd.allowance(p.b, address(nft)) == TRADE_PAYMENT, "Demo: trade approval");
        require(busd.balanceOf(p.b) >= TRADE_PAYMENT, "Demo: trade balance");
        vm.startBroadcast(p.b);
        nft.trade(id);
        vm.stopBroadcast();
    }
}

contract Claim is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        configured(p, busd, nft);
        enabled(nft);
        require(nft.balanceOf(p.b) == 1 && nft.balanceOf(p.a) == 1, "Demo: trade prerequisite");
        uint256[] memory ids = new uint256[](1);
        ids[0] = nft.tokenOfOwnerByIndex(p.b, 0);
        require(nft.values(ids[0]) == NOMINAL, "Demo: claim nominal");
        require(busd.allowance(p.funds, address(nft)) == CLAIM_PAYMENT, "Demo: claim approval");
        require(busd.balanceOf(p.funds) >= 2 * CLAIM_PAYMENT, "Demo: collector reserve");
        vm.startBroadcast(p.b);
        nft.claim(ids);
        vm.stopBroadcast();
    }
}
