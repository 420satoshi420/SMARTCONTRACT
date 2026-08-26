// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/**
 * @title VulnerableERC4626Vault
 * @notice Vulnerable to first depositor share inflation attack (SWC-101)
 */
contract VulnerableERC4626Vault {
    IERC20 public immutable asset;
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;

    constructor(IERC20 _asset) {
        asset = _asset;
    }

    function totalAssets() public view returns (uint256) {
        return asset.balanceOf(address(this));
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        uint256 supply = totalSupply;
        // Flaw: Inflation attack if supply == 0 or totalAssets skewed via direct token donation
        return supply == 0 ? assets : (assets * supply) / totalAssets();
    }

    function deposit(uint256 assets, address receiver) external returns (uint256 shares) {
        shares = convertToShares(assets);
        require(shares > 0, "Zero shares");

        asset.transferFrom(msg.sender, address(this), assets);
        balanceOf[receiver] += shares;
        totalSupply += shares;
    }
}

/**
 * @title VulnerableUniswapV4Hook
 * @notice Uniswap V4 Hook with missing PoolManager authentication and dirty transient storage
 */
contract VulnerableUniswapV4Hook {
    address public poolManager;
    mapping(address => uint256) public feeDiscount;

    constructor(address _poolManager) {
        poolManager = _poolManager;
    }

    // Flaw: Missing require(msg.sender == poolManager)
    function beforeSwap(
        address sender,
        bytes32 poolKey,
        int256 amountSpecified,
        bytes calldata hookData
    ) external returns (bytes4) {
        // Untrusted caller can manipulate fee discounts or state directly
        if (hookData.length > 0) {
            address beneficiary = abi.decode(hookData, (address));
            feeDiscount[beneficiary] += 10;
        }
        return this.beforeSwap.selector;
    }
}

/**
 * @title VulnerablePermitSigner
 * @notice Vulnerable to signature replay and address(0) ecrecover bypass
 */
contract VulnerablePermitSigner {
    mapping(address => uint256) public nonces;

    // Flaw: ecrecover return is not checked against address(0), and missing chainid
    function executePermit(
        address owner,
        address spender,
        uint256 value,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 digest = keccak256(abi.encodePacked(owner, spender, value, nonces[owner]++));
        address signer = ecrecover(digest, v, r, s);
        
        // Missing require(signer != address(0), "Invalid signature");
        require(signer == owner, "Invalid signer");
    }
}
