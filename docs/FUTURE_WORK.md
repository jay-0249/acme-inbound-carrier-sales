# Future Work

This document captures the capabilities deliberately scoped out of the proof of concept, and how each would be built for production. Each entry follows the same shape: the real-world concern, why it was out of scope for the POC, and the production path.

The framing matters: these are design decisions and restraint, not a backlog of things that are broken. The POC was built to prove the core flow end to end, verify it with live calls, and stay honest about its edges. Everything below is the planned path from that working core to a production system, and the build is structured so each step is additive rather than a rewrite.

---

## Negotiation engine

### Source the ceiling from the shipper-paid rate

In reality the negotiation ceiling is the broker's maximum buy rate: the shipper-paid rate minus a target margin, which the broker knows before the call. The posted `loadboard_rate` is only the opening number, not the ceiling. That shipper rate is not in the provided 13-field load schema, so rather than alter the customer's data model, the POC proxies the ceiling as an urgency-scaled band over the posted rate.

**Production:** Source the shipper rate and margin target from the TMS and swap the ceiling input. The negotiation logic does not change; only the input that feeds the ceiling does.

### Market-aware and lane-density pricing

Deadhead miles, live spot-market rates, and how busy a lane is all move the price a carrier will actually accept. A broker holds firmer on a high-traffic lane where another carrier is likely to call, and flexes on a quiet one. None of that data is provided in the POC.

**Production:** Integrate a market-rate feed and the carrier's current location, and track historical call volume per lane, then layer these as additional factors on top of the urgency ceiling.

### Sentiment-aware negotiation strategy

The POC uses a single deterministic strategy (a front-loaded ladder) so every concession is explainable and the ceiling is never at risk. The ladder shape itself is fixed; a more advanced agent could vary it per call based on carrier sentiment. The hard rule: the agent must never *choose* the strategy itself based on a read of the call, that would reintroduce the non-determinism the whole pricing design eliminates. Deciding how aggressively to concede is a money decision and belongs in code, not in the model.

**Production:** Add an optional `strategy` parameter and an optional `sentiment` input to the `/negotiate` endpoint. The server selects the ladder shape and applies sentiment-aware concession rules deterministically (for example: on negative sentiment past the first round, allow one additional concession step, still strictly under the absolute ceiling). The agent passes structured signals; the backend decides everything. The ceiling stays absolute regardless of strategy or sentiment.

### Flat-increment pricing and policy-gated rejection levers

The POC computes offers as fractions of the negotiation band rounded to the nearest $25. Real brokers think in flat dollar increments per lane and rate tier. Separately, when a carrier rejects the final rate, real brokers pivot to non-monetary levers (quick pay, detention coverage, reload guarantees) before walking away. The POC deliberately forbids the agent from offering any of these, because each is a real, unauthorized financial commitment that does not exist in the provided load schema. Letting the agent invent perks to close a deal is a compliance risk in a regulated-money domain, and worse than losing the load.

**Production:** Move to true flat-increment logic per lane and rate tier. For rejection handling, pull a per-load policy payload from the TMS that explicitly authorizes specific levers (with caps), inject only the approved levers into the agent's final turn with strict "if not authorized, never mention it" boundaries, and pitch one approved lever in priority order, else a firm professional walkaway. Log failed negotiations so the system can decide whether to call back rather than re-dialing blindly.

### Graceful exit on repeated below-rate offers

The POC correctly catches an offer below the posted rate (likely a voice mis-transcription) and asks the carrier to restate it. If a carrier repeats a below-rate number many times, the agent keeps asking, with no termination. The floor itself is the core fix and works; the loop bound is a robustness refinement.

**Production:** Track consecutive confirm-and-restate cycles per call and, after a bounded number of attempts, exit gracefully, either escalate to a human or wrap up politely.

---

## Call flow and agent behavior

### Dual-intent call router

Real inbound carrier calls follow two patterns. The dominant one is a carrier calling about a specific load they saw on a board and referencing its load ID. The minority is a carrier offering an empty truck on a lane, usually from an established relationship. The POC implements the load-reference path, since it is the prevalent pattern, and the lane-search lookup is already built behind the same API.

**Production:** Open with a dual-intent prompt ("Are you calling about a specific load, or do you have a truck to fill?") and branch: load-reference lookup on one side, filtered lane search on the other. Both endpoints already exist.

### Graceful pivot when a load is already covered

When a carrier calls about a load that is no longer available, a good agent does not dead-end. It pivots to search mode using the lane the carrier was already interested in. This depends on the lane-search branch above.

**Production:** On a not-found or unavailable load, transition into lane search using the requested load's origin and destination as the seed.

### Guarded alternative-load pitch

If the requested load does not fit or the price gap cannot close, offering a different matching load can still book revenue. Left unguarded, an agent tends to over-pitch alternatives on every call, which annoys carriers.

**Production:** A single controlled alternative suggestion under strict conditions: only after a clear no-match or failed negotiation, offered once, then stop.

### Speech-layer handling and natural pacing

Two call-quality refinements: carriers often read load IDs using the NATO phonetic alphabet ("Baker-six-five-Charlie"), which the agent should normalize before lookup; and dead silence during an API lookup causes carriers to hang up, so a brief filler line before tool calls keeps the call natural. Both depend on observed behavior of the platform's voice layer in real calls.

**Production:** Prime the agent prompt to normalize phonetics and to speak a short filler line before lookups, after confirming the speech-to-text behavior on alphanumeric strings.

### Returning-caller memory

A carrier who called earlier about the same load should not have to start over. Stateful cross-call identity is real work and hard to demonstrate over the web-call trigger used in the POC.

**Production:** Key call records by MC number, retrieve prior context on a repeat call, and confirm with the caller whether to continue or start fresh.

---

## Data model and persistence

### Mark a load as booked when a deal closes

When a deal closes, the POC records the booking on the call but does not change the load's own status, so the load stays in the available pool and could still be returned by a later lookup. This is consistent with the POC treating loads as a read catalog rather than live inventory.

**Production:** Give a load a status that flips to booked when a deal closes, and exclude non-available loads from lookups so the same load is never offered to two carriers. In a real deployment this state would live in, or sync with, the load board or TMS, so the system updates the source of truth rather than a local copy.

### Multiple loads per call

The POC assumes one load per call, which matches the dominant inbound pattern, and keys the call summary to a single load. Per-load negotiation history is still preserved correctly even if more than one load is touched; only the call-level summary collapses to the last load.

**Production:** Key call-level outcomes by call and load together, so one call can carry multiple per-load outcomes (a call becomes a parent of one or more load engagements), and aggregate the dashboard at that grain. This is a schema change, not a prompt change.

### Transcript-level storage, if needed

The POC persists only the structured call fields (carrier, load, agreed rate, rounds, outcome, sentiment), not the raw transcript, because the dashboard's metrics are derived from structured fields and the transcript adds no value to aggregation. The platform already retains the full transcript on its side for per-call review.

**Production:** Keep the structured-variables contract as the persistence boundary. If transcript-level analysis is later needed (for example, mining decline reasons), store transcripts separately in object storage or a JSON column keyed by call id, rather than coupling them to the metrics table.

---

## Carrier verification

### Richer FMCSA eligibility policy

The POC treats carrier eligibility as a clean pass or fail against FMCSA authority, which keeps the call flow simple. Real vetting weighs safety rating, insurance on file, and authority history.

**Production:** Pull the full FMCSA profile and apply a configurable eligibility policy (minimum safety rating, insurance thresholds, authority age) that the broker controls.

---

## Dashboard

### Analytics depth at production volume

Two enhancements once real call volume exists: a call-duration analysis section with operationally useful cross-cuts (duration by outcome, duration versus sentiment, duration versus negotiation rounds), and server-side pagination plus filtering on the recent-calls table (by outcome, date range, sentiment). The POC's single-load metrics and 25-row sample table are sufficient to demonstrate the product, and these are deferred deliberately to protect the deadline-critical deliverables.

**Production:** Extend the metrics payload with duration buckets and cross-tabs, and move the recent-calls table to server-side pagination with filter controls.

---

## Infrastructure and security

### Remove the API key from the browser

The POC gates every endpoint with an API key over HTTPS, which meets the stated security bar. The honest limitation: the dashboard is a single-page app that calls the API from the browser, so its key is present in the built bundle and is visible to anyone who opens the deployed dashboard. In the POC this only exposes synthetic demo data, so the exposure is non-sensitive. Scoping the key read-only does not fix this, any key shipped to a browser is public by definition.

**Production:** Authenticate the user viewing the dashboard (session or token) with the backend proxying the metrics behind that session, or server-inject the dashboard data at render time, so no long-lived key ever reaches the browser. A scoped read/write key split was implemented on a separate branch as a partial hardening step, but session-based auth is the real fix.

### Platform-native persistence

The POC runs a standalone FastAPI service with its own database, which directly satisfies the assignment's loads-API requirement and demonstrates REST design, async data access, API-key auth, FMCSA integration, and testing. The HappyRobot platform offers a managed per-org database (Twin) that could replace parts of this self-hosted stack. Migrating proven, tested infrastructure to an unfamiliar managed feature on a deadline is high risk for no requirement gain, so the custom API was kept for the POC and the platform-native path is documented here.

**Production:** Persist call outcomes through managed write nodes rather than a custom endpoint, sync loads into a managed polling table from the real load board or TMS instead of seed data, and serve the dashboard through the platform's managed gateway, removing the need for separate backend infrastructure. The custom-API approach keeps the integration portable; the platform-native path is the natural production evolution.
