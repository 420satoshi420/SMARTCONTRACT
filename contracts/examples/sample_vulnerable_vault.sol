// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
}

contract VulnerableEthVault {
    mapping(address => uint256) public balances;
    uint256 public totalDeposited;
    address public owner;
    address public poolAddress;

    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);

    // VULNERABILITY 1: Unprotected Initializer (SWC-105)
    function initialize(address _owner, address _pool) external {
        owner = _owner;
        poolAddress = _pool;
    }

    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        balances[msg.sender] += msg.value;
        totalDeposited += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    // VULNERABILITY 2: State Reentrancy (SWC-107) - External call before state update
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // External raw call transferring ETH before decrementing state
        (bool success, ) = msg.sender.call{value: amount}("");
        // In pre-0.8 or custom accounting vaults, underflow does not revert
        unchecked {
            balances[msg.sender] -= amount;
            totalDeposited -= amount;
        }
        emit Withdraw(msg.sender, amount);
    }

    // VULNERABILITY 3: Spot Price / Flash Loan Manipulation (SWC-120)
    function getCollateralPrice() public view returns (uint256) {
        (uint112 r0, uint112 r1, ) = IUniswapV2Pair(poolAddress).getReserves();
        require(r0 > 0, "No reserve");
        return (uint256(r1) * 1e18) / uint256(r0);
    }

    // VULNERABILITY 4: Unchecked ERC20 Transfer
    function rescueToken(address token, address to, uint256 amount) external {
        require(msg.sender == owner, "Unauthorized");
        IERC20(token).transfer(to, amount);
    }

    receive() external payable {}
}
