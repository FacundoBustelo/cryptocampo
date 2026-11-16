// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {DemoBase} from "./DemoBase.sol";

contract Identity is DemoBase {
    function run() external view {
        actors();
    }
}
