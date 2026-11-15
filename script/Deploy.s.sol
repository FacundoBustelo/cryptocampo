// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {DemoBase, BUSD, CCNFT} from "./DemoBase.sol";

contract Deploy is DemoBase {
    function run() external {
        Actors memory p = actors();
        vm.startBroadcast(p.admin);
        new BUSD();
        new CCNFT();
        vm.stopBroadcast();
    }
}
