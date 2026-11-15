// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC721Receiver} from "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {CCNFT} from "../../src/CCNFT.sol";

/// @dev Permite fallar un cobro especifico o intentar reentrar desde el ERC20.
contract AdversarialToken is ERC20 {
    uint256 public calls;
    uint256 public failAt;
    CCNFT public target;
    bytes public callback;
    bool public callbackBlocked;

    constructor() ERC20("Test funds", "TEST") {
        _mint(msg.sender, 1_000_000 ether);
    }

    function setFailure(uint256 callNumber) external {
        failAt = callNumber;
    }

    function setCallback(CCNFT nft, bytes calldata data) external {
        target = nft;
        callback = data;
    }

    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        ++calls;
        if (calls == failAt) return false;
        if (address(target) != address(0)) {
            (bool ok, bytes memory reason) = address(target).call(callback);
            require(!ok, "Reentry succeeded");
            require(
                keccak256(reason) == keccak256(abi.encodeWithSignature("Error(string)", "ReentrancyGuard: reentrant call")),
                "Unexpected callback error"
            );
            callbackBlocked = true;
        }
        return super.transferFrom(from, to, amount);
    }
}

contract AdversarialReceiver is IERC721Receiver {
    CCNFT public immutable nft;
    bool public reject;
    bool public attack;
    bool public propagateFailure;
    uint256 public received;
    uint256 public blockedCalls;
    mapping(uint256 => bool) public seen;

    constructor(CCNFT target, IERC20 token) {
        nft = target;
        token.approve(address(target), type(uint256).max);
    }

    function configure(bool rejectNFT, bool attemptReentry, bool propagate) external {
        reject = rejectNFT;
        attack = attemptReentry;
        propagateFailure = propagate;
    }

    function execute(bytes calldata data) external {
        (bool ok, bytes memory result) = address(nft).call(data);
        if (!ok) {
            assembly {
                revert(add(result, 32), mload(result))
            }
        }
    }

    function onERC721Received(address, address, uint256 tokenId, bytes calldata) external override returns (bytes4) {
        require(msg.sender == address(nft), "Unexpected NFT");
        require(nft.ownerOf(tokenId) == address(this), "Owner not prepared");
        require(nft.values(tokenId) > 0, "Value not prepared");
        (bool onSale, uint256 price) = nft.tokensOnSale(tokenId);
        require(!onSale && price == 0, "Sale not cleared");
        require(!seen[tokenId], "Duplicate ID");
        seen[tokenId] = true;
        ++received;
        if (reject) return bytes4(0);
        if (attack) {
            uint256[] memory ids = new uint256[](1);
            ids[0] = tokenId;
            _attempt(abi.encodeCall(nft.buy, (100 ether, 1)));
            _attempt(abi.encodeCall(nft.trade, (tokenId)));
            _attempt(abi.encodeCall(nft.claim, (ids)));
            _attempt(abi.encodeCall(nft.putOnSale, (tokenId, 1)));
        }
        return IERC721Receiver.onERC721Received.selector;
    }

    function _attempt(bytes memory data) private {
        (bool ok, bytes memory result) = address(nft).call(data);
        if (propagateFailure && !ok) {
            assembly {
                revert(add(result, 32), mload(result))
            }
        }
        require(!ok, "Reentry succeeded");
        require(
            keccak256(result) == keccak256(abi.encodeWithSignature("Error(string)", "ReentrancyGuard: reentrant call")),
            "Unexpected callback error"
        );
        ++blockedCalls;
    }
}
