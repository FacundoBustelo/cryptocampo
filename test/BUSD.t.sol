// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {BUSD} from "../src/BUSD.sol";

contract BUSDTest is Test {
    BUSD private busd;
    address private deployer = address(0xA11CE);

    function setUp() public {
        vm.prank(deployer);
        busd = new BUSD();
    }

    function testMetadata() public {
        assertEq(busd.name(), "BUSD");
        assertEq(busd.symbol(), "BUSD");
        assertEq(busd.decimals(), 18);
    }

    function testInitialSupplyBelongsToDeployer() public {
        assertEq(busd.totalSupply(), 10_000_000 ether);
        assertEq(busd.balanceOf(deployer), busd.totalSupply());
        assertEq(busd.balanceOf(address(this)), 0);
        assertEq(busd.balanceOf(address(busd)), 0);
    }
}
