"""
Core data structures and models for the Ethereum Bug Bounty Multi-Agent Framework.
Built using standard dataclasses for zero-dependency portability.

v2.0: Added proof-level tracking, on-chain verification fields, and fork-test metadata.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"
    FALSE_POSITIVE = "False Positive"


class FindingStatus(str, Enum):
    HYPOTHESIS = "Hypothesis"
    CHALLENGED = "Challenged"
    VALIDATED = "Validated"
    REJECTED = "Rejected"


@dataclass
class SolidityFunction:
    name: str
    visibility: str = "public"            # public, external, internal, private
    state_mutability: str = "nonpayable"  # nonpayable, payable, view, pure
    modifiers: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    return_types: List[str] = field(default_factory=list)
    code: str = ""
    start_line: int = 1
    end_line: int = 1
    is_non_reentrant: bool = False
    has_access_control: bool = False
    has_unchecked_block: bool = False
    is_initializer: bool = False
    is_modified: bool = False
    is_guarded: bool = False              # nonReentrant or custom mutex (alias)


@dataclass
class SolidityContract:
    name: str
    kind: str = "contract"                # contract, interface, library, abstract
    inheritance: List[str] = field(default_factory=list)
    state_variables: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    functions: List[SolidityFunction] = field(default_factory=list)
    raw_code: str = ""
    start_line: int = 1
    end_line: int = 1
    is_non_reentrant: bool = False
    has_checked_math: bool = False
    is_ownable: bool = False
    has_initializer_lock: bool = False
    defense_tags: Dict[str, Any] = field(default_factory=dict)
    is_modified: bool = False


@dataclass
class ContractContext:
    file_path: str
    pragma_version: str = "^0.8.0"
    imports: List[str] = field(default_factory=list)
    contracts: List[SolidityContract] = field(default_factory=list)
    slither_findings: List[Dict[str, Any]] = field(default_factory=list)
    full_source: str = ""
    defense_tags: Dict[str, Any] = field(default_factory=dict)
    delta_metadata: Optional[Dict[str, Any]] = None
    address: Optional[str] = None
    chain_id: Optional[int] = None
    contract_name: Optional[str] = None
    # v2: On-chain verification context
    on_chain_tvl_usd: float = 0.0
    contract_balance_eth: float = 0.0
    protocol_name: Optional[str] = None
    bounty_program_url: Optional[str] = None
    bounty_max_usd: float = 0.0


@dataclass
class RedTeamHypothesis:
    id: str
    title: str
    target_contract: str
    target_function: Optional[str] = None
    severity: Severity = Severity.MEDIUM
    threat_vector: str = "Logic Inconsistency"
    swc_id: Optional[str] = None
    description: str = ""
    attack_preconditions: List[str] = field(default_factory=list)
    theoretical_attack_steps: List[str] = field(default_factory=list)
    impact: str = ""
    confidence: int = 7


@dataclass
class BlueTeamCritique:
    hypothesis_id: str
    status: FindingStatus = FindingStatus.VALIDATED
    counter_arguments: List[str] = field(default_factory=list)
    validated_severity: Severity = Severity.MEDIUM
    foundry_invariant_spec: Optional[str] = None
    remediation_patch: Optional[str] = None
    defense_mechanisms_present: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class TriagedFinding:
    id: str
    title: str
    contract_name: str
    function_name: Optional[str] = None
    threat_vector: str = "Logic"
    final_severity: Severity = Severity.MEDIUM
    status: FindingStatus = FindingStatus.VALIDATED
    red_team_analysis: RedTeamHypothesis = field(default_factory=lambda: RedTeamHypothesis(id="0", title="", target_contract=""))
    blue_team_defense: BlueTeamCritique = field(default_factory=lambda: BlueTeamCritique(hypothesis_id="0"))
    proof_of_concept_logic: Optional[str] = None
    recommended_mitigation: str = ""
    mitigation_diff: Optional[str] = None
    confidence_score: int = 0
    composite_score: int = 0
    bounty_estimate_usd: float = 0.0
    economic_feasibility: Optional[Dict[str, Any]] = None
    # v2: Proof-level tracking
    proof_level: str = "Theoretical"          # Theoretical | Static | Fork Reproduced | Mainnet Sim
    has_compilable_poc: bool = False
    forge_test_passed: bool = False
    fork_test_output: str = ""
    forge_test_command: str = ""
    # v2: On-chain metadata
    on_chain_tvl_usd: float = 0.0
    contract_balance_eth: float = 0.0


@dataclass
class AuditSession:
    target_file: str
    context: ContractContext
    red_hypotheses: List[RedTeamHypothesis] = field(default_factory=list)
    blue_critiques: List[BlueTeamCritique] = field(default_factory=list)
    triaged_findings: List[TriagedFinding] = field(default_factory=list)
    summary: str = ""
    # v2: Session-level metadata
    proof_level: str = "Theoretical"
    total_findings: int = 0
    validated_findings: int = 0
    rejected_findings: int = 0
    protocol_name: str = ""
    bounty_program_url: str = ""
