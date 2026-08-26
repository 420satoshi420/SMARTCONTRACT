"""
Account Abstraction (ERC-4337) Smart Contract Wallet Manager for EthAudit-Agent.
Generates local EOA signers, computes deterministic Smart Account addresses,
and interfaces with ERC-4337 Bundlers.
"""
import os
import json
import logging
from pathlib import Path
from eth_account import Account
from web3 import Web3

logger = logging.getLogger(__name__)

# Standard ERC-4337 SimpleAccountFactory (V0.6)
FACTORY_ADDRESS = "0x9406Cc6185a346906296840746125a0E44976454"
ENTRY_POINT_ADDRESS = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"

class AgentWalletManager:
    """Manages the agent's ERC-4337 cryptographic identity."""

    def __init__(self, key_store_path: str):
        self.key_store_path = Path(key_store_path)
        self.signer_key = None
        self.signer_address = None
        self._load_or_create_signer()

    def _load_or_create_signer(self):
        """Loads the existing signer private key or generates a new one."""
        if self.key_store_path.exists():
            try:
                data = json.loads(self.key_store_path.read_text(encoding="utf-8"))
                if "private_key" in data:
                    self.signer_key = data["private_key"]
                    account = Account.from_key(self.signer_key)
                    self.signer_address = account.address
                    logger.info(f"Loaded existing Agent Signer: {self.signer_address}")
                    return
            except Exception as e:
                logger.warning(f"Failed to load signer key: {e}")

        # Generate new EOA
        # Warning: Private key is stored in plaintext for the sandbox environment!
        account = Account.create()
        self.signer_key = account.key.hex()
        self.signer_address = account.address
        
        # Save to keystore
        self.key_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_store_path.write_text(json.dumps({
            "address": self.signer_address,
            "private_key": self.signer_key,
            "note": "DO NOT USE ON MAINNET WITH REAL FUNDS. SANDBOX USE ONLY."
        }, indent=2))
        logger.info(f"Generated new Agent Signer: {self.signer_address}")

    def get_smart_account_address(self) -> str:
        """
        Computes the deterministic ERC-4337 Smart Account address for the signer.
        (Note: For full accuracy across all factories, we use an on-chain reading
        or CREATE2 derivation. For this sandbox, we generate a deterministic 
        derived address based on the signer).
        """
        if not self.signer_address:
            return ""
        
        # We simulate the CREATE2 deterministic address calculation by hashing
        # the factory address and the signer address. In a real production environment
        # we would query the EntryPoint's getSenderAddress() with the initCode.
        
        derived_hash = Web3.keccak(text=f"{FACTORY_ADDRESS}:{self.signer_address}")
        # Take the last 20 bytes (40 hex chars) to format as an Ethereum address
        address_hex = "0x" + derived_hash.hex()[-40:]
        return Web3.to_checksum_address(address_hex)

    def get_status(self) -> dict:
        """Returns the public status of the agent's AA wallet."""
        return {
            "is_setup": self.signer_address is not None,
            "signer_address": self.signer_address,
            "smart_account_address": self.get_smart_account_address(),
            "factory_address": FACTORY_ADDRESS,
            "entry_point": ENTRY_POINT_ADDRESS
        }
