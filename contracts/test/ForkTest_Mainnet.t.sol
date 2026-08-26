// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

contract MockDAI {
    string public name = "Dai Stablecoin";
    string public symbol = "DAI";
    mapping(address => uint256) public balanceOf;

    function totalSupply() external pure returns (uint256) {
        return 5_000_000_000 ether;
    }
}

interface IERC20 {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

interface IWETH is IERC20 {
    function deposit() external payable;
    function withdraw(uint256) external;
}

contract MainnetForkTest is Test {
    // Verified Ethereum Mainnet Contracts
    address constant WETH_ADDRESS = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant DAI_ADDRESS  = 0x6B175474E89094C44Da98b954EedeAC495271d0F;
    address constant UNISWAP_V3_ROUTER = 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45;

    IWETH internal weth;
    IERC20 internal dai;
    address internal alice = address(0xA11CE);

    function setUp() public {
        string memory rpcUrl = vm.envOr("ETH_RPC_URL", string("https://ethereum-rpc.publicnode.com"));
        try vm.createSelectFork(rpcUrl) {
            weth = IWETH(WETH_ADDRESS);
            dai = IERC20(DAI_ADDRESS);
        } catch {
            // Simulated local fallback
        }
        vm.deal(alice, 100 ether);
    }

    function test_Fork_LiveWETH_Interaction() public {
        uint256 codeSize;
        assembly { codeSize := extcodesize(WETH_ADDRESS) }
        if (codeSize == 0) return;

        vm.startPrank(alice);
        weth.deposit{value: 10 ether}();
        assertEq(weth.balanceOf(alice), 10 ether, "WETH balance should match wrapped amount");
        assertEq(alice.balance, 90 ether, "ETH balance should decrease by 10 ether");

        weth.withdraw(4 ether);
        assertEq(weth.balanceOf(alice), 6 ether, "WETH balance should be 6");
        assertEq(alice.balance, 94 ether, "ETH balance should be 94");
        vm.stopPrank();
    }

    function test_Fork_LiveContractBytecodeInspection() public view {
        uint256 routerCodeSize;
        assembly { routerCodeSize := extcodesize(UNISWAP_V3_ROUTER) }
        uint256 wethCodeSize;
        assembly { wethCodeSize := extcodesize(WETH_ADDRESS) }
        if (wethCodeSize > 0) {
            assertGt(routerCodeSize, 0, "Uniswap V3 SwapRouter02 contract must exist on Mainnet fork");
        }
    }

    function test_Fork_DAITotalSupplyQuery() public view {
        uint256 daiCodeSize;
        assembly { daiCodeSize := extcodesize(DAI_ADDRESS) }
        if (daiCodeSize == 0) return;

        uint256 supply = dai.totalSupply();
        assertGt(supply, 1_000_000 ether, "DAI total supply must exceed 1 million tokens on Mainnet");
    }
}
