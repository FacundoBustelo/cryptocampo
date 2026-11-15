// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {CCNFTBase, CCNFT} from "./CCNFTBase.sol";

contract CCNFTAdminTest is CCNFTBase {
    function testInitialStateAndInterfaces() public {
        CCNFT fresh = new CCNFT();
        assertEq(fresh.name(), "CryptoCampo NFT");
        assertEq(fresh.symbol(), "CCNFT");
        assertEq(fresh.owner(), address(this));
        assertFalse(fresh.canBuy());
        assertFalse(fresh.canTrade());
        assertFalse(fresh.canClaim());
        assertEq(fresh.totalValue(), 0);
        assertEq(fresh.totalSupply(), 0);
        assertEq(address(fresh.fundsToken()), address(0));
        assertEq(fresh.fundsCollector(), address(0));
        assertEq(fresh.feesCollector(), address(0));
        assertTrue(fresh.supportsInterface(0x01ffc9a7)); // ERC165
        assertTrue(fresh.supportsInterface(0x80ac58cd)); // ERC721
        assertTrue(fresh.supportsInterface(0x5b5e139f)); // ERC721Metadata
        assertTrue(fresh.supportsInterface(0x780e9d63)); // ERC721Enumerable
        assertFalse(fresh.supportsInterface(0xffffffff));
    }

    function testAllSettersAndFullProfitRange() public {
        nft.setFundsToken(address(busd));
        nft.setFundsCollector(bob);
        nft.setFeesCollector(alice);
        nft.setProfitToPay(type(uint32).max);
        nft.setMaxValueToRaise(123);
        nft.setMaxBatchCount(type(uint16).max);
        nft.setBuyFee(10_000);
        nft.setTradeFee(10_000);
        nft.addValidValues(7);
        nft.addValidValues(7);
        assertEq(address(nft.fundsToken()), address(busd));
        assertEq(nft.fundsCollector(), bob);
        assertEq(nft.feesCollector(), alice);
        assertEq(nft.profitToPay(), type(uint32).max);
        assertEq(nft.maxValueToRaise(), 123);
        assertEq(nft.maxBatchCount(), type(uint16).max);
        assertEq(nft.buyFee(), 10_000);
        assertEq(nft.tradeFee(), 10_000);
        assertTrue(nft.validValues(7));
        nft.setCanBuy(false);
        nft.setCanTrade(false);
        nft.setCanClaim(false);
        assertFalse(nft.canBuy());
        assertFalse(nft.canTrade());
        assertFalse(nft.canClaim());
        nft.setCanBuy(true);
        nft.setCanTrade(true);
        nft.setCanClaim(true);
        assertTrue(nft.canBuy());
        assertTrue(nft.canTrade());
        assertTrue(nft.canClaim());
        nft.setBuyFee(0);
        nft.setTradeFee(0);
        nft.setProfitToPay(0);
        nft.setMaxValueToRaise(0);
        assertEq(nft.buyFee(), 0);
        assertEq(nft.tradeFee(), 0);
        assertEq(nft.profitToPay(), 0);
        assertEq(nft.maxValueToRaise(), 0);
    }

    function testEverySetterRequiresOwner() public {
        bytes[] memory calls = new bytes[](13);
        calls[0] = abi.encodeCall(nft.setFundsToken, (address(busd)));
        calls[1] = abi.encodeCall(nft.setFundsCollector, (bob));
        calls[2] = abi.encodeCall(nft.setFeesCollector, (bob));
        calls[3] = abi.encodeCall(nft.setProfitToPay, (500));
        calls[4] = abi.encodeCall(nft.setCanBuy, (false));
        calls[5] = abi.encodeCall(nft.setCanTrade, (false));
        calls[6] = abi.encodeCall(nft.setCanClaim, (false));
        calls[7] = abi.encodeCall(nft.setMaxValueToRaise, (1));
        calls[8] = abi.encodeCall(nft.setMaxBatchCount, (1));
        calls[9] = abi.encodeCall(nft.setBuyFee, (0));
        calls[10] = abi.encodeCall(nft.setTradeFee, (0));
        calls[11] = abi.encodeCall(nft.addValidValues, (1));
        calls[12] = abi.encodeCall(nft.setMetadataURI, ("http://127.0.0.1:8000/metadata.json"));
        for (uint256 i; i < calls.length; ++i) {
            vm.prank(alice);
            (bool ok, bytes memory result) = address(nft).call(calls[i]);
            assertFalse(ok);
            assertEq(result, abi.encodeWithSignature("Error(string)", "Ownable: caller is not the owner"));
        }
    }

    function testInvalidSetterInputs() public {
        vm.expectRevert("Zero address");
        nft.setFundsToken(address(0));
        vm.expectRevert("Funds token must be a contract");
        nft.setFundsToken(alice);
        vm.expectRevert("Zero address");
        nft.setFundsCollector(address(0));
        vm.expectRevert("Zero address");
        nft.setFeesCollector(address(0));
        vm.expectRevert("Invalid value");
        nft.addValidValues(0);
        vm.expectRevert("Invalid batch size");
        nft.setMaxBatchCount(0);
        vm.expectRevert("Invalid fee");
        nft.setBuyFee(10_001);
        vm.expectRevert("Invalid fee");
        nft.setTradeFee(type(uint16).max);
    }

    function testDisabledOperations() public {
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        nft.setCanBuy(false);
        nft.setCanTrade(false);
        nft.setCanClaim(false);
        vm.expectRevert("Buying disabled");
        _buy(alice, 100 ether, 1);
        vm.expectRevert("Trading disabled");
        _list(alice, 0, 120 ether);
        vm.expectRevert("Trading disabled");
        _trade(bob, 0);
        vm.expectRevert("Claiming disabled");
        _claim(alice, 0);
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.listTokensOnSale(0), 0);
        _assertAccounting();
    }

    function testBuyRequiresCompleteConfiguration() public {
        CCNFT fresh = new CCNFT();
        fresh.setCanBuy(true);
        fresh.setMaxBatchCount(1);
        fresh.setMaxValueToRaise(100 ether);
        fresh.addValidValues(100 ether);
        vm.expectRevert("Funds token not configured");
        fresh.buy(100 ether, 1);
        fresh.setFundsToken(address(busd));
        vm.expectRevert("Funds collector not configured");
        fresh.buy(100 ether, 1);
        fresh.setFundsCollector(funds);
        vm.expectRevert("Fees collector not configured");
        fresh.buy(100 ether, 1);
        assertEq(fresh.totalSupply(), 0);
        assertEq(fresh.totalValue(), 0);
    }
}
