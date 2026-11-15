// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {CCNFTBase} from "./CCNFTBase.sol";

contract CCNFTFuzzTest is CCNFTBase {
    function testFuzzBuyFormula(uint256 valueSeed, uint256 amountSeed, uint16 feeSeed) public {
        uint256 value = bound(valueSeed, 1, 500 ether);
        uint256 amount = bound(amountSeed, 1, 10);
        uint16 fee = uint16(bound(uint256(feeSeed), 0, 10_000));
        nft.addValidValues(value);
        nft.setBuyFee(fee);
        uint256 principal = value * amount;
        uint256 commission = principal * fee / 10_000;
        uint256 beforeBalance = busd.balanceOf(alice);
        _buy(alice, value, amount);
        assertEq(busd.balanceOf(alice), beforeBalance - principal - commission);
        assertEq(busd.balanceOf(funds), principal);
        assertEq(busd.balanceOf(fees), commission);
        assertEq(nft.totalSupply(), amount);
        assertEq(nft.totalValue(), principal);
        for (uint256 i; i < amount; ++i) {
            assertEq(nft.ownerOf(i), alice);
            assertEq(nft.values(i), value);
        }
        _assertAccounting();
    }

    function testFuzzTradeFormulaPreservesNominal(uint256 priceSeed, uint16 feeSeed) public {
        uint256 price = bound(priceSeed, 1, 1_000 ether);
        uint16 fee = uint16(bound(uint256(feeSeed), 0, 10_000));
        _buy(alice, 100 ether, 1);
        nft.setTradeFee(fee);
        _list(alice, 0, price);
        uint256 aliceBefore = busd.balanceOf(alice);
        uint256 bobBefore = busd.balanceOf(bob);
        uint256 feesBefore = busd.balanceOf(fees);
        uint256 commission = price * fee / 10_000;
        _trade(bob, 0);
        assertEq(busd.balanceOf(alice), aliceBefore + price);
        assertEq(busd.balanceOf(bob), bobBefore - price - commission);
        assertEq(busd.balanceOf(fees), feesBefore + commission);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.totalValue(), 100 ether);
        _assertNoSale(0);
        _assertListLength(0);
        _assertAccounting();
    }

    function testFuzzClaimFormulaFullUint32Profit(uint256 valueSeed, uint256 amountSeed, uint32 profit) public {
        // Incluso con uint32.max, el pago cabe en el suministro BUSD del ejercicio.
        uint256 value = bound(valueSeed, 1, 1 ether);
        uint256 amount = bound(amountSeed, 1, 10);
        nft.addValidValues(value);
        nft.setProfitToPay(profit);
        _buy(alice, value, amount);
        uint256 principal = value * amount;
        uint256 benefit = principal * profit / 10_000;
        busd.transfer(funds, benefit);
        uint256 beforeBalance = busd.balanceOf(alice);
        uint256 feesBefore = busd.balanceOf(fees);
        uint256[] memory ids = new uint256[](amount);
        for (uint256 i; i < amount; ++i) {
            ids[i] = i;
            if (i % 2 == 0) _list(alice, i, 1);
        }
        vm.prank(alice);
        nft.claim(ids);
        assertEq(busd.balanceOf(alice), beforeBalance + principal + benefit);
        assertEq(busd.balanceOf(funds), 0);
        assertEq(busd.balanceOf(fees), feesBefore);
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.totalValue(), 0);
        for (uint256 i; i < amount; ++i) {
            assertEq(nft.values(i), 0);
            _assertNoSale(i);
        }
        _assertListLength(0);
        _assertAccounting();
    }

    function testFuzzNominalConservationAcrossLifecycle(uint256 amountSeed, uint256 claimSeed, uint256 priceSeed)
        public
    {
        uint256 amount = bound(amountSeed, 2, 10);
        uint256 claimCount = bound(claimSeed, 1, amount - 1);
        uint256 price = bound(priceSeed, 1, 1_000 ether);
        _buy(alice, 100 ether, amount);
        _assertAccounting();
        for (uint256 i; i < claimCount; ++i) {
            _list(alice, i, price);
            _list(alice, i, price + 1);
            _assertListLength(1);
            _trade(bob, i);
            assertEq(nft.totalValue(), amount * 100 ether);
            assertEq(nft.values(i), 100 ether);
            _assertAccounting();
        }
        busd.transfer(funds, claimCount * 5 ether);
        uint256[] memory ids = new uint256[](claimCount);
        for (uint256 i; i < claimCount; ++i) {
            ids[i] = i;
        }
        vm.prank(bob);
        nft.claim(ids);
        assertEq(nft.totalValue(), (amount - claimCount) * 100 ether);
        assertEq(nft.totalSupply(), amount - claimCount);
        assertEq(nft.balanceOf(alice), amount - claimCount);
        assertEq(nft.balanceOf(bob), 0);
        _assertAccounting();
        _buy(bob, 100 ether, 1);
        assertEq(nft.ownerOf(amount), bob);
        assertEq(nft.totalValue(), (amount - claimCount + 1) * 100 ether);
        _assertListLength(0);
        _assertAccounting();
    }
}
