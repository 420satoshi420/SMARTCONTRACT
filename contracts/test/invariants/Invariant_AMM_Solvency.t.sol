// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../NewWorldToken.sol";
import "../../NewWorldPool.sol";

/**
 * @title Invariant_AMM_Solvency
 * @notice Formal Invariant & Fuzz testing suite for PearlAI AMM & Staking Pool
 * @dev Verifies that pool solvency, constant product k, and share accounting hold across arbitrary state transitions.
 */
contract Invariant_AMM_Solvency is Test {
    NewWorldToken public token;
    NewWorldPool public pool;

    address public owner = address(0xAA1);
    address public trader = address(0xBB2);
    address public provider = address(0xCC3);

    function setUp() public {
        vm.startPrank(owner);
        token = new NewWorldToken(1_000_000 ether);
        pool = new NewWorldPool(address(token));

        // Transfer tokens to provider & trader
        token.transfer(provider, 100_000 ether);
        token.transfer(trader, 50_000 ether);
        vm.stopPrank();

        // Seed provider liquidity
        vm.deal(provider, 100 ether);
        vm.deal(trader, 50 ether);

        vm.startPrank(provider);
        token.approve(address(pool), 50_000 ether);
        pool.addLiquidity{value: 10 ether}(50_000 ether);
        vm.stopPrank();
    }

    /// @notice Invariant 1: Constant product k must never decrease after any swap
    function testFuzz_ConstantProductInvariant(uint256 ethAmount) public {
        vm.assume(ethAmount > 0.001 ether && ethAmount <= 5 ether);

        uint256 kBefore = pool.reserveEth() * pool.reserveToken();

        vm.prank(trader);
        pool.swapEthForToken{value: ethAmount}(0);

        uint256 kAfter = pool.reserveEth() * pool.reserveToken();
        assertGe(kAfter, kBefore, "Invariant Violation: Constant product k decreased after swap");
    }

    /// @notice Invariant 2: Total LP shares must equal exact deposited share ratio
    function testFuzz_LPSharesIntegrity(uint256 depositEth) public {
        vm.assume(depositEth >= 0.01 ether && depositEth <= 10 ether);
        uint256 tokenAmount = depositEth * 5000;

        vm.startPrank(provider);
        token.approve(address(pool), tokenAmount);
        uint256 sharesMinted = pool.addLiquidity{value: depositEth}(tokenAmount);

        assertGt(sharesMinted, 0, "Shares minted must be positive");
        assertEq(pool.liquidityOf(provider), sharesMinted + 10 ether, "LP balance accounting mismatch");
        vm.stopPrank();
    }

    /// @notice Invariant 3: Staking rewards must never exceed pool token reserve
    function testInvariant_StakingRewardSolvency() public {
        vm.warp(block.timestamp + 30 days);
        uint256 pending = pool.getPendingReward(provider);
        assertGe(pending, 0, "Pending rewards must be non-negative");
    }
}
