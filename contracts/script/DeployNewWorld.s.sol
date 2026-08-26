// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../NewWorldToken.sol";
import "../NewWorldPool.sol";

contract DeployNewWorld is Script {
    function run() external {
        uint256 deployerPrivateKey;
        
        try vm.envUint("PRIVATE_KEY") returns (uint256 pk) {
            deployerPrivateKey = pk;
        } catch {
            // Default Anvil Account #0
            deployerPrivateKey = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
        }

        address deployer = vm.addr(deployerPrivateKey);
        console.log("==================================================");
        console.log("[Deploy] Deploying NewWorld Protocol Contracts");
        console.log("Deployer Address:", deployer);
        console.log("Deployer Balance (ETH):", deployer.balance / 1e18);
        console.log("==================================================");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy NewWorldToken (1,000,000 NEW supply)
        uint256 initialSupply = 1_000_000 ether;
        NewWorldToken token = new NewWorldToken(initialSupply);
        console.log("[Success] NewWorldToken Deployed at:", address(token));

        // 2. Deploy NewWorldPool AMM & Staking Resource
        NewWorldPool pool = new NewWorldPool(address(token));
        console.log("[Success] NewWorldPool Deployed at:", address(pool));

        // 3. Fund pool with initial reward reserves (50,000 NEW)
        token.transfer(address(pool), 50_000 ether);
        console.log("[Success] Funded Pool with 50,000 NEW reward reserves");

        // 4. Provide Initial Liquidity if deployer has sufficient ETH (>= 1 ETH)
        if (deployer.balance >= 1 ether) {
            token.approve(address(pool), 10_000 ether);
            uint256 lpShares = pool.addLiquidity{value: 1 ether}(10_000 ether);
            console.log("[Success] Seeded Initial Liquidity: 1 ETH + 10,000 NEW");
            console.log("[Success] Deployer LP Shares Received:", lpShares);
        } else {
            console.log("[Info] Deployer ETH < 1 ETH. Skipped auto-liquidity seeding. Pool is ready for user deposits.");
        }


        vm.stopBroadcast();

        console.log("==================================================");
        console.log("[Complete] Deployment & Pool Initialization Done!");
        console.log("Token Address:", address(token));
        console.log("Pool Address :", address(pool));
        console.log("==================================================");

    }
}
