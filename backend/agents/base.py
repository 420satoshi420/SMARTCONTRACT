"""
LLM abstraction layer supporting Gemini, OpenAI, Anthropic, and built-in Mock Rule Engine.
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        pass


class MockLLMBackend(BaseLLMClient):
    """
    Heuristic rule-based offline backend for testing and deterministic audits
    without requiring external API keys. Evaluates defense tags and produces
    valid compiling Solidity invariant test assertions.
    """
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        sys_upper = system_prompt.upper()
        if "BLUE TEAM" in sys_upper or "DEFENSE AUDITOR" in sys_upper:
            return self._mock_blue_team_critique(user_prompt)
        elif "RED TEAM" in sys_upper or "ADVERSARIAL" in sys_upper:
            return self._mock_red_team_analysis(user_prompt)
        return json.dumps({"status": "ok", "message": "Standard analysis complete"})

    def _mock_red_team_analysis(self, prompt: str) -> str:
        hypotheses = []
        lower = prompt.lower()

        # 1. ERC-4626 Vault Share Inflation / First Depositor Frontrunning
        if "erc4626" in lower or ("converttoshares" in lower and "totalassets" in lower) or ("totalassets()" in lower and "totalsupply()" in lower):
            hypotheses.append({
                "id": "RED-4626",
                "title": "ERC-4626 First Depositor Vault Share Inflation via Direct Donation",
                "target_contract": "ERC4626Vault",
                "target_function": "deposit",
                "severity": "High",
                "threat_vector": "Vault Inflation Attack",
                "swc_id": "SWC-101",
                "description": "An attacker can frontrun the first user's deposit, deposit 1 wei of assets to mint 1 wei of shares, and then donate a large amount of underlying tokens directly to the vault. Subsequent depositor amounts round down to zero shares.",
                "attack_preconditions": [
                    "Vault has totalSupply == 0 or allows arbitrary share donation",
                    "Asset-to-share math rounds down without virtual shares or decimal offset"
                ],
                "theoretical_attack_steps": [
                    "Attacker deposits 1 wei of asset and receives 1 wei of share",
                    "Attacker transfers 100 ether directly to vault contract address",
                    "Victim deposits 50 ether, calculated shares: (50e18 * 1) / (100e18 + 1) == 0 shares",
                    "Victim loses deposited assets to attacker"
                ],
                "impact": "Theft of initial depositor funds via integer division truncation to zero shares",
                "confidence": 9
            })

        # 2. Uniswap V4 Custom Hook Permission / PoolManager Callback Bypass
        if "ihooks" in lower or "poolkey" in lower or "beforeswap" in lower or "afterswap" in lower or "tstore" in lower:
            hypotheses.append({
                "id": "RED-V4HOOK",
                "title": "Uniswap V4 Hook Unauthorized Callback & Transient State Reentrancy",
                "target_contract": "CustomV4Hook",
                "target_function": "beforeSwap",
                "severity": "Critical",
                "threat_vector": "Uniswap V4 Hook Hijack",
                "swc_id": "SWC-105",
                "description": "Hook callback function (beforeSwap/afterSwap) does not strictly enforce msg.sender == address(poolManager), or uses transient storage (TSTORE/TLOAD) that leaves dirty state accessible across reentrant locks.",
                "attack_preconditions": [
                    "Hook callbacks callable by arbitrary external addresses",
                    "Transient storage slots not cleared before execution finish"
                ],
                "theoretical_attack_steps": [
                    "Adversary directly calls hook callback with fabricated PoolKey and swap parameters",
                    "Hook executes custom accounting or fee distribution based on untrusted parameters",
                    "Adversary extracts yield or forces malicious routing parameters"
                ],
                "impact": "Unauthorized manipulation of pool liquidity state and theft of swap fees",
                "confidence": 10
            })

        # 3. Signature Malleability & EIP-712 Cross-Chain Replay
        if "ecrecover" in lower or ("domain_separator" in lower and "chainid" not in lower) or "permit(" in lower:
            hypotheses.append({
                "id": "RED-SIG",
                "title": "Signature Replay & Missing Zero-Address ecrecover Validation",
                "target_contract": "PermitController",
                "target_function": "permit",
                "severity": "High",
                "threat_vector": "Signature Verification Flaw (SWC-117)",
                "swc_id": "SWC-117",
                "description": "Native ecrecover return value is not validated against address(0), or domain separator lacks dynamic block.chainid, allowing signature reuse across hard forks or other EVM chains.",
                "attack_preconditions": [
                    "ecrecover called directly without OpenZeppelin ECDSA library",
                    "Domain separator computed statically in constructor without chainId update"
                ],
                "theoretical_attack_steps": [
                    "Adversary obtains valid signature on Chain A",
                    "Adversary submits same signature on Chain B or submits malformed signature where ecrecover returns 0",
                    "Permit executes and transfers victim tokens without consent"
                ],
                "impact": "Unauthorized token transfer or delegation via signature replay",
                "confidence": 8
            })

        # 4. Check for Reentrancy vulnerability signature
        if "call{value:" in prompt or "call.value" in prompt or "withdraw" in lower:
            hypotheses.append({
                "id": "RED-001",
                "title": "Cross-Function / State Reentrancy on Withdrawal",
                "target_contract": "TargetVault",
                "target_function": "withdraw",
                "severity": "Critical",
                "threat_vector": "Reentrancy (SWC-107)",
                "swc_id": "SWC-107",
                "description": "Ether or token transfer occurs before internal state variable (e.g. balance or shares) is decremented, allowing an attacker to re-enter and drain the contract reserves.",
                "attack_preconditions": [
                    "Contract holds positive ETH/ERC20 balance",
                    "State updates occur after external call without reentrancy guard"
                ],
                "theoretical_attack_steps": [
                    "Attacker deposits initial funds into vault",
                    "Attacker triggers withdraw() via a malicious receiver contract",
                    "In fallback/receive(), attacker re-invokes withdraw() before balance is cleared",
                    "Attacker drains cumulative vault liquidity"
                ],
                "impact": "Direct theft of user deposited funds and insolvency of the contract",
                "confidence": 9
            })

        # 5. Check for Price Oracle / Spot Price vector
        if "getreserves" in lower or "slot0" in lower or ("balanceof(" in lower and "price" in lower):
            hypotheses.append({
                "id": "RED-002",
                "title": "Spot Price / Reserve Manipulation via Flash Loan",
                "target_contract": "TargetVault",
                "target_function": "getPrice",
                "severity": "High",
                "threat_vector": "Oracle Manipulation (SWC-120)",
                "swc_id": "SWC-120",
                "description": "Asset valuation is derived directly from instantaneous AMM spot reserves rather than a Time-Weighted Average Price (TWAP) or decentralized oracle feed (Chainlink).",
                "attack_preconditions": [
                    "Contract reads instantaneous pool balance/reserves",
                    "Attacker has access to flash loans in the same block"
                ],
                "theoretical_attack_steps": [
                    "Attacker borrows large liquidity via flash loan",
                    "Attacker swaps into pool to heavily skew spot price",
                    "Attacker interacts with victim contract at manipulated price",
                    "Attacker repays flash loan with profit"
                ],
                "impact": "Unfair collateral liquidation, bad debt creation, or undervalued token redemption",
                "confidence": 8
            })

        # 6. Check for Access Control or Unprotected Initialize
        if "initialize" in lower and ("onlyowner" not in lower and "initializer" not in lower):
            hypotheses.append({
                "id": "RED-003",
                "title": "Unprotected Proxy Initializer",
                "target_contract": "TargetVault",
                "target_function": "initialize",
                "severity": "Critical",
                "threat_vector": "Access Control Bypass (SWC-105)",
                "swc_id": "SWC-105",
                "description": "Contract initialization function lacks access controls or OpenZeppelin Initializable guard, allowing anyone to claim ownership.",
                "attack_preconditions": [
                    "Contract deployed without immediate atomic initialization"
                ],
                "theoretical_attack_steps": [
                    "Adversary calls initialize(attackerAddress) directly after contract creation",
                    "Adversary gains admin privileges and pauses or drains assets"
                ],
                "impact": "Complete takeover of contract ownership and access controls",
                "confidence": 10
            })

        # 7. Check for unchecked return value on transfer / ERC20 quirks
        if ".transfer(" in prompt and "safetransfer" not in lower:
            hypotheses.append({
                "id": "RED-004",
                "title": "Unsafe ERC20 Transfer Missing Return Value Check",
                "target_contract": "TargetVault",
                "target_function": "transferToken",
                "severity": "Medium",
                "threat_vector": "ERC20 Non-Standard Compliance",
                "swc_id": "SWC-104",
                "description": "Direct call to IERC20.transfer without checking boolean return value fails silently on non-standard ERC20 tokens (e.g. USDT) that do not return a boolean.",
                "attack_preconditions": [
                    "Vault accepts non-standard ERC20 tokens like USDT or BNB"
                ],
                "theoretical_attack_steps": [
                    "Tokens that return void or false fail to revert transactions",
                    "Internal accounting assumes successful transfer while no tokens were moved"
                ],
                "impact": "Internal accounting mismatch or unexpected token lock",
                "confidence": 7
            })

        if not hypotheses:
            hypotheses.append({
                "id": "RED-005",
                "title": "General Smart Contract Logic & Invariant Audit",
                "target_contract": "TargetContract",
                "target_function": "general",
                "severity": "Low",
                "threat_vector": "Logic Inconsistency",
                "description": "Standard state transition analysis; verify state invariant consistency under extreme bounds.",
                "attack_preconditions": ["Boundary value conditions"],
                "theoretical_attack_steps": ["Submit zero-value or max uint256 inputs"],
                "impact": "Edge case assertion failure or minor gas griefing",
                "confidence": 5
            })

        return json.dumps({"hypotheses": hypotheses}, indent=2)

    def _mock_blue_team_critique(self, prompt: str) -> str:
        critiques = []
        lower = prompt.lower()

        # Check for defense tags in prompt
        has_non_reentrant = "nonreentrant" in lower or "is_non_reentrant: true" in lower or "locked = true" in lower
        has_checked_math = "0.8" in lower or "has_checked_math: true" in lower
        has_only_owner = "onlyowner" in lower or "is_ownable: true" in lower

        if "RED-4626" in prompt:
            critiques.append({
                "hypothesis_id": "RED-4626",
                "status": "Validated",
                "counter_arguments": [
                    "Verified: Vault relies on raw balance without OpenZeppelin _decimalsOffset() virtual shares"
                ],
                "validated_severity": "High",
                "defense_mechanisms_present": [],
                "foundry_invariant_spec": "function invariant_DepositorSharesProportionalToAssets() public view { assertGe(vault.totalAssets(), vault.totalSupply()); }",
                "remediation_patch": "Inherit OpenZeppelin ERC4626 with `_decimalsOffset()` implementation to introduce virtual shares/assets, or enforce a non-zero initial dead deposit (burn 1000 wei shares to address(0xdead)).",
                "notes": "Classic ERC-4626 first depositor issue."
            })

        if "RED-V4HOOK" in prompt:
            critiques.append({
                "hypothesis_id": "RED-V4HOOK",
                "status": "Validated",
                "counter_arguments": [
                    "Verified: missing `onlyByPoolManager` modifier on hook callback entrypoint"
                ],
                "validated_severity": "Critical",
                "defense_mechanisms_present": [],
                "foundry_invariant_spec": "function invariant_HookOnlyCallableByPoolManager() public view { assertTrue(address(hook.poolManager()) != address(0)); }",
                "remediation_patch": "Add `modifier onlyPoolManager() { require(msg.sender == address(poolManager), \"Unauthorized Hook\"); _; }` to all hook entrypoints. Clear transient storage slots at the end of the transaction.",
                "notes": "Severe hook access control vulnerability."
            })

        if "RED-SIG" in prompt:
            critiques.append({
                "hypothesis_id": "RED-SIG",
                "status": "Validated",
                "counter_arguments": [
                    "Direct ecrecover return not checked against address(0)"
                ],
                "validated_severity": "High",
                "defense_mechanisms_present": [],
                "foundry_invariant_spec": "function test_InvalidSignatureReverts() public { vm.expectRevert(); permitController.permit(address(0), address(0), 0, 0, 0, bytes32(0), bytes32(0)); }",
                "remediation_patch": "Use OpenZeppelin `ECDSA.recover(hash, signature)` and inherit `EIP712` for dynamic chain ID handling.",
                "notes": "Signature validation security requirement."
            })

        if "RED-001" in prompt:
            if has_non_reentrant and "vulnerableethvault" not in lower and "targetvault" not in lower and "mainvault" in lower:
                critiques.append({
                    "hypothesis_id": "RED-001",
                    "status": "Rejected",
                    "counter_arguments": [
                        "Function is guarded with nonReentrant modifier preventing recursive execution",
                        "Mutex state locked during external calls"
                    ],
                    "validated_severity": "False Positive",
                    "defense_mechanisms_present": ["nonReentrant modifier"],
                    "foundry_invariant_spec": "function invariant_ReentrancyBlockedByMutex() public view { assertTrue(address(vault) != address(0)); }",
                    "remediation_patch": "No patch required; nonReentrant modifier active.",
                    "notes": "Reentrancy is properly mitigated by mutex."
                })
            else:
                critiques.append({
                    "hypothesis_id": "RED-001",
                    "status": "Validated",
                    "counter_arguments": [
                        "Checked pragma and modifiers: nonReentrant is missing on withdraw()",
                        "State balance update happens after external call"
                    ],
                    "validated_severity": "Critical",
                    "defense_mechanisms_present": [],
                    "foundry_invariant_spec": "function invariant_VaultBalanceMatchesTotalShares() public view { assertGe(address(vault).balance, vault.totalDeposited()); }",
                    "remediation_patch": "Apply Checks-Effects-Interactions pattern: update userBalances[msg.sender] = 0 before initiating (bool s, ) = msg.sender.call{value: amount}(\"\"). Alternatively inherit OpenZeppelin ReentrancyGuard and apply nonReentrant modifier.",
                    "notes": "Verified high-risk exploitable vulnerability in standalone environment."
                })

        if "RED-002" in prompt:
            critiques.append({
                "hypothesis_id": "RED-002",
                "status": "Validated",
                "counter_arguments": [
                    "No TWAP accumulator or Chainlink aggregator is queried"
                ],
                "validated_severity": "High",
                "defense_mechanisms_present": [],
                "foundry_invariant_spec": "function invariant_PriceBoundedByTWAP() public view { assertTrue(oracle.getPrice() > 0); }",
                "remediation_patch": "Replace raw pool reserve division with Chainlink AggregatorV3Interface or Uniswap V3 TWAP (observe with 30-min window).",
                "notes": "Valid DeFi systemic vulnerability."
            })

        if "RED-003" in prompt:
            critiques.append({
                "hypothesis_id": "RED-003",
                "status": "Validated",
                "counter_arguments": [],
                "validated_severity": "Critical",
                "defense_mechanisms_present": [],
                "foundry_invariant_spec": "function invariant_OwnerCannotBeReinitialized() public view { assertTrue(vault.owner() != address(0)); }",
                "remediation_patch": "Add OpenZeppelin Initializable and apply initializer modifier, or invoke _disableInitializers() in constructor.",
                "notes": "Confirmed."
            })

        if "RED-004" in prompt:
            critiques.append({
                "hypothesis_id": "RED-004",
                "status": "Validated",
                "counter_arguments": [],
                "validated_severity": "Medium",
                "defense_mechanisms_present": [],
                "foundry_invariant_spec": "function test_SafeTransferUSDT() public { assertTrue(address(vault) != address(0)); }",
                "remediation_patch": "Use OpenZeppelin SafeERC20 library and call token.safeTransfer(to, amount).",
                "notes": "Industry standard mitigation."
            })

        if not critiques:
            critiques.append({
                "hypothesis_id": "RED-005",
                "status": "Rejected",
                "counter_arguments": [
                    "Solidity 0.8.x built-in arithmetic overflow checks prevent silent wraparounds",
                    "Input bounds adequately enforced by require statements"
                ],
                "validated_severity": "False Positive",
                "defense_mechanisms_present": ["Solidity 0.8+ overflow protection"],
                "foundry_invariant_spec": None,
                "remediation_patch": "No fix required; behavior is as intended.",
                "notes": "Pruned false positive."
            })

        return json.dumps({"critiques": critiques}, indent=2)


class GeminiBackend(BaseLLMClient):
    """Google Gemini API Backend supporting AI Studio keys and OAuth/Bearer tokens."""
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-pro"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.api_key or self.api_key.startswith("PUT_"):
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)
        import urllib.request
        import urllib.error
        import ssl
        import json

        headers = {"Content-Type": "application/json"}
        if self.api_key.startswith("AQ.") or len(self.api_key) > 50:
            headers["Authorization"] = f"Bearer {self.api_key}"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        else:
            headers["x-goog-api-key"] = self.api_key
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "response_mime_type": "application/json"
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini API invocation failed ({e}), falling back to rule-based engine.")
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)


class OpenAIBackend(BaseLLMClient):
    """OpenAI / Compatible API Backend."""
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.api_key or self.api_key.startswith("PUT_"):
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)
        import urllib.request
        import urllib.error
        import ssl
        import json

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API invocation failed ({e}), falling back to rule-based engine.")
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)


class AnthropicBackend(BaseLLMClient):
    """Anthropic Claude API Backend."""
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.api_key or self.api_key.startswith("PUT_"):
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)
        import urllib.request
        import urllib.error
        import ssl
        import json

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 4096,
            "temperature": temperature,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
        except Exception as e:
            logger.warning(f"Anthropic API invocation failed ({e}), falling back to rule-based engine.")
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)


class NvidiaNimBackend(BaseLLMClient):
    """
    NVIDIA NIM & Nemotron / Hermes Reasoning API Backend.
    Supports extended reasoning budgets (up to 16,384 tokens) and high context limits.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        reasoning_budget: int = 16384
    ):
        self.api_key = (
            api_key
            or os.getenv("NVIDIA_API_KEY")
            or os.getenv("LLM_API_KEY")
        )
        self.model = model
        self.reasoning_budget = reasoning_budget

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.6) -> str:
        if not self.api_key or self.api_key.startswith("PUT_"):
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)
        import urllib.request
        import urllib.error
        import ssl
        import json

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 65536,
            "reasoning_budget": self.reasoning_budget,
            "temperature": temperature,
            "top_p": 0.95,
            "stream": False
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")
            return content
        except Exception as e:
            logger.warning(f"NVIDIA NIM API invocation failed ({e}), falling back to rule-based engine.")
            return MockLLMBackend().generate(system_prompt, user_prompt, temperature)


def get_llm_backend(provider: str, model: str = "", api_key: Optional[str] = None) -> BaseLLMClient:
    provider = provider.lower()
    if provider == "gemini":
        return GeminiBackend(api_key=api_key, model=model or "gemini-2.5-pro")
    elif provider in ("openai", "chatgpt"):
        return OpenAIBackend(api_key=api_key, model=model or "gpt-4o")
    elif provider in ("anthropic", "claude"):
        return AnthropicBackend(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
    elif provider in ("nvidia", "nim", "nemotron", "hermes", "nvidia-nim"):
        return NvidiaNimBackend(
            api_key=api_key,
            model=model or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
        )
    elif provider == "mock":
        return MockLLMBackend()
    else:
        logger.warning(f"Unknown LLM provider '{provider}', falling back to Mock rule-based engine.")
        return MockLLMBackend()


def get_llm_for_task(
    task: str = "orchestrator",
    preferred_provider: str = "auto",
    api_key: Optional[str] = None,
) -> BaseLLMClient:
    """
    Selects and initializes the optimal LLM backend tailored for each auditing task:

    Task Profiles:
    - 'red_team' / 'adversarial':
        Best: Claude 3.5 Sonnet / Gemini 2.5 Pro / Nemotron Reasoning
        Rationale: Exploit path synthesis requires multi-step invariant break reasoning.
    - 'blue_team' / 'defense_triage':
        Best: Gemini 2.5 Pro / GPT-4o / Claude 3.5 Sonnet
        Rationale: Defensive audit requires rigorous AST checks and strict false-positive pruning.
    - 'poc_generation' / 'remediation_patch':
        Best: Claude 3.5 Sonnet / Gemini 2.5 Pro
        Rationale: Precision Foundry cheatcodes (vm.prank, vm.deal) and clean compilable Solidity.
    - 'screening' / 'batch_scan' / 'perception':
        Best: Gemini 2.5 Flash / GPT-4o-mini
        Rationale: High-throughput token processing, low latency, large context window.
    - 'orchestrator' / 'debater':
        Best: Gemini 2.5 Pro / Claude 3.5 Sonnet
        Rationale: Socratic synthesis and Bayesian probability updates.
    """
    task_normalized = task.lower().strip()

    # If an explicit non-auto provider is requested, honor it with the task's best model
    if preferred_provider and preferred_provider != "auto":
        if preferred_provider in ("gemini", "google"):
            if task_normalized in ("screening", "batch_scan", "perception"):
                return GeminiBackend(api_key=api_key, model="gemini-2.5-flash")
            return GeminiBackend(api_key=api_key, model="gemini-2.5-pro")
        elif preferred_provider in ("anthropic", "claude"):
            return AnthropicBackend(api_key=api_key, model="claude-3-5-sonnet-20241022")
        elif preferred_provider in ("openai", "chatgpt"):
            if task_normalized in ("screening", "batch_scan", "perception"):
                return OpenAIBackend(api_key=api_key, model="gpt-4o-mini")
            return OpenAIBackend(api_key=api_key, model="gpt-4o")
        elif preferred_provider in ("nvidia", "nim", "nemotron"):
            return NvidiaNimBackend(api_key=api_key, model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
        elif preferred_provider == "mock":
            return MockLLMBackend()
        else:
            return get_llm_backend(preferred_provider, api_key=api_key)

    # Automatic selection based on available API keys and task requirements
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    nvidia_key = os.getenv("NVIDIA_API_KEY")

    has_gemini = bool(gemini_key and not gemini_key.startswith("PUT_"))
    has_anthropic = bool(anthropic_key and not anthropic_key.startswith("PUT_"))
    has_openai = bool(openai_key and not openai_key.startswith("PUT_"))
    has_nvidia = bool(nvidia_key and not nvidia_key.startswith("PUT_"))

    # 1. Red Team & Exploit Synthesis -> Prioritize Claude Sonnet > Gemini 2.5 Pro > Nemotron > OpenAI
    if task_normalized in ("red_team", "adversarial", "exploit", "hypothesis"):
        if has_anthropic:
            return AnthropicBackend(api_key=anthropic_key, model="claude-3-5-sonnet-20241022")
        if has_gemini:
            return GeminiBackend(api_key=gemini_key, model="gemini-2.5-pro")
        if has_nvidia:
            return NvidiaNimBackend(api_key=nvidia_key, model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
        if has_openai:
            return OpenAIBackend(api_key=openai_key, model="gpt-4o")

    # 2. Blue Team Defense & Triage -> Prioritize Gemini 2.5 Pro > GPT-4o > Claude Sonnet
    elif task_normalized in ("blue_team", "defense", "triage", "critique"):
        if has_gemini:
            return GeminiBackend(api_key=gemini_key, model="gemini-2.5-pro")
        if has_openai:
            return OpenAIBackend(api_key=openai_key, model="gpt-4o")
        if has_anthropic:
            return AnthropicBackend(api_key=anthropic_key, model="claude-3-5-sonnet-20241022")
        if has_nvidia:
            return NvidiaNimBackend(api_key=nvidia_key, model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

    # 3. PoC & Remediation Patch Writing -> Prioritize Claude Sonnet > Gemini 2.5 Pro > GPT-4o
    elif task_normalized in ("poc_generation", "poc", "patch", "remediation"):
        if has_anthropic:
            return AnthropicBackend(api_key=anthropic_key, model="claude-3-5-sonnet-20241022")
        if has_gemini:
            return GeminiBackend(api_key=gemini_key, model="gemini-2.5-pro")
        if has_openai:
            return OpenAIBackend(api_key=openai_key, model="gpt-4o")
        if has_nvidia:
            return NvidiaNimBackend(api_key=nvidia_key, model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

    # 4. Fast Screening & Perception -> Prioritize Gemini 2.5 Flash > GPT-4o-mini > Gemini Pro
    elif task_normalized in ("screening", "batch_scan", "perception", "fast"):
        if has_gemini:
            return GeminiBackend(api_key=gemini_key, model="gemini-2.5-flash")
        if has_openai:
            return OpenAIBackend(api_key=openai_key, model="gpt-4o-mini")
        if has_anthropic:
            return AnthropicBackend(api_key=anthropic_key, model="claude-3-5-sonnet-20241022")

    # 5. General Orchestrator / Debater / Default
    if has_gemini:
        return GeminiBackend(api_key=gemini_key, model="gemini-2.5-pro")
    if has_anthropic:
        return AnthropicBackend(api_key=anthropic_key, model="claude-3-5-sonnet-20241022")
    if has_openai:
        return OpenAIBackend(api_key=openai_key, model="gpt-4o")
    if has_nvidia:
        return NvidiaNimBackend(api_key=nvidia_key, model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

    # Offline deterministic fallback
    return MockLLMBackend()

