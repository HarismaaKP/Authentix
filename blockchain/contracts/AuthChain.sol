// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title AuthChain
/// @notice Stores an immutable identity record (product ID -> image hash)
///         for each manufacturer-registered product, used to detect
///         counterfeits when the app later compares a scanned image
///         against the registered original.
contract AuthChain {
    struct Product {
        string imageHash;
        address manufacturer;
        uint256 timestamp;
        bool exists;
    }

    mapping(string => Product) private products;
    string[] private productIds;

    event ProductRegistered(string indexed productId, address indexed manufacturer, string imageHash, uint256 timestamp);

    modifier notAlreadyRegistered(string memory productId) {
        require(!products[productId].exists, "AuthChain: product already registered");
        _;
    }

    function registerProduct(string memory productId, string memory imageHash)
        external
        notAlreadyRegistered(productId)
    {
        products[productId] = Product({
            imageHash: imageHash,
            manufacturer: msg.sender,
            timestamp: block.timestamp,
            exists: true
        });
        productIds.push(productId);
        emit ProductRegistered(productId, msg.sender, imageHash, block.timestamp);
    }

    function getProduct(string memory productId)
        external
        view
        returns (string memory imageHash, address manufacturer, uint256 timestamp, bool exists)
    {
        Product memory p = products[productId];
        return (p.imageHash, p.manufacturer, p.timestamp, p.exists);
    }

    function totalProducts() external view returns (uint256) {
        return productIds.length;
    }
}
