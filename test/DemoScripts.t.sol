// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {DemoBase, BUSD, CCNFT} from "../script/DemoBase.sol";
import {Deploy} from "../script/Deploy.s.sol";
import {Configure} from "../script/Configure.s.sol";
import {Fund, Approve, Enable} from "../script/Prepare.s.sol";
import {Buy, List, Trade, Claim} from "../script/Operations.s.sol";

contract DemoGuard is DemoBase {
    function validate() external view {
        Actors memory p = actors();
        deployed(p);
    }
}

/// @notice vm.setEnv es global al proceso: una sola prueba agrupa las guardas para evitar carreras.
/// Solo guardas y preparación de scripts; las operaciones se prueban en sus suites existentes.
contract DemoScriptsTest is Test {
    address internal constant ADMIN = address(0xA0);
    address internal constant A = address(0xA1);
    address internal constant B = address(0xA2);
    address internal constant FUNDS = address(0xA3);
    address internal constant FEES = address(0xA4);
    BUSD internal busd;
    CCNFT internal nft;
    DemoGuard internal guard;
    Configure internal configure;
    Fund internal fund;
    Approve internal approve;
    Enable internal enable;
    Buy internal buy;
    List internal listing;
    Trade internal trade;
    Claim internal claim;

    function testScriptsConfigurationAndRejections() public {
        uint256 snapshot = vm.snapshotState();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsWrongChainBeforeDeploy();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsZeroActor();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsContractActor();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsDuplicateActors();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsIncorrectBUSDIncludingOtherContract();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsIncorrectCCNFTIncludingOtherContract();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptRejectsIncorrectOwner();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkConfigureUsesSharedParametersAndKeepsOperationsDisabled();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkConfigureRejectsAlreadyEnabledCollection();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkPreparationRejectsUnconfiguredContracts();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkEnableRequiresFundingAndAllExactApprovals();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkApproveRejectsOtherAccountAndMissingFunding();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkFundAndApproveRejectRepeatedExecution();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkOperationsRejectDisabledFlagsAndMissingPreviousStages();
        assertTrue(vm.revertToState(snapshot));
        resetEnvironment();
        checkScriptSequencePreservesSecondNFTAndReserve();
    }

    function setUp() public {
        vm.startPrank(ADMIN);
        busd = new BUSD();
        nft = new CCNFT();
        vm.stopPrank();
        guard = new DemoGuard();
        configure = new Configure();
        fund = new Fund();
        approve = new Approve();
        enable = new Enable();
        buy = new Buy();
        listing = new List();
        trade = new Trade();
        claim = new Claim();
        resetEnvironment();
    }

    function resetEnvironment() internal {
        vm.chainId(31337);
        vm.setEnv("DEMO_ADMIN", vm.toString(ADMIN));
        vm.setEnv("DEMO_A", vm.toString(A));
        vm.setEnv("DEMO_B", vm.toString(B));
        vm.setEnv("DEMO_FUNDS", vm.toString(FUNDS));
        vm.setEnv("DEMO_FEES", vm.toString(FEES));
        vm.setEnv("DEMO_BUSD", vm.toString(address(busd)));
        vm.setEnv("DEMO_CCNFT", vm.toString(address(nft)));
        vm.setEnv("DEMO_APPROVER", vm.toString(A));
    }

    function checkScriptSequencePreservesSecondNFTAndReserve() internal {
        configure.run();
        fund.run();
        approve.run();
        vm.setEnv("DEMO_APPROVER", vm.toString(B));
        approve.run();
        vm.setEnv("DEMO_APPROVER", vm.toString(FUNDS));
        approve.run();
        enable.run();
        buy.run();
        uint256 keptId = nft.tokenOfOwnerByIndex(A, 1);
        listing.run();
        trade.run();
        claim.run();
        assertEq(nft.tokenOfOwnerByIndex(A, 0), keptId);
        assertEq(nft.tokenURI(keptId), configure.URI());
        assertEq(busd.balanceOf(FUNDS), configure.CLAIM_PAYMENT());
    }

    function checkScriptRejectsWrongChainBeforeDeploy() internal {
        Deploy deploy = new Deploy();
        vm.chainId(1);
        vm.expectRevert("Demo: chain must be 31337");
        deploy.run();
    }

    function checkScriptRejectsZeroActor() internal {
        vm.setEnv("DEMO_A", vm.toString(address(0)));
        vm.expectRevert("Demo: invalid actor");
        guard.validate();
    }

    function checkScriptRejectsContractActor() internal {
        vm.setEnv("DEMO_A", vm.toString(address(busd)));
        vm.expectRevert("Demo: invalid actor");
        guard.validate();
    }

    function checkScriptRejectsDuplicateActors() internal {
        vm.setEnv("DEMO_FEES", vm.toString(FUNDS));
        vm.expectRevert("Demo: duplicate actors");
        guard.validate();
    }

    function checkScriptRejectsIncorrectBUSDIncludingOtherContract() internal {
        vm.setEnv("DEMO_BUSD", vm.toString(A));
        vm.expectRevert("Demo: incorrect BUSD code");
        guard.validate();
        vm.setEnv("DEMO_BUSD", vm.toString(address(nft)));
        vm.expectRevert("Demo: incorrect BUSD code");
        guard.validate();
    }

    function checkScriptRejectsIncorrectCCNFTIncludingOtherContract() internal {
        vm.setEnv("DEMO_CCNFT", vm.toString(B));
        vm.expectRevert("Demo: incorrect CCNFT code");
        guard.validate();
        vm.setEnv("DEMO_CCNFT", vm.toString(address(busd)));
        vm.expectRevert("Demo: incorrect CCNFT code");
        guard.validate();
    }

    function checkScriptRejectsIncorrectOwner() internal {
        vm.prank(ADMIN);
        nft.transferOwnership(A);
        vm.expectRevert("Demo: incorrect owner");
        guard.validate();
    }

    function checkConfigureUsesSharedParametersAndKeepsOperationsDisabled() internal {
        configure.run();
        assertEq(address(nft.fundsToken()), address(busd));
        assertEq(nft.fundsCollector(), FUNDS);
        assertEq(nft.feesCollector(), FEES);
        assertTrue(nft.validValues(configure.NOMINAL()));
        assertTrue(nft.validValues(configure.OTHER_NOMINAL()));
        assertEq(nft.buyFee(), configure.BUY_FEE());
        assertEq(nft.tradeFee(), configure.TRADE_FEE());
        assertEq(nft.profitToPay(), configure.PROFIT());
        assertEq(nft.maxBatchCount(), configure.BATCH());
        assertEq(nft.maxValueToRaise(), configure.LIMIT());
        assertFalse(nft.canBuy() || nft.canTrade() || nft.canClaim());
    }

    function checkConfigureRejectsAlreadyEnabledCollection() internal {
        vm.prank(ADMIN);
        nft.setCanBuy(true);
        vm.expectRevert("Demo: operations already enabled");
        configure.run();
    }

    function checkPreparationRejectsUnconfiguredContracts() internal {
        vm.expectRevert("Demo: incorrect payment configuration");
        fund.run();
        vm.expectRevert("Demo: incorrect payment configuration");
        approve.run();
        vm.expectRevert("Demo: incorrect payment configuration");
        enable.run();
    }

    function checkEnableRequiresFundingAndAllExactApprovals() internal {
        configure.run();
        vm.expectRevert("Demo: funding prerequisite");
        enable.run();
        fund.run();
        vm.expectRevert("Demo: approval prerequisite");
        enable.run();
        approve.run();
        vm.setEnv("DEMO_APPROVER", vm.toString(B));
        approve.run();
        vm.expectRevert("Demo: approval prerequisite");
        enable.run();
        vm.setEnv("DEMO_APPROVER", vm.toString(FUNDS));
        approve.run();
        enable.run();
        assertTrue(nft.canBuy() && nft.canTrade() && nft.canClaim());
        assertEq(busd.allowance(A, address(nft)), configure.BUY_PAYMENT());
        assertEq(busd.allowance(B, address(nft)), configure.TRADE_PAYMENT());
        assertEq(busd.allowance(FUNDS, address(nft)), configure.CLAIM_PAYMENT());
    }

    function checkApproveRejectsOtherAccountAndMissingFunding() internal {
        configure.run();
        vm.setEnv("DEMO_APPROVER", vm.toString(ADMIN));
        vm.expectRevert("Demo: invalid approver");
        approve.run();
        vm.setEnv("DEMO_APPROVER", vm.toString(A));
        vm.expectRevert("Demo: funding prerequisite");
        approve.run();
    }

    function checkFundAndApproveRejectRepeatedExecution() internal {
        configure.run();
        fund.run();
        vm.expectRevert("Demo: funded");
        fund.run();
        approve.run();
        vm.expectRevert("Demo: already approved");
        approve.run();
    }

    function checkOperationsRejectDisabledFlagsAndMissingPreviousStages() internal {
        configure.run();
        vm.expectRevert("Demo: operations disabled");
        buy.run();
        vm.startPrank(ADMIN);
        nft.setCanBuy(true);
        nft.setCanTrade(true);
        nft.setCanClaim(true);
        vm.stopPrank();
        vm.expectRevert("Demo: buy approval");
        buy.run();
        vm.expectRevert("Demo: buy prerequisite");
        listing.run();
        vm.expectRevert("Demo: seller prerequisite");
        trade.run();
        vm.expectRevert("Demo: trade prerequisite");
        claim.run();
    }
}
