# RugGuard

An Intelligent Contract on GenLayer that screens crypto projects for scam signals
and records an auditable, consensus-backed risk report on-chain.

   Deployed on Testnet Bradbury: `0xC965cF1A47eB081477c62945bFf70e764dCcD9F2`
   Explorer: https://explorer-bradbury.genlayer.com/address/0xC965cF1A47eB081477c62945bFf70e764dCcD9F2
   
## Why GenLayer

Deciding whether a project looks like a rug pull depends on reading unstructured
web content. A normal contract cannot do that, and a single oracle or a single LLM
call is not trustworthy. RugGuard has validators independently read the sources
and agree on the result.

## How it works

1. `check(url, extra_url)`: the contract fetches the page (and an optional second
   source such as docs or GitHub) and asks an LLM to extract **factual signals**.
2. The LLM only extracts signals. It never decides the risk level.
   - Positive signals: `team_identified`, `audit_present`, `source_verified`,
     `active_development`, each `yes` / `no` / `unknown`.
   - Red flags: `guaranteed_returns`, `urgency_pressure`, `anonymous_team`,
     each `true` only if explicitly shown in the text.
3. The risk level is computed deterministically in code (`LOW`, `MEDIUM`, `HIGH`, `UNKNOWN`).
4. Missing evidence is `unknown`, not `no`. With too little evidence the result
   is `UNKNOWN` instead of a false alarm.

## Consensus design

Uses `gl.vm.run_nondet_unsafe` with a custom validator function. Each validator
runs its own extraction and accepts the leader's result only if:

- at most one red flag differs, and
- the computed risk level differs by at most one step.

Comparing the outcome (not raw LLM fields) tolerates normal LLM variance while
still rejecting a leader that is clearly wrong.
Early versions compared every signal and failed to reach consensus
(`UNDETERMINED`), which led to this design.

## State

- `reports: url -> latest report (JSON)` with a `check_count` per URL
- `disputes: url -> list of {by, reason}`

## Methods

| Method | Type | Description |
|---|---|---|
| `check(url, extra_url)` | write | Analyze sources and store the report |
| `dispute(url, reason)` | write | Record a dispute against an existing report |
| `get_report(url)` | view | Latest report JSON |
| `get_disputes(url)` | view | Disputes for a URL |

## Example outputs (GenLayer Studio, full consensus)

**Little evidence (homepage only, JS-heavy):** `https://uniswap.org`
```json
{"page_chars": 513, "risk_level": "UNKNOWN",
 "signals": {"team_identified": "unknown", "audit_present": "unknown",
 "source_verified": "unknown", "active_development": "unknown",
 "guaranteed_returns": false, "urgency_pressure": false, "anonymous_team": false}}
```

**Same project with a second source:** `https://uniswap.org` + `https://github.com/Uniswap/v3-core`
```json
{"page_chars": 3429, "risk_level": "LOW",
 "signals": {"team_identified": "unknown", "audit_present": "yes",
 "source_verified": "yes", "active_development": "yes",
 "guaranteed_returns": false, "urgency_pressure": false, "anonymous_team": false}}
```

**Obvious scam text:** [`samples/scam_example.txt`](samples/scam_example.txt)
```json
{"page_chars": 310, "risk_level": "HIGH",
 "signals": {"team_identified": "no", "audit_present": "no",
 "source_verified": "unknown", "active_development": "unknown",
 "guaranteed_returns": true, "urgency_pressure": true, "anonymous_team": true}}
```

## Limitations

- Signals come from page text only. JavaScript-rendered pages may yield little text;
  pass a docs or GitHub URL as `extra_url`.
- Not financial advice and not a replacement for an audit.
- Tested on GenLayer Studio only.
