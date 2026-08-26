#!/usr/bin/env python3
"""
ETH Hunter Brain Unified MCP Server
Written by Meta & Sirin (420satoshi420)
Provides tools for Antigravity IDE, Claude Desktop, and CLI agentic reasoning.
"""
import sys, json, os, glob
from pathlib import Path

BRAIN_DIR = Path(__file__).resolve().parent

def list_brain_files():
    files = []
    for p in BRAIN_DIR.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            files.append(str(p.relative_to(BRAIN_DIR)))
    return {"files": sorted(files), "total_count": len(files)}

def get_rules(rule_name="all"):
    rules_dir = BRAIN_DIR / "rules"
    if rule_name == "all":
        res = {}
        for f in rules_dir.glob("*.md"):
            res[f.stem] = f.read_text(encoding="utf-8")
        return res
    target = rules_dir / f"{rule_name}.md"
    if target.exists():
        return {rule_name: target.read_text(encoding="utf-8")}
    return {"error": f"Rule {rule_name} not found"}

def get_knowledge(category="all"):
    k_dir = BRAIN_DIR / "knowledge"
    res = {}
    for p in k_dir.rglob("*.md"):
        key = str(p.relative_to(k_dir))
        if category == "all" or category in key:
            res[key] = p.read_text(encoding="utf-8")
    return res

def get_poc_template(name="reentrancy"):
    template_file = BRAIN_DIR / "templates" / "FOUNDRY_POC_TEMPLATES.sol"
    if template_file.exists():
        return {"template": template_file.read_text(encoding="utf-8")}
    return {"error": "PoC template file not found"}

def get_thresholds():
    cfg = BRAIN_DIR / "config" / "thresholds.json"
    if cfg.exists():
        return json.loads(cfg.read_text(encoding="utf-8"))
    return {"goal_usd": 2088}

def handle_request(req):
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {"name": "list_brain_files", "description": "Lists all rules, knowledge, and templates in ETH Hunter Brain"},
                    {"name": "get_rules", "description": "Fetches security rules and false positive filters"},
                    {"name": "get_knowledge", "description": "Fetches domain knowledge for reentrancy, access control, flashloans"},
                    {"name": "get_poc_template", "description": "Returns verified Foundry PoC exploit templates"},
                    {"name": "get_thresholds", "description": "Returns speed mode and bounty threshold settings ($2088 target)"}
                ]
            }
        }
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "list_brain_files":
            res = list_brain_files()
        elif name == "get_rules":
            res = get_rules(args.get("rule_name", "all"))
        elif name == "get_knowledge":
            res = get_knowledge(args.get("category", "all"))
        elif name == "get_poc_template":
            res = get_poc_template(args.get("name", "reentrancy"))
        elif name == "get_thresholds":
            res = get_thresholds()
        else:
            res = {"error": f"Unknown tool {name}"}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
        }
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("MCP Server Ready. Files in brain:", len(list_brain_files()["files"]))
        return
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
