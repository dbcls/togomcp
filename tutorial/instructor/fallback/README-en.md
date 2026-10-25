# Fallback material: what to switch to when things fail

**Recorded: 2026-08-21** (all measured on the live environment). **Values re-measured: 2026-10-01, 10-14, 10-20** (TogoMCP 2.27.0). **Model behavior re-measured: 2026-10-20** (Sonnet).

> ⚠️ **About the model.** The main record was taken with the session configured as `claude-opus-5`. The appendix holds the August **re-measurement on Sonnet 5**. All values matched, but **short demos took 1.5 to 2.5 times as long**, and **the failure demo behaved differently altogether** (Sonnet never touched a database). Be sure to read it.

> ⚠️ **In the 2026-10-20 Sonnet re-measurement the values matched, but four demos behaved differently from August** (PDB reached the top 10 by search alone without SPARQL; the lysosome demo chose GO:0005764 and answered GLA and GAA only; failure demo A disclosed that its answer came from memory; failure demo B aggregated over all rows without sampling, so the error does not occur). The record has not been rebuilt: it stays as **"the 2026-08 record"**, and the affected sections open with a note on the 10-20 behavior. When you project it, say "this is the August record".

> 📝 **About this English edition.** The sessions were run with Japanese prompts. Prompts and model replies in `transcripts-en.md` are translations; tool calls, SPARQL and returned data are as recorded.

## What this is

**A network failure that wipes out every demo really does happen.** In August 2026, every SPARQL endpoint on rdfportal.org went down.

`transcripts-en.md` (and `fallback-en.html` for projection) contains **the run record, as it happened,** of every demo used in the lecture: the prompt, the order and arguments of the tool calls, the full text of the SPARQL executed, the real data returned, and the reply.

**If the live demo goes down, project this.**

---

## Deciding to switch

| Situation | Decision |
|---|---|
| A demo has not returned in 60 seconds | **One retry at most.** On the second failure, give up and go to the fallback |
| Every SPARQL query fails | Endpoint outage. Use the fallback for everything SPARQL-based. **The REST-based demo (TogoVar in M9) may still be alive**, so it is worth trying |
| MIE files and the guide respond but only SPARQL fails | Same as above. The problem is the external endpoints |
| Most participants cannot connect | Decide at M1 whether to switch to the 60-minute version. **The later you leave it, the harder it gets** |

> ⚠️ **Silence in front of the audience is the worst outcome.** When in doubt, switch.

---

## How to use it

1. **Before the session starts, open `fallback-en.html` in a separate browser tab.** Looking for it after the failure is too late.
2. When something fails, switch to that tab and scroll to the demo.
3. **Say honestly: "this is a record of a run done in advance".** There is no need to hide it. In fact, the situation itself ("the database is alive, but we cannot reach it today") connects to the reproducibility discussion in Chapter 7.

---

## What instructors must prepare themselves

**Take your own screenshots.** None are included here.

Why: participants look at **your screen**. Unless it looks like the client you use (Claude desktop / web / Claude Code), it causes more confusion than it solves.

What to capture:

- [ ] Each demo **with the tool-call log expanded** (← the most important one. The failure demos in M2 and M4 do not work unless the log is visible)
- [ ] The connector-adding screen (M1)
- [ ] A successful connection check

---

## Demos included

| # | Demo | Measured (August) | 10-20 (Sonnet) | Module |
|---|---|---|---|---|
| 1 | Database list (connection check) | 8 s | 19 s | M1 |
| 2 | Insulin → UniProt | 18 s | 29 s | M2 |
| 3 | ID conversion + PDB | 18 s | about 29 s | M2 |
| 4 | With and without a pinned graph | 40 s | 26 s (also narrowed by EC, so the counts differ) | M3 |
| 5 | PDB Mpro by resolution | 51 s | 54 s ⚠️ different behavior | M4 |
| 6 | Lysosomal enzymes × approved drugs | 100 s | 64 s ⚠️ different behavior | M4 |
| 7 | ★ Failure demo A (vague question) | 9 s | 25 s ⚠️ different behavior | M4 |
| 8 | ★ Failure demo B (specified question) | 369 s | 63 s ⚠️ different behavior | M4 |
| 9 | TogoVar GBA1 | 32 s | 40 s | M9 |

**In the August recording every endpoint was healthy; the only failure or retry was one timeout in #8.** On 10-20 there were 0 timeouts.

---

## ⚠️ The numbers move

The recorded numbers are basically **as of 2026-08-21**; the values that changed on re-measurement (the number of databases, the PDB method breakdown, §9 TogoVar) have been replaced with the 2026-10 values, and each place says which day a value is from. PDB changes with new depositions, TogoVar with ClinVar releases and data reloads, and PubTator with ingestion.

**If the numbers differ when the live run works, that is not abnormal.** Tell the participants so as well: if anything, it is evidence that "the database is alive".
