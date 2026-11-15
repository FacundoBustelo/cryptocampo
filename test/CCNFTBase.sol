// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {BUSD} from "../src/BUSD.sol";
import {CCNFT} from "../src/CCNFT.sol";

abstract contract CCNFTBase is Test {
    BUSD internal busd;
    CCNFT internal nft;
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);
    address internal funds = address(0xF00D);
    address internal fees = address(0xFEE);

    event Buy(address indexed buyer, uint256 indexed tokenId, uint256 value);
    event BuyPayment(address indexed buyer, uint256 principal, uint256 fee);
    event PutOnSale(address indexed seller, uint256 indexed tokenId, uint256 price);
    event Trade(address indexed buyer, address indexed seller, uint256 indexed tokenId, uint256 price, uint256 fee);
    event Claim(address indexed claimer, uint256 indexed tokenId, uint256 value);
    event ClaimPayment(address indexed claimer, uint256 principal, uint256 profit);

    function setUp() public virtual {
        busd = new BUSD();
        nft = new CCNFT();
        nft.setFundsToken(address(busd));
        nft.setFundsCollector(funds);
        nft.setFeesCollector(fees);
        nft.addValidValues(100 ether);
        nft.addValidValues(500 ether);
        nft.setMaxBatchCount(10);
        nft.setMaxValueToRaise(10_000 ether);
        nft.setBuyFee(200);
        nft.setTradeFee(100);
        nft.setProfitToPay(500);
        nft.setCanBuy(true);
        nft.setCanTrade(true);
        nft.setCanClaim(true);
        assertTrue(busd.transfer(alice, 100_000 ether));
        assertTrue(busd.transfer(bob, 100_000 ether));
        vm.prank(alice);
        assertTrue(busd.approve(address(nft), type(uint256).max));
        vm.prank(bob);
        assertTrue(busd.approve(address(nft), type(uint256).max));
        vm.prank(funds);
        assertTrue(busd.approve(address(nft), type(uint256).max));
    }

    function _buy(address buyer, uint256 value, uint256 amount) internal {
        vm.prank(buyer);
        nft.buy(value, amount);
    }

    function _list(address seller, uint256 id, uint256 price) internal {
        vm.prank(seller);
        nft.putOnSale(id, price);
    }

    function _trade(address buyer, uint256 id) internal {
        vm.prank(buyer);
        nft.trade(id);
    }

    function _ids(uint256 id) internal pure returns (uint256[] memory ids) {
        ids = new uint256[](1);
        ids[0] = id;
    }

    function _claim(address claimer, uint256 id) internal {
        vm.prank(claimer);
        nft.claim(_ids(id));
    }

    function _assertNoSale(uint256 id) internal view {
        (bool onSale, uint256 price) = nft.tokensOnSale(id);
        assertFalse(onSale);
        assertEq(price, 0);
    }

    function _assertListLength(uint256 length) internal view {
        // El getter de un array publico revierte al acceder fuera de rango.
        for (uint256 i; i < length; ++i) {
            nft.listTokensOnSale(i);
        }
        (bool ok,) = address(nft).staticcall(abi.encodeCall(nft.listTokensOnSale, (length)));
        assertFalse(ok);
    }

    function _assertAccounting() internal view {
        uint256 nominal;
        for (uint256 i; i < nft.totalSupply(); ++i) {
            uint256 id = nft.tokenByIndex(i);
            nominal += nft.values(id);
            address holder = nft.ownerOf(id);
            uint256 occurrences;
            for (uint256 j; j < nft.balanceOf(holder); ++j) {
                if (nft.tokenOfOwnerByIndex(holder, j) == id) ++occurrences;
            }
            assertEq(occurrences, 1);
        }
        assertEq(nft.totalValue(), nominal);
        assertEq(busd.balanceOf(address(nft)), 0);
    }
}
