"""
Automated Foundry Invariant Test Harness & Executor.
Runs generated invariant suites using `forge test` and parses execution traces.
"""

import subprocess
import shutil
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union


class ForgeRunner:
    """Executes Foundry invariant test suites in a local or temporary workspace."""

    def __init__(self, workspace_path: Optional[Path] = None, forge_bin: Optional[str] = None):
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.forge_bin = forge_bin or shutil.which("forge")

    def is_foundry_installed(self) -> bool:
        """Returns True if Foundry 'forge' executable is available in PATH."""
        if not self.forge_bin:
            return False
        return shutil.which(self.forge_bin) is not None or Path(self.forge_bin).exists()

    def extract_call_trace(self, forge_output: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses Forge output (JSON or text) and extracts call traces and counterexamples
        into a structured dictionary and reproducible markdown PoC attack steps.
        """
        calls: List[Dict[str, Any]] = []
        counterexample: List[str] = []
        raw_trace_lines: List[str] = []
        reverted = False
        invariant_broken = False
        broken_invariant_name = ""

        # If forge_output is a string, attempt JSON parsing first
        parsed_json: Optional[Dict[str, Any]] = None
        raw_text = ""
        if isinstance(forge_output, dict):
            parsed_json = forge_output
            raw_text = json.dumps(forge_output, indent=2)
        elif isinstance(forge_output, str):
            raw_text = forge_output.strip()
            if raw_text.startswith("{") and raw_text.endswith("}"):
                try:
                    parsed_json = json.loads(raw_text)
                except Exception:
                    parsed_json = None

        # 1. Extract from JSON structure if available
        if parsed_json:
            test_results = {}
            if "test_results" in parsed_json:
                test_results = parsed_json["test_results"]
            else:
                # Search nested keys for test_results
                for k, v in parsed_json.items():
                    if isinstance(v, dict) and "test_results" in v:
                        test_results.update(v["test_results"])
                    elif isinstance(v, dict) and "success" in v:
                        test_results[k] = v

            for test_name, res in test_results.items():
                if isinstance(res, dict):
                    if not res.get("success", True):
                        invariant_broken = True
                        broken_invariant_name = test_name
                    if "counterexample" in res and res["counterexample"]:
                        ce = res["counterexample"]
                        if isinstance(ce, list):
                            counterexample.extend([str(c) for c in ce])
                        elif isinstance(ce, dict):
                            counterexample.extend([f"{k}: {v}" for k, v in ce.items()])
                        else:
                            counterexample.append(str(ce))
                    if "traces" in res and isinstance(res["traces"], list):
                        for t in res["traces"]:
                            if isinstance(t, dict):
                                calls.append({
                                    "step": len(calls) + 1,
                                    "caller": t.get("caller", "0xAttacker"),
                                    "target": t.get("target", "TargetContract"),
                                    "function": t.get("function", t.get("call_type", "call")),
                                    "args": t.get("args", []),
                                    "value": t.get("value", "0"),
                                    "success": t.get("success", True),
                                    "reverted": not t.get("success", True),
                                })
                            elif isinstance(t, str):
                                raw_trace_lines.append(t)

        # 2. Extract from raw text / trace tree if calls not fully parsed or text provided
        if raw_text:
            lines = raw_text.splitlines()
            for line in lines:
                cleaned = line.strip()
                # Trace call patterns: ├─ [gas] Target::function(args) or [FAIL] or [revert]
                if any(sym in line for sym in ["├─", "└─", "│", "[FAIL", "Counterexample", "::"]):
                    raw_trace_lines.append(line)
                
                # Match contract call: [gas] Target::func(args)
                call_match = re.search(r'\[(\d+)?\]\s+([A-Za-z0-9_]+)::([A-Za-z0-9_]+)\((.*?)\)(?:\s+\[(revert|failed)\])?', line)
                if call_match:
                    gas = call_match.group(1) or "0"
                    target = call_match.group(2)
                    func = call_match.group(3)
                    args_str = call_match.group(4)
                    is_rev = bool(call_match.group(5))
                    if is_rev:
                        reverted = True
                    calls.append({
                        "step": len(calls) + 1,
                        "gas": gas,
                        "target": target,
                        "function": func,
                        "args": [a.strip() for a in args_str.split(",") if a.strip()],
                        "reverted": is_rev
                    })

                # Match counterexample in text: Counterexample: [...]
                ce_match = re.search(r'Counterexample:\s*\[(.*?)\]', line, re.IGNORECASE)
                if ce_match:
                    items = [it.strip() for it in ce_match.group(1).split(",") if it.strip()]
                    counterexample.extend(items)

                if "[FAIL" in line or "assertion failed" in line.lower():
                    invariant_broken = True
                    if not broken_invariant_name:
                        inv_match = re.search(r'(invariant_[A-Za-z0-9_]+)', line)
                        if inv_match:
                            broken_invariant_name = inv_match.group(1)

        poc_steps = self.format_trace_to_poc_steps({
            "calls": calls,
            "counterexample": counterexample,
            "broken_invariant": broken_invariant_name,
            "invariant_broken": invariant_broken,
            "raw_trace": "\n".join(raw_trace_lines)
        })

        return {
            "calls": calls,
            "counterexample": counterexample,
            "poc_steps": poc_steps,
            "raw_trace": "\n".join(raw_trace_lines),
            "reverted": reverted or invariant_broken,
            "invariant_broken": invariant_broken,
            "broken_invariant": broken_invariant_name
        }

    def format_trace_to_poc_steps(self, trace_or_calls: Union[Dict[str, Any], List[Dict[str, Any]], str]) -> str:
        """
        Formats extracted call trace data or counterexample sequence into reproducible
        step-by-step markdown PoC attack steps.
        """
        calls: List[Dict[str, Any]] = []
        counterexample: List[str] = []
        broken_inv = ""
        
        if isinstance(trace_or_calls, dict):
            calls = trace_or_calls.get("calls", [])
            counterexample = trace_or_calls.get("counterexample", [])
            broken_inv = trace_or_calls.get("broken_invariant", "")
        elif isinstance(trace_or_calls, list):
            calls = trace_or_calls
        elif isinstance(trace_or_calls, str):
            res = self.extract_call_trace(trace_or_calls)
            calls = res.get("calls", [])
            counterexample = res.get("counterexample", [])
            broken_inv = res.get("broken_invariant", "")

        steps: List[str] = []
        steps.append("### Reproducible Proof of Concept (PoC) Attack Steps\n")
        steps.append("1. **Prank Environment Setup:** Initialize test actor / attacker address (`0xBAD...`) with initial token or native gas balances.")

        step_idx = 2
        if counterexample:
            steps.append(f"{step_idx}. **Execute Counterexample Action Sequence:**")
            for ce in counterexample:
                steps.append(f"   - Trigger `{ce}`")
            step_idx += 1

        if calls:
            for call in calls:
                target = call.get("target", "TargetContract")
                raw_func = call.get("function", "execute")
                args = call.get("args", [])
                
                # Clean function name if signature types are present with arguments
                if "(" in raw_func and args:
                    func_name = raw_func.split("(")[0]
                else:
                    func_name = raw_func

                args_str = ", ".join(str(a) for a in args) if args else ""
                call_repr = f"{target}.{func_name}({args_str})" if "(" not in func_name else f"{target}.{func_name}"
                
                status = " (🚨 Reverts as expected in exploit condition)" if call.get("reverted") else ""
                steps.append(f"{step_idx}. **Execute Call:** `{call_repr}`{status}")
                step_idx += 1
        elif not counterexample:
            steps.append(f"{step_idx}. **Execute Flashloan / Initial Deposit:** Supply initial capital or flashloan funds into the protocol.")
            step_idx += 1
            steps.append(f"{step_idx}. **Trigger Vulnerable State Transition:** Invoke target contract method manipulating internal state.")
            step_idx += 1
            steps.append(f"{step_idx}. **Exploit Extraction Callback:** Extract drained collateral or inflated shares to attacker address.")
            step_idx += 1

        if broken_inv:
            steps.append(f"{step_idx}. **Invariant Validation Check:** Assert state consistency invariant `{broken_inv}` fails, proving state violation.")
        else:
            steps.append(f"{step_idx}. **Invariant Validation Check:** Assert state consistency invariant fails, confirming funds extraction.")

        return "\n".join(steps)

    def run_invariant_test(
        self,
        test_contract: str = "GeneratedInvariantsTest",
        verbosity: str = "-vvv",
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Executes `forge test --match-contract <test_contract>` and captures trace output.
        """
        if not self.is_foundry_installed():
            return {
                "success": False,
                "error": "Foundry 'forge' not found in system PATH. Install with: curl -L https://foundry.paradigm.xyz | bash && foundryup",
                "simulated": True,
                "call_trace": "",
                "poc_steps": self.format_trace_to_poc_steps([])
            }

        cmd = [
            self.forge_bin,
            "test",
            "--match-contract", test_contract,
            verbosity,
            "--json"
        ]

        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            stdout = res.stdout or ""
            stderr = res.stderr or ""
            
            trace_data = self.extract_call_trace(stdout if stdout else stderr)

            return {
                "success": res.returncode == 0,
                "return_code": res.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "simulated": False,
                "call_trace": trace_data.get("raw_trace", ""),
                "poc_steps": trace_data.get("poc_steps", ""),
                "parsed_trace": trace_data
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Forge test execution timed out ({timeout_seconds}s limit exceeded).",
                "simulated": False,
                "timeout": True,
                "call_trace": "",
                "poc_steps": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "simulated": False,
                "call_trace": "",
                "poc_steps": ""
            }
