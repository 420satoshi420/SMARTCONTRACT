// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title Historical DeFi Vulnerability Playground
 * @notice Educational and invariant audit playground showcasing realistic DeFi vulnerability patterns.
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/**
 * 1. READ-ONLY REENTRANCY IN STABLESWAP POOL (Curve / Balancer style)
 * Flaw: get_virtual_price() calculates asset price based on transient un-synced balances
 * during remove_liquidity() before transfer execution.
 */
contract StableswapPool {
    uint256[2] public balances;
    uint256 public totalShares;

    function get_virtual_price() external view returns (uint256) {
        // Returns virtual price of LP token based on current pool balances
        uint256 total_balance = balances[0] + balances[1];
        if (totalShares == 0) return 1e18;
        return (total_balance * 1e18) / totalShares;
    }

    function remove_liquidity(uint256 shares, uint256 min_amount) external {
        require(shares > 0 && shares <= totalShares, "Invalid shares");
        
        // 1. Burns shares immediately
        totalShares -= shares;
        uint256 amount = (shares * (balances[0] + balances[1])) / (totalShares + shares);

        // 2. External raw call transfers ETH / tokens (Control flow handed over while balances[] not updated yet)
        (bool s, ) = msg.sender.call{value: amount}("");
        require(s, "ETH transfer failed");

        // 3. State updated after external call (Read-only reentrancy window!)
        balances[0] -= amount;
    }
}

/**
 * 2. LENDING PROTOCOL ORACLE CONSUMER
 * Reads StableswapPool.get_virtual_price() to value user collateral during liquidation.
 */
contract LendingPoolConsumer {
    StableswapPool public pool;
    mapping(address => uint256) public userCollateralShares;

    constructor(StableswapPool _pool) {
        pool = _pool;
    }

    function getCollateralUSD(address user) public view returns (uint256) {
        // Vulnerable: Calls read-only reentrant function to price collateral
        uint256 price = pool.get_virtual_price();
        return (userCollateralShares[user] * price) / 1e18;
    }
}

/**
 * 3. PRECISION LOSS IN LIQUIDITY FEE ACCUMULATOR
 * Flaw: Division before multiplication or truncation leading to zero-fee extraction.
 */
contract FeeAccumulator {
    uint256 public totalFees;
    uint256 public constant BPS_DIVISOR = 10000;

    function calculateAndCollectFee(uint256 amount, uint256 feeBps) external returns (uint256) {
        // Flaw: Truncation when amount * feeBps < BPS_DIVISOR
        uint256 fee = (amount * feeBps) / BPS_DIVISOR;
        totalFees += fee;
        return fee;
    }
}
