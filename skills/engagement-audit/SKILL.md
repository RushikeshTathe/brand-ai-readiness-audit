# Engagement Audit Skill

## Purpose
Evaluates what happens after a visitor arrives - whether they can quickly understand the site and take desired actions.

## Capabilities
1. **First-screen Orientation** - Checks if visitors can immediately understand the site
2. **Navigation** - Analyzes navigation structure and broken links
3. **Call-to-Action Analysis** - Evaluates presence and clarity of CTAs
4. **Content Clarity** - Assesses how well content communicates value

## Input
- `audit_context`: Shared audit context from crawl-render-audit
- `findings`: Existing findings from other skills

## Output
- Orientation findings
- Navigation findings
- CTA findings
- Updated findings list

## Usage
```python
from scripts.engagement import analyze_engagement

# Analyze engagement
updated_context, findings = analyze_engagement(context, existing_findings)
```

## Findings Format
```json
{
  "id": "engage-001",
  "skill": "engagement-audit",
  "category": "orientation|navigation|cta|content",
  "severity": "critical|high|medium|low|info",
  "title": "Finding title",
  "description": "Detailed description",
  "evidence": "Concrete evidence",
  "location": "URL or path",
  "recommendation": "Specific fix"
}
```

## Key Principles
- Convert observations into evidence
- Avoid vague subjective statements
- Focus on observable signals
- Provide actionable recommendations
