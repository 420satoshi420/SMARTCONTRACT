"""
Solidity contract parser and static analysis context builder.
Supports single files, multi-file projects, directory scanning, and Etherscan source ingestion.
Extracts 1-indexed line spans and classifies defense attributes (nonReentrant, Ownable, checked math, etc.).
"""
import re
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from .context import (
    ContractContext,
    SolidityContract,
    SolidityFunction,
)
from .slither_runner import SlitherRunner

logger = logging.getLogger("SolidityParser")


class SolidityParser:
    """Parses Solidity source code into structured representations for Agent analysis."""

    PRAGMA_REGEX = re.compile(r"pragma\s+solidity\s+([^;]+);")
    IMPORT_REGEX = re.compile(r"import\s+[^;]+;")

    # Contract declaration regex (contracts, abstract contracts, interfaces, libraries)
    CONTRACT_REGEX = re.compile(
        r"(contract|abstract\s+contract|interface|library)\s+([A-Za-z0-9_]+)(?:\s+is\s+([^{]+))?\s*\{",
        re.MULTILINE
    )

    # Function declaration regex: function name, constructor, receive, fallback
    FUNCTION_REGEX = re.compile(
        r"(?:function\s+([A-Za-z0-9_]+)|(constructor)|(receive)|(fallback))\s*\((.*?)\)\s*([^{;]*)(?:\{|;)",
        re.DOTALL
    )

    # Modifier declaration regex
    MODIFIER_REGEX = re.compile(
        r"modifier\s+([A-Za-z0-9_]+)\s*(?:\((.*?)\))?\s*\{",
        re.DOTALL
    )

    # Known Solidity qualifiers that are not custom modifiers
    KNOWN_QUALIFIERS = {
        "public", "external", "internal", "private",
        "view", "pure", "payable", "nonpayable",
        "virtual", "override",
    }

    @classmethod
    def parse(
        cls,
        file_path: Union[str, Path],
        slither_json_path: Optional[str] = None,
        auto_slither: bool = False
    ) -> ContractContext:
        """Alias for parse_file for convenience."""
        return cls.parse_file(file_path, slither_json_path, auto_slither)

    @classmethod
    def parse_file(
        cls,
        file_path: Union[str, Path],
        slither_json_path: Optional[str] = None,
        auto_slither: bool = False
    ) -> ContractContext:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Solidity source file not found: {file_path}")

        source_code = path.read_text(encoding="utf-8")

        slither_findings = []
        if slither_json_path and Path(slither_json_path).exists():
            try:
                with open(slither_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    slither_findings = data.get("results", {}).get("detectors", [])
            except Exception:
                slither_findings = []
        elif auto_slither:
            slither_findings = SlitherRunner.run_analysis(str(path))

        return cls.parse_source(
            source_code=source_code,
            file_path=str(path),
            slither_findings=slither_findings
        )

    @classmethod
    def parse_directory(
        cls,
        dir_path: Union[str, Path],
        exclude_patterns: Optional[List[str]] = None,
        slither_json_path: Optional[str] = None,
        auto_slither: bool = False
    ) -> ContractContext:
        """Recursively parses all .sol files in a project/directory into a unified ContractContext."""
        root = Path(dir_path).resolve()
        if not root.exists() or not root.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        excludes = exclude_patterns or ["node_modules", ".git", "lib", "artifacts", "cache", ".agents"]

        sol_files = []
        for p in root.rglob("*.sol"):
            # Check exclusions against path parts
            if any(ex in p.parts for ex in excludes):
                continue
            sol_files.append(p)

        all_imports = set()
        all_contracts: List[SolidityContract] = []
        full_sources = []
        pragma_version = "unknown"

        for f in sol_files:
            try:
                content = f.read_text(encoding="utf-8")
                ctx = cls.parse_source(content, file_path=str(f))
                all_imports.update(ctx.imports)
                all_contracts.extend(ctx.contracts)
                if pragma_version == "unknown" and ctx.pragma_version != "unknown":
                    pragma_version = ctx.pragma_version
                full_sources.append(f"// FILE: {f.name}\n" + content)
            except Exception as e:
                logger.debug(f"Skipping unparseable file {f}: {e}")
                continue

        slither_findings = []
        if slither_json_path and Path(slither_json_path).exists():
            try:
                with open(slither_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    slither_findings = data.get("results", {}).get("detectors", [])
            except Exception:
                slither_findings = []
        elif auto_slither:
            slither_findings = SlitherRunner.run_analysis(str(root))

        defense_tags_map = {c.name: c.defense_tags for c in all_contracts}

        return ContractContext(
            file_path=str(root),
            pragma_version=pragma_version,
            imports=list(all_imports),
            contracts=all_contracts,
            slither_findings=slither_findings,
            full_source="\n\n".join(full_sources),
            defense_tags=defense_tags_map,
        )

    @classmethod
    def parse_source(
        cls,
        source_code: str,
        file_path: str = "InMemory.sol",
        slither_findings: Optional[List[Dict[str, Any]]] = None,
        delta_metadata: Optional[Dict[str, Any]] = None,
    ) -> ContractContext:
        """Parses a Solidity source string into a ContractContext with exact line spans & defense tags."""
        pragma_match = cls.PRAGMA_REGEX.search(source_code)
        pragma_version = pragma_match.group(1).strip() if pragma_match else "unknown"

        # Extract Imports
        imports = [m.group(0).strip() for m in cls.IMPORT_REGEX.finditer(source_code)]

        # Extract Contracts
        contracts: List[SolidityContract] = []
        contract_matches = list(cls.CONTRACT_REGEX.finditer(source_code))

        for match in contract_matches:
            kind_str = match.group(1).strip()
            name = match.group(2).strip()
            inheritance_str = match.group(3)
            inheritance = [inh.strip() for inh in inheritance_str.split(",")] if inheritance_str else []

            contract_start_idx = match.start()
            body, raw_code, body_start_idx, contract_end_idx = cls._extract_block_with_indices(
                source_code, contract_start_idx
            )

            # Compute exact 1-indexed contract line span
            start_line = source_code.count("\n", 0, contract_start_idx) + 1
            end_line = source_code.count("\n", 0, contract_end_idx) + 1

            functions = cls._extract_functions(body, source_code, body_start_idx)
            modifiers = cls._extract_modifiers(body)
            state_vars = cls._extract_state_variables(body)

            # Classify contract defense attributes
            has_checked_math = cls._check_checked_math(pragma_version, inheritance, raw_code)
            is_non_reentrant = cls._check_non_reentrant(inheritance, modifiers, state_vars, raw_code, functions)
            is_ownable = cls._check_ownable(inheritance, modifiers, state_vars, raw_code, functions)
            has_initializer_lock = cls._check_initializer_lock(inheritance, functions, raw_code)

            defense_tags = {
                "has_checked_math": has_checked_math,
                "is_non_reentrant": is_non_reentrant,
                "is_ownable": is_ownable,
                "has_initializer_lock": has_initializer_lock,
                "is_pausable": any("pausable" in inh.lower() for inh in inheritance) or "whenNotPaused" in raw_code,
                "has_erc20_safe_transfer": "SafeERC20" in source_code or "safeTransfer" in raw_code,
                "has_oracle_twap": "observe" in raw_code or "latestRoundData" in raw_code,
                "uses_spot_reserves": "getReserves" in raw_code or "slot0" in raw_code,
            }

            contracts.append(
                SolidityContract(
                    name=name,
                    kind=kind_str,
                    inheritance=inheritance,
                    state_variables=state_vars,
                    modifiers=modifiers,
                    functions=functions,
                    raw_code=raw_code,
                    start_line=start_line,
                    end_line=end_line,
                    is_non_reentrant=is_non_reentrant,
                    has_checked_math=has_checked_math,
                    is_ownable=is_ownable,
                    has_initializer_lock=has_initializer_lock,
                    defense_tags=defense_tags,
                )
            )

        defense_tags_map = {c.name: c.defense_tags for c in contracts}

        return ContractContext(
            file_path=file_path,
            pragma_version=pragma_version,
            imports=imports,
            contracts=contracts,
            slither_findings=slither_findings or [],
            full_source=source_code,
            defense_tags=defense_tags_map,
            delta_metadata=delta_metadata,
        )

    @classmethod
    def parse_etherscan_result(
        cls,
        contract_result: Any,
        slither_json_path: Optional[str] = None,
        auto_slither: bool = False,
    ) -> ContractContext:
        """Parses an EtherscanContractResult or fetched Path into a ContractContext."""
        # Handle Path or str directly
        if isinstance(contract_result, (str, Path)):
            p = Path(contract_result).resolve()
            if p.is_dir():
                return cls.parse_directory(p, slither_json_path=slither_json_path, auto_slither=auto_slither)
            else:
                return cls.parse_file(p, slither_json_path=slither_json_path, auto_slither=auto_slither)

        # Handle EtherscanContractResult object
        local_path = getattr(contract_result, "local_path", None)
        address = getattr(contract_result, "address", None)
        chain_id = getattr(contract_result, "chain_id", None)
        contract_name = getattr(contract_result, "contract_name", None)
        raw_source = getattr(contract_result, "raw_source", None)
        is_multi_file = getattr(contract_result, "is_multi_file", False)

        if is_multi_file and local_path and Path(local_path).is_dir() and Path(local_path) != Path(".") and Path(local_path) != Path.cwd():
            ctx = cls.parse_directory(local_path, slither_json_path=slither_json_path, auto_slither=auto_slither)
        elif local_path and Path(local_path).is_file():
            ctx = cls.parse_file(local_path, slither_json_path=slither_json_path, auto_slither=auto_slither)
        elif raw_source:
            ctx = cls.parse_source(raw_source, file_path=f"{contract_name or 'Contract'}.sol")
        elif local_path and Path(local_path).is_dir() and Path(local_path) != Path(".") and Path(local_path) != Path.cwd():
            ctx = cls.parse_directory(local_path, slither_json_path=slither_json_path, auto_slither=auto_slither)
        else:
            ctx = cls.parse_source("// Empty contract stub", file_path="Unknown.sol")

        ctx.address = address
        ctx.chain_id = chain_id
        ctx.contract_name = contract_name
        return ctx

    @classmethod
    def _extract_block(cls, source: str, start_index: int) -> Tuple[str, str]:
        """Finds matching braces for a block starting at or after start_index."""
        body, raw, _, _ = cls._extract_block_with_indices(source, start_index)
        return body, raw

    @classmethod
    def _extract_block_with_indices(cls, source: str, start_index: int) -> Tuple[str, str, int, int]:
        """Finds matching braces for a block and returns (body, full_code, body_start_idx, end_idx)."""
        first_brace = source.find("{", start_index)
        if first_brace == -1:
            return "", source[start_index:], start_index, len(source)

        depth = 0
        end_brace = -1
        in_string = False
        in_line_comment = False
        in_block_comment = False
        quote_char = ""

        i = first_brace
        while i < len(source):
            ch = source[i]
            next_ch = source[i + 1] if i + 1 < len(source) else ""

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
            elif in_block_comment:
                if ch == "*" and next_ch == "/":
                    in_block_comment = False
                    i += 1
            elif in_string:
                if ch == quote_char and (i == 0 or source[i - 1] != "\\"):
                    in_string = False
            else:
                if ch == "/" and next_ch == "/":
                    in_line_comment = True
                    i += 1
                elif ch == "/" and next_ch == "*":
                    in_block_comment = True
                    i += 1
                elif ch in ('"', "'"):
                    in_string = True
                    quote_char = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_brace = i
                        break
            i += 1

        if end_brace == -1:
            end_brace = len(source) - 1

        body = source[first_brace + 1:end_brace]
        full_code = source[start_index:end_brace + 1]
        return body, full_code, first_brace + 1, end_brace + 1

    @classmethod
    def _extract_functions(
        cls,
        contract_body: str,
        full_source: str,
        body_start_in_source: int
    ) -> List[SolidityFunction]:
        """Extracts functions with modifiers, parameters, return types, and exact 1-indexed line spans."""
        functions: List[SolidityFunction] = []

        for match in cls.FUNCTION_REGEX.finditer(contract_body):
            f_name = match.group(1) or match.group(2) or match.group(3) or match.group(4) or "anonymous"
            params_str = match.group(5).strip() if match.group(5) else ""
            qualifiers_str = match.group(6).strip() if match.group(6) else ""

            params = [p.strip() for p in params_str.split(",") if p.strip()]

            # Determine visibility
            visibility = "public"
            for v in ["public", "external", "internal", "private"]:
                if re.search(r"\b" + v + r"\b", qualifiers_str):
                    visibility = v
                    break

            # Determine mutability
            mutability = "nonpayable"
            for m in ["view", "pure", "payable"]:
                if re.search(r"\b" + m + r"\b", qualifiers_str):
                    mutability = m
                    break

            # Extract return types: returns (...)
            return_types: List[str] = []
            ret_match = re.search(r"returns\s*\((.*?)\)", qualifiers_str, re.DOTALL)
            if ret_match:
                ret_str = ret_match.group(1).strip()
                return_types = [r.strip() for r in ret_str.split(",") if r.strip()]

            # Extract custom function modifiers
            # Strip returns clause, then split by whitespace or arguments
            cleaned_qual = re.sub(r"returns\s*\(.*?\)", "", qualifiers_str, flags=re.DOTALL).strip()
            # Tokenize modifier invocations: modName or modName(args)
            mod_tokens = re.findall(r"\b[A-Za-z0-9_]+(?:\s*\([^)]*\))?", cleaned_qual)
            func_modifiers: List[str] = []
            for token in mod_tokens:
                base_token = re.split(r"[\s(]", token)[0]
                if base_token not in cls.KNOWN_QUALIFIERS and base_token != "":
                    func_modifiers.append(token.strip())

            # Find function body and exact start/end indices in full_source
            func_decl_offset = body_start_in_source + match.start()
            _, full_func_code, _, func_end_idx = cls._extract_block_with_indices(
                full_source, func_decl_offset
            )

            start_line = full_source.count("\n", 0, func_decl_offset) + 1
            end_line = full_source.count("\n", 0, func_end_idx) + 1

            # Function defense properties
            mods_lower = [m.lower() for m in func_modifiers]
            is_non_reentrant = any("nonreentrant" in m or "lock" in m or "noreentrancy" in m for m in mods_lower)
            has_access_control = (
                any("onlyowner" in m or "onlyrole" in m or "onlyadmin" in m or "auth" in m for m in mods_lower)
                or "require(msg.sender ==" in full_func_code
                or "_checkOwner()" in full_func_code
            )
            has_unchecked_block = bool(re.search(r"unchecked\s*\{", full_func_code))
            is_initializer = (
                bool(re.match(r"^(initialize|init|setUp)", f_name, re.IGNORECASE))
                and any("initializer" in m or "reinitializer" in m for m in mods_lower)
            )

            functions.append(
                SolidityFunction(
                    name=f_name,
                    visibility=visibility,
                    state_mutability=mutability,
                    modifiers=func_modifiers,
                    parameters=params,
                    return_types=return_types,
                    code=full_func_code.strip(),
                    start_line=start_line,
                    end_line=end_line,
                    is_non_reentrant=is_non_reentrant,
                    has_access_control=has_access_control,
                    has_unchecked_block=has_unchecked_block,
                    is_initializer=is_initializer,
                    is_guarded=is_non_reentrant or has_access_control,
                )
            )

        return functions

    @classmethod
    def _extract_modifiers(cls, contract_body: str) -> List[str]:
        modifiers = []
        for match in cls.MODIFIER_REGEX.finditer(contract_body):
            modifiers.append(match.group(1).strip())
        return modifiers

    @classmethod
    def _extract_state_variables(cls, contract_body: str) -> List[str]:
        vars_list = []
        lines = contract_body.split("\n")
        var_types = ["uint", "int", "address", "bool", "bytes", "string", "mapping", "IERC20", "IERC721", "IERC1155"]
        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("//") or trimmed.startswith("/*") or trimmed.startswith("*"):
                continue
            if any(trimmed.startswith(vt) for vt in var_types) and "(" not in trimmed and trimmed.endswith(";"):
                vars_list.append(trimmed)
        return vars_list

    @classmethod
    def _check_checked_math(cls, pragma_version: str, inheritance: List[str], raw_code: str) -> bool:
        """Solidity 0.8+ has built-in checked arithmetic; <0.8 checks SafeMath."""
        if any(ver in pragma_version for ver in ["0.8", "0.9", ">=0.8", "^0.8", ">0.7"]):
            return True
        inh_lower = [i.lower() for i in inheritance]
        if any("safemath" in i for i in inh_lower) or "using SafeMath for" in raw_code:
            return True
        return False

    @classmethod
    def _check_non_reentrant(
        cls,
        inheritance: List[str],
        modifiers: List[str],
        state_vars: List[str],
        raw_code: str,
        functions: List[SolidityFunction],
    ) -> bool:
        """Checks for ReentrancyGuard inheritance, nonReentrant modifier, or mutex state vars."""
        inh_lower = [i.lower() for i in inheritance]
        if any("reentrancyguard" in i or "reentrancylock" in i for i in inh_lower):
            return True
        mod_lower = [m.lower() for m in modifiers]
        if any("nonreentrant" in m or "lock" in m or "noreentrancy" in m or "mutex" in m for m in mod_lower):
            return True
        # Check functions for nonReentrant modifier
        if any(f.is_non_reentrant for f in functions):
            return True
        # Check mutex state variables
        sv_lower = " ".join(state_vars).lower()
        if "_status" in sv_lower or "_locked" in sv_lower or "entered" in sv_lower or "reentrancylock" in sv_lower:
            return True
        return False

    @classmethod
    def _check_ownable(
        cls,
        inheritance: List[str],
        modifiers: List[str],
        state_vars: List[str],
        raw_code: str,
        functions: List[SolidityFunction],
    ) -> bool:
        """Checks for Ownable, AccessControl, Auth inheritance or access modifiers."""
        inh_lower = [i.lower() for i in inheritance]
        if any("ownable" in i or "accesscontrol" in i or "auth" in i or "roles" in i for i in inh_lower):
            return True
        mod_lower = [m.lower() for m in modifiers]
        if any("onlyowner" in m or "onlyrole" in m or "onlyadmin" in m or "auth" in m or "requiresauth" in m for m in mod_lower):
            return True
        if any(f.has_access_control for f in functions):
            return True
        sv_lower = " ".join(state_vars).lower()
        if "owner" in sv_lower or "admin" in sv_lower:
            return True
        return False

    @classmethod
    def _check_initializer_lock(
        cls,
        inheritance: List[str],
        functions: List[SolidityFunction],
        raw_code: str,
    ) -> bool:
        """Checks for Initializable inheritance and _disableInitializers lock."""
        if "_disableInitializers()" in raw_code or "_lockInitializers()" in raw_code:
            return True
        inh_lower = [i.lower() for i in inheritance]
        if any("initializable" in i for i in inh_lower):
            # If any function is an initializer with modifier
            return any(f.is_initializer for f in functions)
        return False
