# Case 101 — Ground Truth

This is the answer key for Case 101's seed data. Not consumed by any pipeline
code — it's here so we (or anyone on the team) can manually check whether
Stage 4–7 (extraction, resolution, graph write) actually recovered what's in
the source files, instead of just trusting the output looks plausible.

## Entities that should be extracted

| Entity | Type | Identifiers | Found in |
|---|---|---|---|
| Anita Deshmukh | Person | phone 9871122334, acc 30011122233 | FIR, CDR, transactions |
| Ravi Kumar | Person | phone 9876543210, acc 30012345678 | FIR, CDR, transactions, vehicle |
| Suresh Yadav | Person | phone 9123456780, acc 50098765432 | FIR, CDR, transactions |
| Priya Singh | Person | phone 9988776655 | FIR (mentioned, unconfirmed), CDR |
| MH12AB1234 | Vehicle | Maruti Suzuki Swift, White | FIR (narrative), vehicle records |
| SBIN0001234 / 30012345678 | Account | Ravi Kumar's account | FIR, transactions |
| HDFC0000123 / 50098765432 | Account | Suresh Yadav's account | FIR, transactions |
| 50098765499 | Account | unidentified — downstream mule account | transactions only |
| 60011002233 | Account | unidentified — downstream mule account | transactions only |
| Koregaon Park, Pune | Location | — | FIR, CDR tower location |
| Wakad, Pune | Location | — | CDR tower location, vehicle sighting |
| Baner, Pune | Location | — | CDR tower location |

## Relationships that should be extracted (with source + confidence intuition)

- Ravi Kumar **CALLED** Anita Deshmukh — 12/08 11:30 — source: CDR-7801, FIR narrative — high confidence (both sources agree)
- Ravi Kumar **CALLED** Suresh Yadav — three times (12/08, 14/08) — source: CDR-7802/7803/7807 — high confidence
- Ravi Kumar **CALLED** Priya Singh — 13/08, twice — source: CDR-7804/7805 — high confidence
- Suresh Yadav **CALLED** Anita Deshmukh — 14/08 — source: CDR-7806 — medium confidence (role unclear — possible follow-up contact)
- Priya Singh **CALLED** Suresh Yadav — 17/08 — source: CDR-7808 — medium confidence (this is the "hidden bridge" style link — Priya is only loosely tied to Ravi via the FIR narrative, but is directly tied to Suresh via CDR)
- Anita Deshmukh **TRANSFERRED_TO** Ravi Kumar's account — Rs 4,50,000 — 12/08 12:05 — source: TXN-55021, FIR narrative — high confidence
- Ravi Kumar's account **TRANSFERRED_TO** Suresh Yadav's account — Rs 4,30,000 — 12/08 16:40 — source: TXN-55029, FIR narrative — high confidence
- Suresh Yadav's account **TRANSFERRED_TO** two further unidentified accounts — 13–14/08 — source: TXN-55044, TXN-55051 — high confidence on the transfer, no identity behind the receiving accounts yet (realistic: not everything resolves to a named person)
- Ravi Kumar **OWNS** vehicle MH12AB1234 — source: vehicle_101.csv, FIR narrative (vehicle described, not registration-numbered, in the FIR text — the registration number itself only appears in the structured vehicle file) — this is a deliberate test: does entity resolution correctly link the FIR's "white Maruti Suzuki Swift" description to the structured record's exact plate number?
- Vehicle MH12AB1234 **SEEN_AT** HDFC ATM, Koregaon Park — 13/08 08:55 — source: VEH-3301
- Vehicle MH12AB1234 **SEEN_AT** Wakad Main Road — 14/08 19:40 — source: VEH-3302

## Deliberate entity-resolution challenges planted in this file set

1. **Name-only vs. identifier match:** the FIR narrative names "Ravi Kumar" without his phone number attached to that exact sentence; CDR/transaction files carry the phone/account. Resolution must merge these into one node via shared name + shared account number appearing elsewhere in the same document.
2. **Unconfirmed entity:** Priya Singh is introduced in the FIR with hedging language ("I suspect," "may also be involved") but has real CDR contact with both Ravi and Suresh. This tests whether the system keeps her as a *lower-confidence* investigative lead rather than asserting her involvement as fact — matching the "never assign guilt" principle.
3. **Dangling accounts:** the two downstream accounts (50098765499, 60011002233) have no name attached anywhere in this file set. They should remain as unresolved Account nodes — this is intentional, not a bug, and is exactly the kind of node a *future* case (once cross-case data exists) might resolve.

## What this seed data is NOT meant to test yet

- Cross-case discovery (Stage 12+) — this is a single case, no historical repository exists yet.
- Hidden bridge detection across *cases* — the Priya→Suresh link above is a bridge *within* this one case, useful for testing the underlying graph traversal logic early, but it isn't a cross-case bridge.
