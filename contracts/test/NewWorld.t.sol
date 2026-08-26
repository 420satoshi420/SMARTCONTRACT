// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../NewWorldToken.sol";
import "../NewWorldPool.sol";

contract NewWorldTest is Test {
    NewWorldToken public token;
    NewWorldPool public pool;

    address public owner = address(this);
    address public alice = address(0xA11CE);
    address public bob = address(0xB0B);

    uint256 constant INITIAL_SUPPLY = 1_000_000 ether;

    function setUp() public {
        // 1. Deploy NewWorldToken
        token = new NewWorldToken(INITIAL_SUPPLY);

        // 2. Deploy NewWorldPool
        pool = new NewWorldPool(address(token));

        // Fund Alice and Bob with ETH and NEWWORLD tokens
        vm.deal(alice, 100 ether);
        vm.deal(bob, 100 ether);

        token.transfer(alice, 10_000 ether);
        token.transfer(bob, 10_000 ether);

        // Fund pool with reward reserves
        token.transfer(address(pool), 50_000 ether);
    }

    function test_InitialState() public view {
        assertEq(token.name(), "New World");
        assertEq(token.symbol(), "NEWWORLD");
        assertEq(token.decimals(), 18);
        assertEq(token.owner(), owner);
        assertEq(pool.owner(), owner);
    }

    function test_AddLiquidity() public {
        vm.startPrank(alice);
        token.approve(address(pool), 1000 ether);
        uint256 lpShares = pool.addLiquidity{value: 10 ether}(1000 ether);
        vm.stopPrank();

        assertGt(lpShares, 0);
        assertEq(pool.reserveEth(), 10 ether);
        assertEq(pool.reserveToken(), 1000 ether);
        assertEq(pool.liquidityOf(alice), lpShares);
    }

    function test_SwapEthForToken() public {
        // Initial liquidity
        vm.startPrank(alice);
        token.approve(address(pool), 10_000 ether);
        pool.addLiquidity{value: 10 ether}(10_000 ether);
        vm.stopPrank();

        uint256 bobTokensBefore = token.balanceOf(bob);

        // Bob swaps 1 ETH for tokens
        vm.startPrank(bob);
        uint256 tokensOut = pool.swapEthForToken{value: 1 ether}(1);
        vm.stopPrank();

        assertGt(tokensOut, 0);
        assertEq(token.balanceOf(bob), bobTokensBefore + tokensOut);
        assertEq(pool.reserveEth(), 11 ether);
    }

    function test_SwapTokenForEth() public {
        // Initial liquidity
        vm.startPrank(alice);
        token.approve(address(pool), 10_000 ether);
        pool.addLiquidity{value: 10 ether}(10_000 ether);
        vm.stopPrank();

        uint256 bobEthBefore = bob.balance;

        // Bob swaps 500 tokens for ETH
        vm.startPrank(bob);
        token.approve(address(pool), 500 ether);
        uint256 ethOut = pool.swapTokenForEth(500 ether, 1);
        vm.stopPrank();

        assertGt(ethOut, 0);
        assertEq(bob.balance, bobEthBefore + ethOut);
    }

    function test_StakingRewardsAccrual() public {
        // Alice adds liquidity
        vm.startPrank(alice);
        token.approve(address(pool), 5000 ether);
        pool.addLiquidity{value: 5 ether}(5000 ether);
        vm.stopPrank();

        // Warp time 100 seconds
        vm.warp(block.timestamp + 100);

        uint256 pending = pool.getPendingReward(alice);
        assertGt(pending, 0);

        // Claim reward
        uint256 balBefore = token.balanceOf(alice);
        vm.prank(alice);
        uint256 claimed = pool.claimRewards();

        assertEq(claimed, pending);
        assertEq(token.balanceOf(alice), balBefore + claimed);
    }

    function test_RemoveLiquidity() public {
        vm.startPrank(alice);
        token.approve(address(pool), 1000 ether);
        uint256 lpShares = pool.addLiquidity{value: 10 ether}(1000 ether);

        (uint256 ethOut, uint256 tokenOut) = pool.removeLiquidity(lpShares);
        vm.stopPrank();

        assertEq(ethOut, 10 ether);
        assertEq(tokenOut, 1000 ether);
        assertEq(pool.totalLiquidity(), 0);
    }
}
