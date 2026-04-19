# Baseline v1 — Sonnet 4.6 initial build

**Date:** 2026-04-18 18:22
**Model:** OpenAI gpt-4o-mini
**Sample:** 20 tickets (Ksolves provided)

## Metrics
- Resolved: 7/20 (35%)
- Escalated: 12
- Info Requested: 1
- Failed: 0
- Avg Tool Calls: 11.3
- Avg Confidence: 0.764
- Wall Time: 165.6s

## Analysis
- Chaos injection rates: 12% timeout, 8% malformed → too aggressive for demo
- 6 tickets escalated due to max-steps exhaustion (chaos storm)
- 11 tickets correctly escalated per KB policy (warranty, fraud, replacements)
- Policy-driven escalations: CORRECT behavior

## Next iteration: v2
- Tune chaos to production-realistic rates
- Add loop detection
- Expand test data to 50 tickets
- Target: 55-65% resolved, rest correctly escalated
