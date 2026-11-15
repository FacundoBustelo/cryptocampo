// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721Enumerable} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Counters} from "@openzeppelin/contracts/utils/Counters.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// @notice Certificados de demostracion. Los importes usan las unidades minimas del ERC20.
contract CCNFT is ERC721Enumerable, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;

    event Buy(address indexed buyer, uint256 indexed tokenId, uint256 value);
    event BuyPayment(address indexed buyer, uint256 principal, uint256 fee);
    event PutOnSale(address indexed seller, uint256 indexed tokenId, uint256 price);
    event Trade(address indexed buyer, address indexed seller, uint256 indexed tokenId, uint256 price, uint256 fee);
    event Claim(address indexed claimer, uint256 indexed tokenId, uint256 value);
    event ClaimPayment(address indexed claimer, uint256 principal, uint256 profit);
    event MetadataURIUpdated(string metadataURI);

    struct TokenSale {
        bool onSale;
        uint256 price;
    }

    Counters.Counter private tokenIdTracker;
    string private metadataURI;
    mapping(uint256 => uint256) public values;
    mapping(uint256 => bool) public validValues;
    mapping(uint256 => TokenSale) public tokensOnSale;
    uint256[] public listTokensOnSale;

    address public fundsCollector;
    address public feesCollector;
    bool public canBuy;
    bool public canClaim;
    bool public canTrade;
    uint256 public totalValue;
    uint256 public maxValueToRaise;
    uint16 public buyFee;
    uint16 public tradeFee;
    uint16 public maxBatchCount;
    uint32 public profitToPay;
    IERC20 public fundsToken;

    constructor() ERC721("CryptoCampo NFT", "CCNFT") {}

    /// @notice Ficha compartida por todos los certificados vigentes.
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_exists(tokenId), "Token does not exist");
        return metadataURI;
    }

    function setMetadataURI(string calldata uri) external onlyOwner {
        require(bytes(uri).length > 0, "Empty metadata URI");
        metadataURI = uri;
        emit MetadataURIUpdated(uri);
    }

    function buy(uint256 value, uint256 amount) external nonReentrant {
        require(canBuy, "Buying disabled");
        require(amount > 0 && amount <= maxBatchCount, "Invalid batch size");
        require(value > 0 && validValues[value], "Invalid value");
        require(address(fundsToken) != address(0), "Funds token not configured");
        require(fundsCollector != address(0), "Funds collector not configured");
        require(feesCollector != address(0), "Fees collector not configured");

        uint256 principal = value * amount;
        uint256 fee = principal * buyFee / 10_000;
        require(totalValue + principal <= maxValueToRaise, "Max value exceeded");
        totalValue += principal;

        for (uint256 i; i < amount; ++i) {
            uint256 tokenId = tokenIdTracker.current();
            // Reservar el ID y su nominal antes de llamar al receptor ERC721.
            tokenIdTracker.increment();
            values[tokenId] = value;
            _safeMint(_msgSender(), tokenId);
            emit Buy(_msgSender(), tokenId, value);
        }

        require(fundsToken.transferFrom(_msgSender(), fundsCollector, principal), "Cannot send funds tokens");
        if (fee > 0) {
            require(fundsToken.transferFrom(_msgSender(), feesCollector, fee), "Cannot send fees tokens");
        }
        emit BuyPayment(_msgSender(), principal, fee);
    }

    function putOnSale(uint256 tokenId, uint256 price) external nonReentrant {
        require(canTrade, "Trading disabled");
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == _msgSender(), "Only owner can sell");
        require(price > 0, "Invalid price");

        tokensOnSale[tokenId] = TokenSale(true, price);
        addToArray(listTokensOnSale, tokenId);
        emit PutOnSale(_msgSender(), tokenId, price);
    }

    function trade(uint256 tokenId) external nonReentrant {
        require(canTrade, "Trading disabled");
        require(_exists(tokenId), "Token does not exist");
        address seller = ownerOf(tokenId);
        require(seller != _msgSender(), "Buyer is the Seller");
        TokenSale memory sale = tokensOnSale[tokenId];
        require(sale.onSale, "Token not On Sale");
        require(address(fundsToken) != address(0), "Funds token not configured");
        require(feesCollector != address(0), "Fees collector not configured");

        uint256 fee = sale.price * tradeFee / 10_000;
        delete tokensOnSale[tokenId];
        removeFromArray(listTokensOnSale, tokenId);
        // El callback ve al nuevo propietario y una publicacion ya eliminada.
        _safeTransfer(seller, _msgSender(), tokenId, "");

        require(fundsToken.transferFrom(_msgSender(), seller, sale.price), "Cannot send funds tokens");
        if (fee > 0) {
            require(fundsToken.transferFrom(_msgSender(), feesCollector, fee), "Cannot send fees tokens");
        }
        emit Trade(_msgSender(), seller, tokenId, sale.price, fee);
    }

    function claim(uint256[] calldata tokenIds) external nonReentrant {
        require(canClaim, "Claiming disabled");
        require(tokenIds.length > 0 && tokenIds.length <= maxBatchCount, "Invalid batch size");
        require(address(fundsToken) != address(0), "Funds token not configured");
        require(fundsCollector != address(0), "Funds collector not configured");

        uint256 principal;
        for (uint256 i; i < tokenIds.length; ++i) {
            uint256 tokenId = tokenIds[i];
            // Quemar dentro del bucle tambien rechaza IDs repetidos de forma atomica.
            require(_exists(tokenId), "Token does not exist");
            require(ownerOf(tokenId) == _msgSender(), "Only owner can Claim");
            uint256 value = values[tokenId];
            principal += value;
            delete values[tokenId];
            delete tokensOnSale[tokenId];
            removeFromArray(listTokensOnSale, tokenId);
            _burn(tokenId);
            emit Claim(_msgSender(), tokenId, value);
        }
        totalValue -= principal;
        uint256 profit = principal * profitToPay / 10_000;
        require(fundsToken.transferFrom(fundsCollector, _msgSender(), principal + profit), "Cannot send funds tokens");
        emit ClaimPayment(_msgSender(), principal, profit);
    }

    function setFundsToken(address token) external onlyOwner {
        require(token != address(0), "Zero address");
        require(token.code.length > 0, "Funds token must be a contract");
        fundsToken = IERC20(token);
    }

    function setFundsCollector(address _address) external onlyOwner {
        require(_address != address(0), "Zero address");
        fundsCollector = _address;
    }

    function setFeesCollector(address _address) external onlyOwner {
        require(_address != address(0), "Zero address");
        feesCollector = _address;
    }

    function setProfitToPay(uint32 _profitToPay) external onlyOwner {
        profitToPay = _profitToPay;
    }

    function setCanBuy(bool _canBuy) external onlyOwner {
        canBuy = _canBuy;
    }

    function setCanClaim(bool _canClaim) external onlyOwner {
        canClaim = _canClaim;
    }

    function setCanTrade(bool _canTrade) external onlyOwner {
        canTrade = _canTrade;
    }

    function setMaxValueToRaise(uint256 _maxValueToRaise) external onlyOwner {
        maxValueToRaise = _maxValueToRaise;
    }

    function addValidValues(uint256 value) external onlyOwner {
        require(value > 0, "Invalid value");
        validValues[value] = true;
    }

    function setMaxBatchCount(uint16 _maxBatchCount) external onlyOwner {
        require(_maxBatchCount > 0, "Invalid batch size");
        maxBatchCount = _maxBatchCount;
    }

    function setBuyFee(uint16 _buyFee) external onlyOwner {
        require(_buyFee <= 10_000, "Invalid fee");
        buyFee = _buyFee;
    }

    function setTradeFee(uint16 _tradeFee) external onlyOwner {
        require(_tradeFee <= 10_000, "Invalid fee");
        tradeFee = _tradeFee;
    }

    // Se conserva la busqueda lineal propuesta por la cursada: costo O(n).
    function addToArray(uint256[] storage list, uint256 value) private {
        if (find(list, value) == list.length) list.push(value);
    }

    function removeFromArray(uint256[] storage list, uint256 value) private {
        uint256 index = find(list, value);
        if (index < list.length) {
            list[index] = list[list.length - 1];
            list.pop();
        }
    }

    function find(uint256[] storage list, uint256 value) private view returns (uint256) {
        for (uint256 i; i < list.length; ++i) {
            if (list[i] == value) return i;
        }
        return list.length;
    }

    function transferFrom(address, address, uint256) public pure override(ERC721, IERC721) {
        revert("Not Allowed");
    }

    function safeTransferFrom(address, address, uint256) public pure override(ERC721, IERC721) {
        revert("Not Allowed");
    }

    function safeTransferFrom(address, address, uint256, bytes memory) public pure override(ERC721, IERC721) {
        revert("Not Allowed");
    }

    function _beforeTokenTransfer(address from, address to, uint256 tokenId) internal override(ERC721Enumerable) {
        super._beforeTokenTransfer(from, to, tokenId);
    }
}
