// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {DemoBase, BUSD, CCNFT} from "./DemoBase.sol";

contract Configure is DemoBase {
    function run() external {
        Actors memory p = actors();
        (BUSD busd, CCNFT nft) = deployed(p);
        fresh(nft);
        begin(p.admin);
        nft.setFundsToken(address(busd));
        nft.setFundsCollector(p.funds);
        nft.setFeesCollector(p.fees);
        nft.addValidValues(NOMINAL);
        nft.addValidValues(OTHER_NOMINAL);
        nft.setBuyFee(BUY_FEE);
        nft.setTradeFee(TRADE_FEE);
        nft.setProfitToPay(PROFIT);
        nft.setMaxBatchCount(BATCH);
        nft.setMaxValueToRaise(LIMIT);
        nft.setMetadataURI(URI);
        vm.stopBroadcast();
    }
}
