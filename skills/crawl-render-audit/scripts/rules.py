"""
Decision rules -> candidate findings.

Implements the 5 provisional rules from Adobe_R3_Audit_Research_README.md
(Section 6), honoring counterexamples:

- Dot & Key: DOM expansion + JSON-LD price => NO CSR failure (rule 4 rescue
  suppresses rule 3 for rescued facts; rule 5 stays warning-only).
- Healthline: strong HTML but AI bot block => rule 2 fires independently.
- Nordstrom: 403/WAF => rule 1 fires; CSR diagnosis (rule 3) is SKIPPED
  because rendering under blockade is unreliable.
- Saraswat Bank: rendered growth but facts in static table => rule 3 needs
  fact-level proof, never word counts.

Finding contract (README Section 7): id, title, severity, evidence {},
suggested_action, mechanism, priority, confidence. The orchestrator's
official report maps these onto its own schema.
"""

from typing import Dict, List

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def _finding(fid, title, severity, evidence, suggested_action, mechanism,
             priority, confidence="high"):
    return {
        "id": fid,
        "title": title,
        "severity": severity,
        "evidence": evidence,
        "suggested_action": suggested_action,
        "mechanism": mechanism,
        "priority": priority,
        "confidence": confidence,
    }


def apply_rules(signals: Dict) -> List[Dict]:
    """Apply the 5 provisional rules to collected signals.

    signals keys (all optional):
      blockade: {blocked, kind, signals, status}
      ai_access: {blocked_bots, bots}
      fact_summary: {total, in_raw, js_dependent, jsonld_rescue, missing_everywhere}
      fact_matrix: [...] (rows with key/js_dependent/jsonld_rescue)
      expansion: {raw_words, rendered_words, abs_gain, pct_gain, screening_triggered}
      jsonld: {objects_count, errors_count}
      render_ok: bool
    """
    findings: List[Dict] = []
    blockade = signals.get("blockade") or {}
    ai_access = signals.get("ai_access") or {}
    fact_summary = signals.get("fact_summary") or {}
    fact_matrix = signals.get("fact_matrix") or []
    expansion = signals.get("expansion") or {}
    render_ok = signals.get("render_ok", False)

    # Rule 1 — Edge Access Blockade.
    if blockade.get("blocked"):
        kind = blockade.get("kind", "http-block")
        status = blockade.get("status", 0)
        findings.append(_finding(
            "ACCESS-001",
            "Edge access blockade prevents automated retrieval",
            "critical",
            {"status": status, "kind": kind,
             "signals": blockade.get("signals", [])},
            "Allow automated audit traffic or provide an accessible mirror; "
            "verify edge/bot-management rules are not blocking legitimate "
            "fetch traffic before diagnosing content issues.",
            "HTTP edge controls (status/challenge) stop the retrieval chain "
            "before any content layer can be evaluated.",
            1,
        ))
        # Under blockade, rendering/CSR conclusions are unreliable: stop here
        # except for independently measurable policy info.
        # (Nordstrom lesson.)

    # Rule 2 — Crawler Policy Restriction (independent layer; fires even under blockade).
    blocked_bots = ai_access.get("blocked_bots", []) or []
    if blocked_bots:
        live = [b for b in blocked_bots
                if (ai_access.get("bots", {}).get(b, {}).get("kind") == "live-search-agent")]
        findings.append(_finding(
            "POLICY-001",
            "AI crawlers restricted by robots.txt",
            "high" if live else "medium",
            {"blocked_bots": blocked_bots,
             "live_search_agents_blocked": live},
            "Add granular Allow rules for conversational search agents "
            "(e.g. ChatGPT-User, PerplexityBot) on public content paths while "
            "keeping training-crawler restrictions if desired.",
            "robots.txt disallow prevents compliant AI agents from fetching "
            "public target content regardless of HTML quality.",
            2,
        ))

    if blockade.get("blocked"):
        return findings  # no CSR/expansion conclusions under blockade.

    # Rule 3 — Client-Side Rendering Fact Dependency (fact-level proof only).
    js_facts = [m.get("key") for m in fact_matrix if m.get("js_dependent")]
    if render_ok and js_facts:
        findings.append(_finding(
            "RENDER-001",
            "Important facts are JS-dependent",
            "high",
            {"js_dependent_facts": js_facts,
             "count": len(js_facts),
             "note": "absent from raw HTML and raw JSON-LD; appear only after rendering"},
            "Server-render critical facts (price, availability, key specs) or "
            "duplicate them in JSON-LD so they exist pre-render.",
            "Facts missing pre-render force every retrieval system through "
            "full JS execution to observe them.",
            3,
        ))

    # Rule 4 — Structured Data Fallback (positive/info, never a failure).
    rescued = [m.get("key") for m in fact_matrix if m.get("jsonld_rescue")]
    if rescued:
        findings.append(_finding(
            "SCHEMA-001",
            "JSON-LD provides structured fallback for key facts",
            "info",
            {"rescued_facts": rescued},
            "Keep JSON-LD values in sync with visible page content.",
            "Raw JSON-LD carries facts even where visible markup is dynamic.",
            5,
            confidence="medium",
        ))

    # Rule 5 — Word Expansion Screening (warning only, triggers inspection).
    if render_ok and expansion.get("screening_triggered"):
        # Downgrade to info when facts already explain the page (no missing facts).
        missing = fact_summary.get("missing_everywhere", 0) or 0
        js_n = fact_summary.get("js_dependent", 0) or 0
        severity = "medium" if (missing or js_n) else "low"
        if not js_facts:
            # No fact-level proof: observation only, explicitly not a failure.
            findings.append(_finding(
                "SCREEN-001",
                "Rendered text expansion noted (screening only)",
                severity if severity == "low" else "medium",
                {"raw_words": expansion.get("raw_words"),
                 "rendered_words": expansion.get("rendered_words"),
                 "abs_gain": expansion.get("abs_gain"),
                 "pct_gain": expansion.get("pct_gain"),
                 "note": "expansion alone is not a failure; inspect fact matrix"},
                "No action unless the fact matrix shows missing/JS-dependent facts.",
                "Large DOM growth is often nav/widgets; facts decide.",
                6,
                confidence="low" if not (missing or js_n) else "medium",
            ))
    return findings
