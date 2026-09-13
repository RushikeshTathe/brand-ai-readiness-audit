import sys
import os
import json
import time

# Ensure skill script directories are in sys.path
sys.path.insert(0, os.path.join('skills', 'audit-orchestrator', 'scripts'))
sys.path.insert(0, os.path.join('skills', 'crawl-render-audit', 'scripts'))

try:
    from orchestrator import run_audit  # Adjust if orchestrator exports run_audit
except ImportError:
    from audit import audit_url as run_audit

def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_audit.py <URL> [output_file.json]")
        print("Example: python demo_audit.py https://docs.github.com demo_docs.json")
        sys.exit(1)

    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "audit_report.json"

    print("\n=======================================================")
    print("       AI READINESS AUDIT ORCHESTRATOR DEMO           ")
    print("=======================================================")
    print(f"Target URL : {url}")
    print(f"Output File: {output_file}")
    print("Running audit pipeline... Please wait.\n")

    start_time = time.time()
    
    # Run audit pipeline directly
    report = run_audit(url)

    # Save to JSON output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    elapsed = round(time.time() - start_time, 2)

    summary = report.get("summary", {})
    findings = report.get("findings", [])

    print("-------------------------------------------------------")
    print("                 AUDIT SUMMARY REPORT                  ")
    print("-------------------------------------------------------")
    print(f"Total Runtime    : {elapsed}s")
    print(f"Total Findings   : {summary.get('total_findings', 0)}")
    print(f"  - Critical     : {summary.get('critical', 0)}")
    print(f"  - High         : {summary.get('high', 0)}")
    print(f"  - Medium       : {summary.get('medium', 0)}")
    print(f"  - Low          : {summary.get('low', 0)}")
    print(f"  - Info         : {summary.get('info', 0)}")
    print("-------------------------------------------------------")
    print("FINDINGS BREAKDOWN:")

    if not findings:
        print("  [?] No accessibility or brand readiness findings detected.")
    else:
        for idx, f in enumerate(findings, 1):
            sev = str(f.get('severity', 'info')).upper()
            title = f.get('title', 'No Title')
            fid = f.get('id', 'N/A')
            evidence = f.get('evidence', 'No evidence provided.')
            action = f.get('suggested_action') or f.get('recommendation', 'N/A')
            print(f"\n {idx}. [{sev}] ({fid}) {title}")
            print(f"    Evidence: {evidence}")
            print(f"    Action  : {action}")

    print("\n=======================================================")
    print(f"Full Adobe Round 3 compliant JSON report saved to: {output_file}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
