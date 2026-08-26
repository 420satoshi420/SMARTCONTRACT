#!/usr/bin/env python3
"""
Automated MCP Setup and Configurator for ETH Hunter & Multi-Agent Workflows.
Configures Antigravity IDE, Claude Desktop, Cursor, and custom MCP clients.
"""
import sys
import os
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Default ETH Hunter MCP Server Definition
REPO_DIR = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = str(REPO_DIR / "mcp_server.py")
PYTHON_EXEC = sys.executable

ETH_HUNTER_CONFIG = {
    "command": PYTHON_EXEC,
    "args": [SERVER_SCRIPT],
    "env": {
        "PYTHONPATH": str(REPO_DIR)
    }
}

# Base set of default multi-purpose MCP tools provided by the user
DEFAULT_SERVERS: Dict[str, Any] = {
    "eth-hunter-mcp": ETH_HUNTER_CONFIG,
    "chrome-devtools-mcp": {
        "command": "npx",
        "args": ["-y", "chrome-devtools-mcp@latest"]
    },
    "google-managed-service-for-apache-kafka": {
        "serverUrl": "https://managedkafka.googleapis.com/mcp",
        "authProviderType": "google_credentials"
    },
    "genkit-mcp-server": {
        "command": "npx",
        "args": [
            "-y",
            "genkit-cli@^1.28.0",
            "mcp",
            "--explicitProjectRoot",
            "--no-update-notification",
            "--non-interactive"
        ]
    },
    "gopls-mcp-server": {
        "command": "go",
        "args": ["run", "golang.org/x/tools/gopls@latest", "mcp"]
    },
    "google-kubernetes-engine": {
        "serverUrl": "https://container.googleapis.com/mcp",
        "authProviderType": "google_credentials"
    },
    "google-cloud-spanner": {
        "serverUrl": "https://spanner.googleapis.com/mcp",
        "authProviderType": "google_credentials"
    },
    "google-cloud-apigee-api-hub": {
        "serverUrl": "https://apihub.googleapis.com/mcp",
        "authProviderType": "google_credentials"
    },
    "knowledge-catalog": {
        "serverUrl": "https://dataplex.googleapis.com/mcp",
        "authProviderType": "google_credentials"
    },
    "sequential-thinking": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
}

TARGET_LOCATIONS = {
    "antigravity": Path.home() / ".gemini" / "config" / "mcp_config.json",
    "claude_desktop": Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    "cursor_global": Path.home() / ".cursor" / "mcp.json",
    "cursor_project": REPO_DIR / ".cursor" / "mcp.json",
    "project_local": REPO_DIR / "mcp_config.json",
}


def test_mcp_server() -> bool:
    """Run a quick stdio sanity test on the ETH Hunter MCP Server."""
    print("🔍 Testing ETH Hunter MCP Server...")
    try:
        proc = subprocess.Popen(
            [PYTHON_EXEC, SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
        stdout, _ = proc.communicate(input=req, timeout=5)
        res = json.loads(stdout)
        tools = res.get("result", {}).get("tools", [])
        tool_names = [t.get("name") for t in tools]
        print(f"  ✅ MCP Server Healthy! Found {len(tools)} tools: {', '.join(tool_names)}")
        return True
    except Exception as e:
        print(f"  ❌ MCP Server Test Failed: {e}")
        return False


def merge_and_save_config(config_path: Path, new_servers: Dict[str, Any], dry_run: bool = False) -> bool:
    """Merge new MCP servers into target config file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing_data: Dict[str, Any] = {"mcpServers": {}}

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f) or {}
                if "mcpServers" not in existing_data:
                    existing_data["mcpServers"] = {}
        except Exception as e:
            print(f"  ⚠️ Warning reading {config_path}: {e}. Initializing clean structure.")
            existing_data = {"mcpServers": {}}

    # Merge servers
    added = []
    updated = []
    for s_name, s_conf in new_servers.items():
        if s_name not in existing_data["mcpServers"]:
            existing_data["mcpServers"][s_name] = s_conf
            added.append(s_name)
        else:
            existing_data["mcpServers"][s_name] = s_conf
            updated.append(s_name)

    print(f"📍 Target: {config_path}")
    print(f"   ➕ Added: {len(added)} | 🔄 Updated: {len(updated)} | 📊 Total: {len(existing_data['mcpServers'])}")

    if dry_run:
        print("   (Dry-run: skipping disk write)")
        return True

    # Backup
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        try:
            shutil.copy2(config_path, backup_path)
            print(f"   💾 Backup created: {backup_path.name}")
        except Exception:
            pass

    # Save
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)
    print(f"   ✨ Successfully written!")
    return True


def setup_antigravity_schemas(dry_run: bool = False):
    """Generate Antigravity MCP tool schema directory."""
    mcp_dir = Path.home() / ".gemini" / "antigravity" / "mcp" / "eth-hunter-mcp"
    if dry_run:
        print(f"📍 Antigravity Schema Target: {mcp_dir} (dry-run)")
        return

    mcp_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "audit_solidity_contract.json": {
            "name": "audit_solidity_contract",
            "description": "Run Red Team/Blue Team adversarial security audit on a Solidity contract or directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to Solidity file or directory"},
                    "preset": {"type": "string", "enum": ["immunefi", "code4rena", "sherlock"], "default": "immunefi"},
                    "provider": {"type": "string", "default": "mock"},
                    "model": {"type": "string", "description": "LLM model name"}
                },
                "required": ["path"]
            }
        },
        "audit_onchain_contract.json": {
            "name": "audit_onchain_contract",
            "description": "Fetch verified Solidity source code from Etherscan V2 / multichain block explorers and run Red Team / Blue Team adversarial audit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Contract address (0x...) or block explorer URL"},
                    "chain_id": {"type": "integer", "default": 1},
                    "api_key": {"type": "string", "description": "Optional Etherscan API key"},
                    "preset": {"type": "string", "enum": ["immunefi", "code4rena", "sherlock"], "default": "immunefi"},
                    "provider": {"type": "string", "default": "mock"}
                },
                "required": ["target"]
            }
        },
        "get_evm_taxonomy.json": {
            "name": "get_evm_taxonomy",
            "description": "Retrieve comprehensive attack vectors, threat models, and defensive invariant mitigations for known EVM/DeFi vulnerability patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "enum": ["erc4626", "uniswapv4", "signatures", "reentrancy", "oracle", "erc20", "all"], "default": "all"}
                }
            }
        },
        "generate_foundry_invariant_suite.json": {
            "name": "generate_foundry_invariant_suite",
            "description": "Generate Foundry/Forge property-based invariant test suite (Invariants.t.sol) and actor handler (Handler.sol) for target contract.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to Solidity contract file (.sol)"},
                    "provider": {"type": "string", "default": "mock"}
                },
                "required": ["path"]
            }
        }
    }

    for filename, content in schemas.items():
        schema_file = mcp_dir / filename
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2)
    print(f"✨ Antigravity Tool Schemas generated at: {mcp_dir}")


def main():
    parser = argparse.ArgumentParser(description="Automated MCP Setup for ETH Hunter")
    parser.add_argument("--all", action="store_true", default=True, help="Configure all supported MCP hosts")
    parser.add_argument("--antigravity", action="store_true", help="Configure Antigravity global MCP")
    parser.add_argument("--claude", action="store_true", help="Configure Claude Desktop MCP")
    parser.add_argument("--cursor", action="store_true", help="Configure Cursor MCP")
    parser.add_argument("--project", action="store_true", help="Configure local project MCP")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    parser.add_argument("--no-test", action="store_true", help="Skip MCP server validation test")
    parser.add_argument("--custom-json", type=str, help="Path to custom JSON file with mcpServers to merge")

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print(" 🚀 ETH HUNTER: Model Context Protocol (MCP) Automated Configurator")
    print("=" * 70 + "\n")

    servers_to_add = dict(DEFAULT_SERVERS)

    if args.custom_json:
        try:
            with open(args.custom_json, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
                custom_servers = custom_data.get("mcpServers", custom_data)
                servers_to_add.update(custom_servers)
                print(f"📦 Ingested custom servers from: {args.custom_json}")
        except Exception as e:
            print(f"❌ Failed to load custom JSON: {e}")

    # Sanity check
    if not args.no_test:
        if not test_mcp_server():
            print("⚠️ MCP Server test reported an issue. Continuing setup...\n")
        print()

    # Determine targets
    specific_flags = [args.antigravity, args.claude, args.cursor, args.project]
    is_specific = any(specific_flags)

    if is_specific:
        if args.antigravity:
            merge_and_save_config(TARGET_LOCATIONS["antigravity"], servers_to_add, args.dry_run)
            setup_antigravity_schemas(args.dry_run)
        if args.claude:
            merge_and_save_config(TARGET_LOCATIONS["claude_desktop"], servers_to_add, args.dry_run)
        if args.cursor:
            merge_and_save_config(TARGET_LOCATIONS["cursor_global"], servers_to_add, args.dry_run)
            merge_and_save_config(TARGET_LOCATIONS["cursor_project"], servers_to_add, args.dry_run)
        if args.project:
            merge_and_save_config(TARGET_LOCATIONS["project_local"], servers_to_add, args.dry_run)
    else:
        # Default: configure Antigravity, Claude Desktop, Cursor, and Project
        merge_and_save_config(TARGET_LOCATIONS["antigravity"], servers_to_add, args.dry_run)
        setup_antigravity_schemas(args.dry_run)
        merge_and_save_config(TARGET_LOCATIONS["claude_desktop"], servers_to_add, args.dry_run)
        merge_and_save_config(TARGET_LOCATIONS["cursor_global"], servers_to_add, args.dry_run)
        merge_and_save_config(TARGET_LOCATIONS["cursor_project"], servers_to_add, args.dry_run)
        merge_and_save_config(TARGET_LOCATIONS["project_local"], servers_to_add, args.dry_run)

    print("\n" + "=" * 70)
    print(" ✅ MCP Configuration Successfully Completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
