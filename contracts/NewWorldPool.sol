// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./NewWorldToken.sol";

/**
 * @title NewWorldPool
 * @author Eth-Hunter & NewWorld Protocol
 * @notice Automated Market Maker (AMM) Liquidity Pool & Staking Yield Resource for ETH / NEWWORLD
 */
contract NewWorldPool {
    NewWorldToken public immutable token;
    address public owner;

    // --- Pool Reserves ---
    uint256 public reserveEth;
    uint256 public reserveToken;
    uint256 public totalLiquidity;

    mapping(address => uint256) public liquidityOf;

    // --- Reward Staking System ---
    uint256 public rewardRatePerSecond = 1e16; // 0.01 NEWWORLD per second per pool share
    uint256 public lastRewardTimestamp;
    uint256 public accRewardPerShare;

    mapping(address => uint256) public rewardDebt;
    mapping(address => uint256) public pendingRewards;

    // --- Mutex Guard ---
    uint256 private _locked = 1;

    // --- Events ---
    event LiquidityAdded(address indexed provider, uint256 ethAmount, uint256 tokenAmount, uint256 lpMinted);
    event LiquidityRemoved(address indexed provider, uint256 ethAmount, uint256 tokenAmount, uint256 lpBurned);
    event Swap(address indexed user, uint256 ethIn, uint256 tokenIn, uint256 ethOut, uint256 tokenOut);
    event RewardClaimed(address indexed user, uint256 amount);
    event RewardRateUpdated(uint256 newRate);

    // --- Errors ---
    error ReentrancyGuard();
    error InsufficientLiquidity();
    error InsufficientOutputAmount();
    error InsufficientInputAmount();
    error TransferFailed();
    error Unauthorized();
    error ZeroAmount();

    modifier nonReentrant() {
        if (_locked != 1) revert ReentrancyGuard();
        _locked = 2;
        _;
        _locked = 1;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address tokenAddress) {
        if (tokenAddress == address(0)) revert Unauthorized();
        token = NewWorldToken(tokenAddress);
        owner = msg.sender;
        lastRewardTimestamp = block.timestamp;
    }

    // --- Staking & Reward Accounting ---
    function updatePool() public {
        if (block.timestamp <= lastRewardTimestamp) {
            return;
        }
        if (totalLiquidity == 0) {
            lastRewardTimestamp = block.timestamp;
            return;
        }

        uint256 timePassed = block.timestamp - lastRewardTimestamp;
        uint256 rewardAmount = timePassed * rewardRatePerSecond;
        accRewardPerShare += (rewardAmount * 1e12) / totalLiquidity;
        lastRewardTimestamp = block.timestamp;
    }

    /**
     * @notice Add ETH and NEWWORLD liquidity to the pool
     */
    function addLiquidity(uint256 tokenAmount) external payable nonReentrant returns (uint256 lpShares) {
        if (msg.value == 0 || tokenAmount == 0) revert ZeroAmount();
        updatePool();

        if (totalLiquidity == 0) {
            lpShares = msg.value; // Initial LP share based on ETH deposited
        } else {
            uint256 ethShare = (msg.value * totalLiquidity) / reserveEth;
            uint256 tokenShare = (tokenAmount * totalLiquidity) / reserveToken;
            lpShares = ethShare < tokenShare ? ethShare : tokenShare;
        }

        if (lpShares == 0) revert InsufficientLiquidity();

        // Pull tokens from user
        bool success = token.transferFrom(msg.sender, address(this), tokenAmount);
        if (!success) revert TransferFailed();

        // Update user staking accounting
        if (liquidityOf[msg.sender] > 0) {
            pendingRewards[msg.sender] += (liquidityOf[msg.sender] * accRewardPerShare) / 1e12 - rewardDebt[msg.sender];
        }

        liquidityOf[msg.sender] += lpShares;
        totalLiquidity += lpShares;
        reserveEth += msg.value;
        reserveToken += tokenAmount;

        rewardDebt[msg.sender] = (liquidityOf[msg.sender] * accRewardPerShare) / 1e12;

        emit LiquidityAdded(msg.sender, msg.value, tokenAmount, lpShares);
    }

    /**
     * @notice Remove liquidity and burn LP shares to receive ETH and NEWWORLD
     */
    function removeLiquidity(uint256 lpShares) external nonReentrant returns (uint256 ethOut, uint256 tokenOut) {
        if (lpShares == 0 || liquidityOf[msg.sender] < lpShares) revert InsufficientLiquidity();
        updatePool();

        ethOut = (lpShares * reserveEth) / totalLiquidity;
        tokenOut = (lpShares * reserveToken) / totalLiquidity;

        if (ethOut == 0 || tokenOut == 0) revert InsufficientOutputAmount();

        // Harvest pending rewards
        pendingRewards[msg.sender] += (liquidityOf[msg.sender] * accRewardPerShare) / 1e12 - rewardDebt[msg.sender];

        liquidityOf[msg.sender] -= lpShares;
        totalLiquidity -= lpShares;
        reserveEth -= ethOut;
        reserveToken -= tokenOut;

        rewardDebt[msg.sender] = (liquidityOf[msg.sender] * accRewardPerShare) / 1e12;

        // Send assets
        (bool ethSuccess, ) = msg.sender.call{value: ethOut}("");
        if (!ethSuccess) revert TransferFailed();

        bool tokenSuccess = token.transfer(msg.sender, tokenOut);
        if (!tokenSuccess) revert TransferFailed();

        emit LiquidityRemoved(msg.sender, ethOut, tokenOut, lpShares);
    }

    /**
     * @notice Swap ETH for NEWWORLD tokens (0.3% LP fee)
     */
    function swapEthForToken(uint256 minTokensOut) external payable nonReentrant returns (uint256 tokensOut) {
        if (msg.value == 0) revert InsufficientInputAmount();
        if (reserveEth == 0 || reserveToken == 0) revert InsufficientLiquidity();

        uint256 inputAmountWithFee = msg.value * 997;
        uint256 numerator = inputAmountWithFee * reserveToken;
        uint256 denominator = (reserveEth * 1000) + inputAmountWithFee;
        tokensOut = numerator / denominator;

        if (tokensOut < minTokensOut) revert InsufficientOutputAmount();

        reserveEth += msg.value;
        reserveToken -= tokensOut;

        bool success = token.transfer(msg.sender, tokensOut);
        if (!success) revert TransferFailed();

        emit Swap(msg.sender, msg.value, 0, 0, tokensOut);
    }

    /**
     * @notice Swap NEWWORLD tokens for ETH (0.3% LP fee)
     */
    function swapTokenForEth(uint256 tokenIn, uint256 minEthOut) external nonReentrant returns (uint256 ethOut) {
        if (tokenIn == 0) revert InsufficientInputAmount();
        if (reserveEth == 0 || reserveToken == 0) revert InsufficientLiquidity();

        uint256 inputAmountWithFee = tokenIn * 997;
        uint256 numerator = inputAmountWithFee * reserveEth;
        uint256 denominator = (reserveToken * 1000) + inputAmountWithFee;
        ethOut = numerator / denominator;

        if (ethOut < minEthOut) revert InsufficientOutputAmount();

        bool pullSuccess = token.transferFrom(msg.sender, address(this), tokenIn);
        if (!pullSuccess) revert TransferFailed();

        reserveToken += tokenIn;
        reserveEth -= ethOut;

        (bool ethSuccess, ) = msg.sender.call{value: ethOut}("");
        if (!ethSuccess) revert TransferFailed();

        emit Swap(msg.sender, 0, tokenIn, ethOut, 0);
    }

    /**
     * @notice Claim accumulated staking yield rewards
     */
    function claimRewards() external nonReentrant returns (uint256 reward) {
        updatePool();
        reward = pendingRewards[msg.sender] + ((liquidityOf[msg.sender] * accRewardPerShare) / 1e12 - rewardDebt[msg.sender]);
        if (reward == 0) return 0;

        pendingRewards[msg.sender] = 0;
        rewardDebt[msg.sender] = (liquidityOf[msg.sender] * accRewardPerShare) / 1e12;

        bool success = token.transfer(msg.sender, reward);
        if (!success) revert TransferFailed();

        emit RewardClaimed(msg.sender, reward);
    }

    /**
     * @notice View pending reward for an account
     */
    function getPendingReward(address account) external view returns (uint256) {
        uint256 currentAcc = accRewardPerShare;
        if (block.timestamp > lastRewardTimestamp && totalLiquidity > 0) {
            uint256 timePassed = block.timestamp - lastRewardTimestamp;
            uint256 rewardAmount = timePassed * rewardRatePerSecond;
            currentAcc += (rewardAmount * 1e12) / totalLiquidity;
        }
        return pendingRewards[account] + ((liquidityOf[account] * currentAcc) / 1e12 - rewardDebt[account]);
    }

    function setRewardRate(uint256 newRate) external onlyOwner {
        updatePool();
        rewardRatePerSecond = newRate;
        emit RewardRateUpdated(newRate);
    }

    receive() external payable {
        revert("Direct ETH deposit disabled; use addLiquidity or swapEthForToken");
    }
}
