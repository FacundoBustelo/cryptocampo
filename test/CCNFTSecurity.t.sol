// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {CCNFTBase} from "./CCNFTBase.sol";
import {AdversarialToken, AdversarialReceiver} from "./mocks/Adversaries.sol";

contract CCNFTSecurityTest is CCNFTBase {
    function testBuyInsufficientAllowanceOrBalanceRevertsAllMints() public {
        vm.prank(alice);
        assertTrue(busd.approve(address(nft), 199 ether));
        vm.expectRevert("ERC20: insufficient allowance");
        _buy(alice, 100 ether, 2);
        assertEq(busd.balanceOf(alice), 100_000 ether);
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.values(0), 0);
        assertEq(nft.values(1), 0);
        uint256 excess = busd.balanceOf(alice) - 199 ether;
        vm.startPrank(alice);
        assertTrue(busd.approve(address(nft), type(uint256).max));
        assertTrue(busd.transfer(address(this), excess));
        vm.stopPrank();
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        _buy(alice, 100 ether, 2);
        assertEq(busd.balanceOf(alice), 199 ether);
        assertEq(busd.balanceOf(funds), 0);
        assertEq(busd.balanceOf(fees), 0);
        assertEq(nft.totalSupply(), 0);
        _assertAccounting();
    }

    function testBuySecondChargeAllowanceFailureRollsBackPrincipalAndIds() public {
        vm.prank(alice);
        assertTrue(busd.approve(address(nft), 200 ether));
        vm.expectRevert("ERC20: insufficient allowance");
        _buy(alice, 100 ether, 2);
        assertEq(busd.balanceOf(funds), 0);
        assertEq(busd.balanceOf(fees), 0);
        assertEq(busd.allowance(alice, address(nft)), 200 ether);
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.values(0), 0);
        assertEq(nft.values(1), 0);
        vm.prank(alice);
        assertTrue(busd.approve(address(nft), 204 ether));
        _buy(alice, 100 ether, 2);
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.ownerOf(1), alice);
        _assertAccounting();
    }

    function testBuySecondChargeBalanceFailureRollsBackPrincipal() public {
        uint256 excess = busd.balanceOf(alice) - 200 ether;
        vm.prank(alice);
        assertTrue(busd.transfer(address(this), excess));
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        _buy(alice, 100 ether, 2);
        assertEq(busd.balanceOf(alice), 200 ether);
        assertEq(busd.balanceOf(funds), 0);
        assertEq(busd.balanceOf(fees), 0);
        assertEq(nft.totalSupply(), 0);
        _assertAccounting();
    }

    function testTradeSecondChargeAllowanceFailureRestoresOwnerAndListing() public {
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        vm.prank(bob);
        assertTrue(busd.approve(address(nft), 120 ether));
        vm.expectRevert("ERC20: insufficient allowance");
        _trade(bob, 0);
        _assertUnchangedTrade();
        assertEq(busd.allowance(bob, address(nft)), 120 ether);
        assertEq(busd.balanceOf(bob), 100_000 ether);
        assertEq(busd.balanceOf(alice), 99_898 ether);
        assertEq(busd.balanceOf(fees), 2 ether);
    }

    function testTradeInsufficientFundsAndSecondChargeBalanceFailure() public {
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        vm.prank(bob);
        assertTrue(busd.approve(address(nft), 119 ether));
        vm.expectRevert("ERC20: insufficient allowance");
        _trade(bob, 0);
        _assertUnchangedTrade();
        uint256 excess = busd.balanceOf(bob) - 119 ether;
        vm.startPrank(bob);
        assertTrue(busd.approve(address(nft), type(uint256).max));
        assertTrue(busd.transfer(address(this), excess));
        vm.stopPrank();
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        _trade(bob, 0);
        _assertUnchangedTrade();
        assertTrue(busd.transfer(bob, 1 ether));
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        _trade(bob, 0);
        assertEq(busd.balanceOf(bob), 120 ether);
        assertEq(busd.balanceOf(alice), 99_898 ether);
        _assertUnchangedTrade();
    }

    function testClaimInsufficientCollectorBalanceOrAllowanceRestoresBurns() public {
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        _claim(alice, 0);
        _assertUnchangedTrade();
        assertTrue(busd.transfer(funds, 5 ether));
        vm.prank(funds);
        assertTrue(busd.approve(address(nft), 104 ether));
        vm.expectRevert("ERC20: insufficient allowance");
        _claim(alice, 0);
        _assertUnchangedTrade();
        assertEq(busd.balanceOf(funds), 105 ether);
        assertEq(busd.allowance(funds, address(nft)), 104 ether);
        assertEq(busd.balanceOf(alice), 99_898 ether);
    }

    function testFalseERC20OnBothBuyChargesAndClaim() public {
        AdversarialToken token = _useAdversarialToken();
        token.setFailure(1);
        vm.expectRevert("Cannot send funds tokens");
        _buy(alice, 100 ether, 1);
        assertEq(nft.totalSupply(), 0);
        token.setFailure(2);
        vm.expectRevert("Cannot send fees tokens");
        _buy(alice, 100 ether, 1);
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.totalValue(), 0);
        assertEq(nft.values(0), 0);
        assertEq(token.balanceOf(funds), 0);
        assertEq(token.balanceOf(fees), 0);
        assertEq(token.balanceOf(alice), 1_000 ether);
        assertEq(token.calls(), 0);
        token.setFailure(0);
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        assertTrue(token.transfer(funds, 5 ether));
        token.setFailure(3);
        vm.expectRevert("Cannot send funds tokens");
        _claim(alice, 0);
        _assertUnchangedTrade();
        assertEq(token.balanceOf(funds), 105 ether);
        assertEq(token.balanceOf(alice), 898 ether);
        assertEq(token.calls(), 2);
    }

    function testFalseERC20OnBothTradeCharges() public {
        AdversarialToken token = _useAdversarialToken();
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        token.setFailure(3);
        vm.expectRevert("Cannot send funds tokens");
        _trade(bob, 0);
        _assertUnchangedTrade();
        token.setFailure(4);
        vm.expectRevert("Cannot send fees tokens");
        _trade(bob, 0);
        _assertUnchangedTrade();
        assertEq(token.balanceOf(alice), 898 ether);
        assertEq(token.balanceOf(bob), 1_000 ether);
        assertEq(token.balanceOf(fees), 2 ether);
        assertEq(token.calls(), 2);
    }

    function testERC20CallbacksCannotReenterAnyOperation() public {
        AdversarialToken token = _useAdversarialToken();
        bytes[] memory callbacks = new bytes[](4);
        callbacks[0] = abi.encodeCall(nft.buy, (100 ether, 1));
        callbacks[1] = abi.encodeCall(nft.trade, (0));
        callbacks[2] = abi.encodeCall(nft.claim, (_ids(0)));
        callbacks[3] = abi.encodeCall(nft.putOnSale, (0, 1));
        assertTrue(token.transfer(funds, 100 ether));
        for (uint256 i; i < callbacks.length; ++i) {
            token.setCallback(nft, callbacks[i]);
            _buy(alice, 100 ether, 1);
            assertTrue(token.callbackBlocked());
            _list(alice, i, 120 ether);
            _trade(bob, i);
            _claim(bob, i);
            assertEq(nft.totalSupply(), 0);
            assertEq(nft.totalValue(), 0);
            _assertNoSale(i);
            _assertListLength(0);
        }
    }

    function testRejectingReceiverRollsBackMintAndTrade() public {
        AdversarialReceiver receiver = new AdversarialReceiver(nft, busd);
        assertTrue(busd.transfer(address(receiver), 1_000 ether));
        receiver.configure(true, false, false);
        vm.expectRevert("ERC721: transfer to non ERC721Receiver implementer");
        receiver.execute(abi.encodeCall(nft.buy, (100 ether, 2)));
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.totalValue(), 0);
        assertEq(nft.values(0), 0);
        assertEq(receiver.received(), 0);
        assertEq(busd.balanceOf(address(receiver)), 1_000 ether);
        assertEq(busd.balanceOf(funds), 0);
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        vm.expectRevert("ERC721: transfer to non ERC721Receiver implementer");
        receiver.execute(abi.encodeCall(nft.trade, (0)));
        _assertUnchangedTrade();
        assertEq(busd.balanceOf(address(receiver)), 1_000 ether);
        assertEq(busd.balanceOf(alice), 99_898 ether);
        assertEq(busd.balanceOf(fees), 2 ether);
    }

    function testReceiverCallbacksCannotReenterOrChangeListings() public {
        AdversarialReceiver receiver = new AdversarialReceiver(nft, busd);
        assertTrue(busd.transfer(address(receiver), 1_000 ether));
        receiver.configure(false, true, false);
        receiver.execute(abi.encodeCall(nft.buy, (100 ether, 2)));
        assertEq(receiver.received(), 2);
        assertEq(receiver.blockedCalls(), 8);
        assertEq(nft.ownerOf(0), address(receiver));
        assertEq(nft.ownerOf(1), address(receiver));
        _assertListLength(0);
        _buy(alice, 100 ether, 1);
        _list(alice, 2, 120 ether);
        receiver.execute(abi.encodeCall(nft.trade, (2)));
        assertEq(receiver.received(), 3);
        assertEq(receiver.blockedCalls(), 12);
        assertEq(nft.ownerOf(2), address(receiver));
        _assertNoSale(2);
        _assertListLength(0);
        assertEq(nft.totalValue(), 300 ether);
        _assertAccounting();
    }

    function testPropagatedReentryFailureRollsBackOuterOperation() public {
        AdversarialReceiver receiver = new AdversarialReceiver(nft, busd);
        assertTrue(busd.transfer(address(receiver), 1_000 ether));
        receiver.configure(false, true, true);
        vm.expectRevert("ReentrancyGuard: reentrant call");
        receiver.execute(abi.encodeCall(nft.buy, (100 ether, 2)));
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.values(0), 0);
        assertEq(busd.balanceOf(funds), 0);
        _buy(alice, 100 ether, 1);
        _list(alice, 0, 120 ether);
        vm.expectRevert("ReentrancyGuard: reentrant call");
        receiver.execute(abi.encodeCall(nft.trade, (0)));
        _assertUnchangedTrade();
        assertEq(busd.balanceOf(address(receiver)), 1_000 ether);
    }

    function _useAdversarialToken() internal returns (AdversarialToken token) {
        token = new AdversarialToken();
        nft.setFundsToken(address(token));
        assertTrue(token.transfer(alice, 1_000 ether));
        assertTrue(token.transfer(bob, 1_000 ether));
        vm.prank(alice);
        assertTrue(token.approve(address(nft), type(uint256).max));
        vm.prank(bob);
        assertTrue(token.approve(address(nft), type(uint256).max));
        vm.prank(funds);
        assertTrue(token.approve(address(nft), type(uint256).max));
    }

    function _assertUnchangedTrade() internal view {
        assertEq(nft.ownerOf(0), alice);
        assertEq(nft.values(0), 100 ether);
        assertEq(nft.totalValue(), 100 ether);
        assertEq(nft.totalSupply(), 1);
        assertEq(nft.balanceOf(alice), 1);
        assertEq(nft.balanceOf(bob), 0);
        (bool onSale, uint256 price) = nft.tokensOnSale(0);
        assertTrue(onSale);
        assertEq(price, 120 ether);
        _assertListLength(1);
        assertEq(nft.listTokensOnSale(0), 0);
        _assertAccounting();
    }
}
