# Retired benchmark questions

Questions moved here are no longer part of the evaluation set. The validators and the
answer runner read only `benchmark/questions/question_*.yaml`, so nothing in this folder is
scored. Files are kept so that earlier results computed on them stay reproducible.

| File | Retired | Replaced by | Why |
|---|---|---|---|
| `question_022_dev_exposed.yaml` | 2026-09-30 | new `question_022.yaml` (held-out) | Dev-exposed: the v3 MIE equivalence canary failed on it (44 vs 208), and the glycosmos `enum_go_descendants` example was written to fix that failure, so later scores on it measure in-sample fit. Its gold answer had also drifted (208 recorded, 264 live on 2026-09-30); it was retired, not refreshed, so the file still records 208 — the answer the v2/v3 equivalence run was judged against. |
| `question_066_dev_exposed.yaml` | 2026-09-30 | new `question_066.yaml` (held-out) | Dev-exposed: the v3 MIE smoke test failed on it (14 vs 71 LIM-domain proteins); the diagnosis produced MIE spec §4.4 and the uniprot keyword-enumeration rewrite, so later scores on it measure in-sample fit. Its recorded counts still reproduced at retirement. |
