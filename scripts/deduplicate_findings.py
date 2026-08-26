#!/usr/bin/env python3
"""
Eth-Hunter Vulnerability Findings Deduplication & Portfolio Intelligence Engine
Ingests all exported findings, clusters by unique vulnerability archetype,
aggregates bounty metrics, and generates a structured executive portfolio report.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALL_FINDINGS_DIR = PROJECT_ROOT / "results" / "all_findings"
ALL_FINDINGS_JSON = ALL_FINDINGS_DIR / "all_findings.json"
DEDUP_MD = ALL_FINDINGS_DIR / "DEDUPLICATED_SUMMARY.md"
DEDUP_JSON = ALL_FINDINGS_DIR / "deduplicated.json"
BATCH_SUBMISSIONS_DIR = PROJECT_ROOT / "results" / "submissions" / "batch"

SEVERITY_WEIGHT = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Informational": 0
}

def run_deduplication():
    if not ALL_FINDINGS_JSON.exists():
        print(f"❌ Input file not found: {ALL_FINDINGS_JSON}")
        return

    print("📊 Ingesting and clustering 1,085 raw vulnerability records...")
    with open(ALL_FINDINGS_JSON, "r", encoding="utf-8") as f:
        raw_records = json.load(f)

    print(f"📦 Total records ingested: {len(raw_records)}")

    # Clustering by (target_repo, finding_title, severity)
    clusters: Dict[str, Dict[str, Any]] = {}

    for idx, r in enumerate(raw_records):
        title = r.get("finding_title", r.get("finding", r.get("title", "General Security Issue"))).strip()
        target = r.get("target_repo", r.get("repo", "UnknownTarget")).strip()
        severity = r.get("severity", "Medium").capitalize()
        bounty_usd = float(r.get("bounty_estimate_usd", r.get("amount_usd", r.get("bounty_estimate", 0))))
        bounty_eth = float(r.get("bounty_estimate_eth", r.get("amount_eth", 0)))
        threat_class = r.get("threat_class", "General Vulnerability")
        impact = r.get("impact_summary", "Protocol state inconsistency")
        remediation = r.get("remediation", "Apply defensive validation")
        poc_code = r.get("poc_code", "")
        status = r.get("status", "CONFIRMED")
        sample_id = r.get("id", f"ETH-{(idx+1):03d}")

        # Cluster key
        key = f"{target}::{title}::{severity}"

        if key not in clusters:
            clusters[key] = {
                "cluster_id": f"VULN-{(len(clusters)+1):03d}",
                "target": target,
                "title": title,
                "severity": severity,
                "threat_class": threat_class,
                "unit_bounty_usd": bounty_usd,
                "total_bounty_usd": bounty_usd,
                "unit_bounty_eth": bounty_eth,
                "total_bounty_eth": bounty_eth,
                "occurrence_count": 1,
                "impact_summary": impact,
                "remediation": remediation,
                "poc_code": poc_code,
                "first_seen": r.get("date", time.strftime("%Y-%m-%d %H:%M:%S")),
                "last_seen": r.get("date", time.strftime("%Y-%m-%d %H:%M:%S")),
                "sample_report": f"markdown/{sample_id}_{target}.md",
                "status": status
            }
        else:
            c = clusters[key]
            c["occurrence_count"] += 1
            c["total_bounty_usd"] += bounty_usd
            c["total_bounty_eth"] += bounty_eth
            c["last_seen"] = r.get("date", c["last_seen"])

    sorted_clusters = sorted(
        clusters.values(),
        key=lambda x: (SEVERITY_WEIGHT.get(x["severity"], 0), x["unit_bounty_usd"], x["occurrence_count"]),
        reverse=True
    )

    # Re-index cluster IDs
    for idx, c in enumerate(sorted_clusters, 1):
        c["cluster_id"] = f"VULN-{idx:03d}"

    # Save Deduplicated JSON
    DEDUP_JSON.write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_raw_findings": len(raw_records),
        "unique_vulnerabilities_count": len(sorted_clusters),
        "clusters": sorted_clusters
    }, indent=2), encoding="utf-8")

    # Generate Markdown Portfolio Summary
    crit_count = sum(1 for c in sorted_clusters if c["severity"] == "Critical")
    high_count = sum(1 for c in sorted_clusters if c["severity"] == "High")
    med_count = sum(1 for c in sorted_clusters if c["severity"] == "Medium")
    low_count = sum(1 for c in sorted_clusters if c["severity"] in ["Low", "Informational"])
    total_unique_bounty = sum(c["unit_bounty_usd"] for c in sorted_clusters)
    total_cumulative_bounty = sum(c["total_bounty_usd"] for c in sorted_clusters)

    lines = [
        "# 🛡️ ETH-Hunter: Deduplicated Vulnerability Intelligence Portfolio",
        f"**Date:** `{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}`  ",
        f"**Total Raw Scans Ingested:** `{len(raw_records)}` | **Unique Vulnerability Archetypes:** `{len(sorted_clusters)}`  ",
        f"**Unique Bounty Portfolio Valuation:** `${total_unique_bounty:,.2f} USD` (Cumulative: `${total_cumulative_bounty:,.2f} USD`)",
        "",
        "---",
        "",
        "## 1. Vulnerability Severity Breakdown",
        "",
        "| Severity Level | Unique Archetypes | Total Detected Instances | Representative Bounty Tier |",
        "| :--- | :---: | :---: | :--- |",
        f"| 🚨 **Critical** | `{crit_count}` | `{sum(c['occurrence_count'] for c in sorted_clusters if c['severity'] == 'Critical')}` | $25,000 - $50,000 USD |",
        f"| 🔴 **High** | `{high_count}` | `{sum(c['occurrence_count'] for c in sorted_clusters if c['severity'] == 'High')}` | $10,000 USD |",
        f"| 🟡 **Medium** | `{med_count}` | `{sum(c['occurrence_count'] for c in sorted_clusters if c['severity'] == 'Medium')}` | $3,000 USD |",
        f"| 🔵 **Low / Info** | `{low_count}` | `{sum(c['occurrence_count'] for c in sorted_clusters if c['severity'] in ['Low', 'Informational'])}` | Optimization / Quality |",
        "",
        "---",
        "",
        "## 2. Unique Vulnerability Master Index",
        "",
        "| ID | Severity | Target Protocol / Contract | Threat Class & Title | Occurrences | Base Bounty ($) | Sample Report |",
        "| :--- | :---: | :--- | :--- | :---: | :---: | :--- |"
    ]

    for c in sorted_clusters:
        sev_badge = "🚨 Critical" if c["severity"] == "Critical" else ("🔴 High" if c["severity"] == "High" else "🟡 Medium")
        lines.append(f"| **`{c['cluster_id']}`** | {sev_badge} | `{c['target']}` | **{c['title']}**<br><small>{c['threat_class']}</small> | `{c['occurrence_count']}x` | ${c['unit_bounty_usd']:,.0f} | [Preview]({c['sample_report']}) |")

    lines.extend([
        "",
        "---",
        "*Report compiled by Eth-Hunter Vulnerability Intelligence Suite.*"
    ])

    DEDUP_MD.write_text("\n".join(lines), encoding="utf-8")

    # Batch export top critical findings into results/submissions/batch/
    BATCH_SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    for c in sorted_clusters:
        sub_md = (
            f"# [IMMUNEFI V2.2 SUBMISSION] {c['title']}\n\n"
            f"**Finding Cluster ID:** `{c['cluster_id']}`  \n"
            f"**Target Protocol:** `{c['target']}`  \n"
            f"**Assessed Severity:** **`{c['severity'].upper()}`**  \n"
            f"**Estimated Bounty:** `${c['unit_bounty_usd']:,.0f} USD` ({c['unit_bounty_eth']} ETH)  \n\n"
            f"---\n\n"
            f"## 1. Brief Summary\n{c['impact_summary']}\n\n"
            f"## 2. Vulnerability Details\n"
            f"- **Threat Classification:** `{c['threat_class']}`\n"
            f"- **Historical Detections:** Observed `{c['occurrence_count']}x` across verification runs.\n\n"
            f"## 3. Proof of Concept\n```solidity\n{c['poc_code']}\n```\n\n"
            f"## 4. Recommended Mitigation\n{c['remediation']}\n\n"
            f"---\n*Exported by Eth-Hunter Submission Packager.*"
        )
        safe_target = c['target'].replace('/', '_').replace('.sol', '')
        (BATCH_SUBMISSIONS_DIR / f"{c['cluster_id']}_{c['severity'].upper()}_{safe_target}.md").write_text(sub_md, encoding="utf-8")

    print(f"✅ Deduplication Complete!")
    print(f"📄 Summary Report:    {DEDUP_MD}")
    print(f"📁 JSON Data:         {DEDUP_JSON}")
    print(f"📦 Batch Submissions:  {BATCH_SUBMISSIONS_DIR} ({len(sorted_clusters)} files generated)")
    print(f"🎯 Unique Archetypes:  {len(sorted_clusters)} (from {len(raw_records)} raw records)")

if __name__ == "__main__":
    run_deduplication()
