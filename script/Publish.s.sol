// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {DemoBase, BUSD, CCNFT} from "./DemoBase.sol";

/// @notice Publica una transacción del plan simulado; el ejecutor reconcilia cada nonce antes de continuar.
contract Publish is DemoBase {
    function run() external {
        Actors memory p = actors();
        require(block.chainid == 11155111, "Demo: public profile required");
        address sender = vm.envAddress("DEMO_APPROVER");
        require(sender == p.admin || sender == p.a || sender == p.b || sender == p.funds, "Demo: invalid sender");
        require(vm.getNonce(sender) == vm.envUint("DEMO_TX_NONCE"), "Demo: nonce changed");
        bytes memory data = vm.envBytes("DEMO_TX_DATA");
        uint256 kind = vm.envUint("DEMO_TX_KIND");
        if (kind == 1 || kind == 2) {
            require(sender == p.admin, "Demo: admin deployment required");
            bytes memory code = kind == 1 ? type(BUSD).creationCode : type(CCNFT).creationCode;
            require(keccak256(data) == keccak256(code), "Demo: creation code changed");
            begin(sender);
            if (kind == 1) new BUSD();
            else new CCNFT();
        } else {
            require(kind == 0, "Demo: invalid transaction kind");
            (BUSD busd, CCNFT nft) = deployed(p);
            address target = vm.envAddress("DEMO_TX_TO");
            require(target == address(busd) || target == address(nft), "Demo: unexpected target");
            begin(sender);
            (bool success,) = target.call(data);
            require(success, "Demo: transaction failed");
        }
        vm.stopBroadcast();
    }
}
