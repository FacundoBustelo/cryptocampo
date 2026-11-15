// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {CCNFTBase} from "./CCNFTBase.sol";

contract CCNFTOperationsTest is CCNFTBase {
    function testAcceptanceBalancesEventsAndFinalNominal() public {
        uint256 aliceStart = busd.balanceOf(alice);
        uint256 bobStart = busd.balanceOf(bob);
        vm.prank(alice);
        busd.approve(address(nft), 204 ether);
        vm.prank(bob);
        busd.approve(address(nft), 121.2 ether);
        vm.prank(funds);
        busd.approve(address(nft), 105 ether);

        vm.expectEmit(true, true, false, true, address(nft));
        emit Buy(alice, 0, 100 ether);
        vm.expectEmit(true, true, false, true, address(nft));
        emit Buy(alice, 1, 100 ether);
        vm.expectEmit(true, false, false, true, address(nft));
        emit BuyPayment(alice, 200 ether, 4 ether);
        _buy(alice, 100 ether, 2);
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.ownerOf(1), alice);
        assertEq(busd.balanceOf(alice), aliceStart - 204 ether);
        assertEq(busd.balanceOf(funds), 200 ether);
        assertEq(busd.balanceOf(fees), 4 ether);
        assertEq(nft.totalValue(), 200 ether);

        vm.expectEmit(true, true, false, true, address(nft));
        emit PutOnSale(alice, 0, 120 ether);
        _list(alice, 0, 120 ether);
        vm.expectEmit(true, true, true, true, address(nft));
        emit Trade(bob, alice, 0, 120 ether, 1.2 ether);
        _trade(bob, 0);
        assertEq(nft.ownerOf(0), bob);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.totalValue(), 200 ether);
        assertEq(busd.balanceOf(alice), aliceStart - 84 ether);
        assertEq(busd.balanceOf(bob), bobStart - 121.2 ether);
        _assertNoSale(0);
        _assertListLength(0);

        vm.expectEmit(true, true, false, true, address(nft));
        emit Claim(bob, 0, 100 ether);
        vm.expectEmit(true, false, false, true, address(nft));
        emit ClaimPayment(bob, 100 ether, 5 ether);
        _claim(bob, 0);
        assertEq(busd.balanceOf(alice), aliceStart - 84 ether);
        assertEq(busd.balanceOf(bob), bobStart - 16.2 ether);
        assertEq(busd.balanceOf(funds), 95 ether);
        assertEq(busd.balanceOf(fees), 5.2 ether);
        assertEq(busd.allowance(alice, address(nft)), 0);
        assertEq(busd.allowance(bob, address(nft)), 0);
        assertEq(busd.allowance(funds, address(nft)), 0);
        assertEq(nft.totalValue(), 100 ether);
        assertEq(nft.values(0), 0);
        assertEq(nft.totalSupply(), 1);
        assertEq(nft.tokenByIndex(0), 1);
        assertEq(nft.tokenOfOwnerByIndex(alice, 0), 1);
        assertEq(nft.balanceOf(bob), 0);
        _assertNoSale(0);
        _assertAccounting();
    }

    function testBuyAndClaimAtExactBatchAndNominalLimits() public {
        nft.setMaxValueToRaise(1_000 ether);
        _buy(alice, 100 ether, 10);
        assertEq(nft.totalValue(), 1_000 ether);
        assertEq(nft.totalSupply(), 10);
        vm.expectRevert("Max value exceeded");
        _buy(bob, 100 ether, 1);
        busd.transfer(funds, 50 ether);
        uint256[] memory ids = new uint256[](10);
        for (uint256 i; i < ids.length; ++i) ids[i] = i;
        vm.prank(alice);
        nft.claim(ids);
        assertEq(nft.totalValue(), 0);
        assertEq(nft.totalSupply(), 0);
        assertEq(busd.balanceOf(funds), 0);
        _buy(bob, 500 ether, 2);
        assertEq(nft.ownerOf(10), bob);
        assertEq(nft.ownerOf(11), bob);
        _assertAccounting();
    }

    function testInvalidBuyInputsAndZeroCap() public {
        vm.expectRevert("Invalid batch size");
        _buy(alice, 100 ether, 0);
        vm.expectRevert("Invalid batch size");
        _buy(alice, 100 ether, 11);
        vm.expectRevert("Invalid value");
        _buy(alice, 0, 1);
        vm.expectRevert("Invalid value");
        _buy(alice, 101 ether, 1);
        nft.setMaxValueToRaise(99 ether);
        vm.expectRevert("Max value exceeded");
        _buy(alice, 100 ether, 1);
        nft.setMaxValueToRaise(0);
        vm.expectRevert("Max value exceeded");
        _buy(alice, 100 ether, 1);
        assertEq(nft.totalSupply(), 0);
        _assertAccounting();
    }

    function testListingUpdatesWithoutDuplicatesAndSwapPopRemovesAllPositions() public {
        _buy(alice, 100 ether, 4);
        for (uint256 i; i < 4; ++i) _list(alice, i, 120 ether);
        _list(alice, 0, 130 ether);
        (bool onSale, uint256 price) = nft.tokensOnSale(0);
        assertTrue(onSale);
        assertEq(price, 130 ether);
        _assertListLength(4);
        assertEq(busd.balanceOf(fees), 8 ether);
        _trade(bob, 1); // Posicion intermedia reemplazada por el ultimo elemento.
        assertEq(nft.listTokensOnSale(1), 3);
        _assertListLength(3);
        _assertNoSale(1);
        _trade(bob, 2); // Ultimo elemento.
        _assertListLength(2);
        _trade(bob, 0); // Primer elemento.
        assertEq(nft.listTokensOnSale(0), 3);
        _assertListLength(1);
        _trade(bob, 3); // Unico elemento.
        _assertListLength(0);
        _assertNoSale(0);
        _assertNoSale(2);
        _assertNoSale(3);
        assertEq(nft.totalValue(), 400 ether);
        assertEq(nft.balanceOf(alice), 0);
        assertEq(nft.balanceOf(bob), 4);
        _assertAccounting();
    }

    function testPublicationAndTradeRejections() public {
        vm.expectRevert("Token does not exist");
        _list(alice, 99, 1);
        vm.expectRevert("Token does not exist");
        _trade(bob, 99);
        _buy(alice, 100 ether, 1);
        vm.expectRevert("Only owner can sell");
        _list(bob, 0, 120 ether);
        vm.expectRevert("Invalid price");
        _list(alice, 0, 0);
        vm.expectRevert("Token not On Sale");
        _trade(bob, 0);
        _list(alice, 0, 120 ether);
        vm.expectRevert("Buyer is the Seller");
        _trade(alice, 0);
        _trade(bob, 0);
        vm.expectRevert("Token not On Sale");
        _trade(alice, 0);
        vm.expectRevert("Only owner can sell");
        _list(alice, 0, 1);
        _list(bob, 0, 200 ether);
        _assertListLength(1);
        _assertAccounting();
    }

    function testClaimMixedNominalsAndPublishedTokens() public {
        _buy(alice, 100 ether, 2);
        _buy(alice, 500 ether, 1);
        _list(alice, 0, 120 ether);
        _list(alice, 1, 130 ether);
        _list(alice, 2, 600 ether);
        busd.transfer(funds, 35 ether);
        uint256 beforeBalance = busd.balanceOf(alice);
        uint256[] memory ids = new uint256[](2);
        ids[0] = 0;
        ids[1] = 2;
        vm.prank(alice);
        nft.claim(ids);
        assertEq(busd.balanceOf(alice), beforeBalance + 630 ether);
        assertEq(nft.totalValue(), 100 ether);
        assertEq(nft.totalSupply(), 1);
        assertEq(nft.values(0), 0);
        assertEq(nft.values(2), 0);
        _assertNoSale(0);
        _assertNoSale(2);
        _assertListLength(1);
        assertEq(nft.listTokensOnSale(0), 1);
        _claim(alice, 1);
        assertEq(nft.totalValue(), 0);
        _assertListLength(0);
        _assertAccounting();
    }

    function testClaimInvalidBatchesThirdPartyAndDuplicatesAreAtomic() public {
        _buy(alice, 100 ether, 2);
        _list(alice, 0, 120 ether);
        uint256[] memory empty = new uint256[](0);
        vm.expectRevert("Invalid batch size");
        vm.prank(alice);
        nft.claim(empty);
        uint256[] memory tooMany = new uint256[](11);
        vm.expectRevert("Invalid batch size");
        vm.prank(alice);
        nft.claim(tooMany);
        vm.expectRevert("Only owner can Claim");
        _claim(bob, 0);
        vm.expectRevert("Token does not exist");
        _claim(alice, 999);
        uint256[] memory duplicate = new uint256[](2);
        duplicate[0] = 0;
        duplicate[1] = 0;
        vm.expectRevert("Token does not exist");
        vm.prank(alice);
        nft.claim(duplicate);
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.values(0), 100 ether);
        (bool onSale, uint256 price) = nft.tokensOnSale(0);
        assertTrue(onSale);
        assertEq(price, 120 ether);
        assertEq(nft.listTokensOnSale(0), 0);
        // El segundo ID invalido tampoco permite quemar el primero.
        duplicate[1] = 999;
        vm.expectRevert("Token does not exist");
        vm.prank(alice);
        nft.claim(duplicate);
        assertEq(nft.ownerOf(0), alice);
        _assertAccounting();
    }

    function testBurnedIdsCannotBeUsedOrReissued() public {
        _buy(alice, 100 ether, 1);
        busd.transfer(funds, 5 ether);
        _claim(alice, 0);
        vm.expectRevert("Token does not exist");
        _claim(alice, 0);
        vm.expectRevert("Token does not exist");
        _list(alice, 0, 1);
        vm.expectRevert("Token does not exist");
        _trade(bob, 0);
        vm.expectRevert("ERC721: owner query for nonexistent token");
        nft.ownerOf(0);
        _buy(alice, 100 ether, 1);
        assertEq(nft.ownerOf(1), alice);
        assertEq(nft.tokenByIndex(0), 1);
        assertEq(nft.values(0), 0);
        _assertAccounting();
    }

    function testClaimWithAnotherOwnersTokenRestoresEarlierBurn() public {
        _buy(alice, 100 ether, 1);
        _buy(bob, 500 ether, 1);
        _list(alice, 0, 120 ether);
        uint256[] memory ids = new uint256[](2);
        ids[0] = 0;
        ids[1] = 1;
        vm.expectRevert("Only owner can Claim");
        vm.prank(alice);
        nft.claim(ids);
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.ownerOf(1), bob);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.values(1), 500 ether);
        assertEq(busd.balanceOf(funds), 600 ether);
        assertEq(nft.listTokensOnSale(0), 0);
        _assertListLength(1);
        _assertAccounting();
    }

    function testLoweringCapDoesNotPreventClaimOrChangeOutstandingNominal() public {
        _buy(alice, 100 ether, 2);
        nft.setMaxValueToRaise(100 ether);
        assertEq(nft.totalValue(), 200 ether);
        vm.expectRevert("Max value exceeded");
        _buy(bob, 100 ether, 1);
        _claim(alice, 0);
        assertEq(nft.totalValue(), 100 ether);
        vm.expectRevert("Max value exceeded");
        _buy(bob, 100 ether, 1);
        busd.transfer(funds, 10 ether);
        _claim(alice, 1);
        _buy(bob, 100 ether, 1);
        assertEq(nft.ownerOf(2), bob);
        _assertAccounting();
    }

    function testOverflowRevertsWithoutPartialState() public {
        nft.addValidValues(type(uint256).max);
        nft.setMaxValueToRaise(type(uint256).max);
        vm.expectRevert(abi.encodeWithSignature("Panic(uint256)", 0x11));
        _buy(alice, type(uint256).max, 2);
        assertEq(nft.totalValue(), 0);
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.values(0), 0);
        _assertAccounting();
    }

    function testAllPublicTransfersBlockedEvenWithApproval() public {
        _buy(alice, 100 ether, 1);
        vm.prank(alice);
        nft.approve(bob, 0);
        vm.startPrank(bob);
        vm.expectRevert("Not Allowed");
        nft.transferFrom(alice, bob, 0);
        vm.expectRevert("Not Allowed");
        nft.safeTransferFrom(alice, bob, 0);
        vm.expectRevert("Not Allowed");
        nft.safeTransferFrom(alice, bob, 0, "data");
        vm.stopPrank();
        assertEq(nft.ownerOf(0), alice);
        _assertAccounting();
    }

    function testZeroFeesAndProfit() public {
        nft.setBuyFee(0);
        nft.setTradeFee(0);
        nft.setProfitToPay(0);
        vm.prank(alice);
        busd.approve(address(nft), 100 ether);
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        vm.prank(bob);
        busd.approve(address(nft), 120 ether);
        _trade(bob, 0);
        _claim(bob, 0);
        assertEq(busd.balanceOf(fees), 0);
        assertEq(busd.balanceOf(funds), 0);
        _assertAccounting();
    }

    function testOneHundredPercentFeesAndProfitAboveOneHundredPercent() public {
        nft.setBuyFee(10_000);
        nft.setTradeFee(10_000);
        nft.setProfitToPay(15_000);
        _buy(alice, 100 ether, 1);
        assertEq(busd.balanceOf(fees), 100 ether);
        _list(alice, 0, 120 ether);
        _trade(bob, 0);
        assertEq(busd.balanceOf(fees), 220 ether);
        busd.transfer(funds, 150 ether);
        uint256 beforeBalance = busd.balanceOf(bob);
        _claim(bob, 0);
        assertEq(busd.balanceOf(bob), beforeBalance + 250 ether);
        _assertAccounting();
    }

    function testRoundingUsesBatchTotalsInMinimumUnits() public {
        nft.addValidValues(3);
        nft.setBuyFee(2_000);
        nft.setTradeFee(2_000);
        nft.setProfitToPay(2_000);
        _buy(alice, 3, 2); // floor(6 * 20%) = 1; no floor(3 * 20%) * 2.
        assertEq(busd.balanceOf(fees), 1);
        assertEq(busd.balanceOf(funds), 6);
        _list(alice, 0, 9);
        _trade(bob, 0); // floor(9 * 20%) = 1, sobre precio y no sobre nominal.
        assertEq(busd.balanceOf(fees), 2);
        _list(bob, 0, 1);
        _trade(alice, 0); // Comision redondeada a cero.
        busd.transfer(funds, 1);
        uint256[] memory ids = new uint256[](2);
        ids[0] = 0;
        ids[1] = 1;
        uint256 beforeBalance = busd.balanceOf(alice);
        vm.prank(alice);
        nft.claim(ids); // Beneficio sobre suma de nominales: 1.
        assertEq(busd.balanceOf(alice), beforeBalance + 7);
        _assertAccounting();
    }
}
