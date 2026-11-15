// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {CCNFTBase} from "./CCNFTBase.sol";

contract CCNFTMetadataTest is CCNFTBase {
    // Referencias de prueba: no son publicaciones ni CIDs IPFS.
    string private constant LOCAL_URI = "http://127.0.0.1:8000/metadata.json";
    string private constant UPDATED_URI = "https://metadata.example.invalid/updated.json";

    event MetadataURIUpdated(string metadataURI);

    function testExistingTokensHaveEmptyURIUntilConfigured() public {
        _buy(alice, 100 ether, 2);
        assertEq(nft.tokenURI(0), "");
        assertEq(nft.tokenURI(1), "");
        _list(alice, 0, 120 ether);
        _trade(bob, 0);
        assertEq(nft.tokenURI(0), "");
        _claim(bob, 0);
        _assertAccounting();
    }

    function testOwnerConfiguresURIAndEmitsEvent() public {
        vm.expectEmit(false, false, false, true, address(nft));
        emit MetadataURIUpdated(LOCAL_URI);
        nft.setMetadataURI(LOCAL_URI);
        _buy(alice, 100 ether, 1);
        assertEq(nft.tokenURI(0), LOCAL_URI);
    }

    function testTokenOwnerAndThirdPartyCannotConfigureURI() public {
        _buy(alice, 100 ether, 1);
        vm.expectRevert("Ownable: caller is not the owner");
        vm.prank(alice);
        nft.setMetadataURI(LOCAL_URI);
        vm.expectRevert("Ownable: caller is not the owner");
        vm.prank(bob);
        nft.setMetadataURI(LOCAL_URI);
        assertEq(nft.tokenURI(0), "");
        nft.setMetadataURI(LOCAL_URI);
        vm.expectRevert("Ownable: caller is not the owner");
        vm.prank(bob);
        nft.setMetadataURI(UPDATED_URI);
        assertEq(nft.tokenURI(0), LOCAL_URI);
    }

    function testEmptyURIRejectedBeforeAndAfterConfiguration() public {
        _buy(alice, 100 ether, 1);
        vm.expectRevert("Empty metadata URI");
        nft.setMetadataURI("");
        assertEq(nft.tokenURI(0), "");
        nft.setMetadataURI(LOCAL_URI);
        vm.expectRevert("Empty metadata URI");
        nft.setMetadataURI("");
        assertEq(nft.tokenURI(0), LOCAL_URI);
    }

    function testUpdateAppliesToAllExistingAndFutureTokens() public {
        _buy(alice, 100 ether, 1);
        _buy(bob, 500 ether, 1);
        nft.setMetadataURI(LOCAL_URI);
        assertEq(nft.tokenURI(0), LOCAL_URI);
        assertEq(nft.tokenURI(1), LOCAL_URI);
        vm.expectEmit(false, false, false, true, address(nft));
        emit MetadataURIUpdated(UPDATED_URI);
        nft.setMetadataURI(UPDATED_URI);
        _buy(alice, 100 ether, 1);
        for (uint256 i; i < 3; ++i) assertEq(nft.tokenURI(i), UPDATED_URI);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.values(1), 500 ether);
        assertEq(nft.totalValue(), 700 ether);
        _assertAccounting();
    }

    function testResalePreservesSharedURIAndNominal() public {
        nft.setMetadataURI(LOCAL_URI);
        _buy(alice, 100 ether, 2);
        _list(alice, 0, 120 ether);
        _trade(bob, 0);
        assertEq(nft.ownerOf(0), bob);
        assertEq(nft.tokenURI(0), LOCAL_URI);
        assertEq(nft.tokenURI(1), LOCAL_URI);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.totalValue(), 200 ether);
        _assertAccounting();
    }

    function testNonexistentAndBurnedTokensRevertWithOrWithoutURI() public {
        vm.expectRevert("Token does not exist");
        nft.tokenURI(0);
        _buy(alice, 100 ether, 2);
        _claim(alice, 0);
        vm.expectRevert("Token does not exist");
        nft.tokenURI(0);
        nft.setMetadataURI(LOCAL_URI);
        vm.expectRevert("Token does not exist");
        nft.tokenURI(0);
        vm.expectRevert("Token does not exist");
        nft.tokenURI(999);
        assertEq(nft.tokenURI(1), LOCAL_URI);
        busd.transfer(funds, 10 ether);
        _claim(alice, 1);
        vm.expectRevert("Token does not exist");
        nft.tokenURI(1);
        _assertAccounting();
    }

    function testMetadataUpdateDoesNotChangeEconomicStateOrEnableOperations() public {
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        nft.setCanBuy(false);
        nft.setCanTrade(false);
        nft.setCanClaim(false);
        uint256 aliceBalance = busd.balanceOf(alice);
        uint256 fundsBalance = busd.balanceOf(funds);
        uint256 feesBalance = busd.balanceOf(fees);
        nft.setMetadataURI(LOCAL_URI);
        assertEq(nft.tokenURI(0), LOCAL_URI);
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.totalValue(), 100 ether);
        assertEq(nft.totalSupply(), 1);
        (bool onSale, uint256 price) = nft.tokensOnSale(0);
        assertTrue(onSale);
        assertEq(price, 120 ether);
        assertEq(nft.listTokensOnSale(0), 0);
        assertEq(busd.balanceOf(alice), aliceBalance);
        assertEq(busd.balanceOf(funds), fundsBalance);
        assertEq(busd.balanceOf(fees), feesBalance);
        vm.expectRevert("Buying disabled");
        _buy(alice, 100 ether, 1);
        vm.expectRevert("Trading disabled");
        _trade(bob, 0);
        vm.expectRevert("Claiming disabled");
        _claim(alice, 0);
        _assertAccounting();
    }
}
