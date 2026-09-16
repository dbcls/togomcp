# LOTUS → RDF (proposal tooling)

Tooling for the proposal to host [LOTUS](https://lotus.nprod.net/) — referenced
structure–organism occurrences of natural products — as an RDF Portal database.
Nothing here runs as part of the TogoMCP server; it produces files to hand to
DBCLS.

| File | What it is |
| --- | --- |
| [lotus_schema.md](lotus_schema.md) | the proposed RDF schema, with coverage figures, example queries and open questions |
| [lotus_csv_to_rdf.py](lotus_csv_to_rdf.py) | converts a LOTUS frozen CSV release into that schema (N-Triples) |
| [export_lotus.sh](export_lotus.sh) | exports the LOTUS slice of Wikidata as Wikidata-shaped RDF, via QLever |

LOTUS publishes no RDF, so the graph has to be built. There are two ways, and
they answer different questions:

* **From the frozen CSV** (`lotus_csv_to_rdf.py`) — the route the schema
  proposes. Dated, citable, carries a `pav:version`, and the chemical and
  taxonomic classifications the CSV adds are not in Wikidata at all.
* **From live Wikidata** (`export_lotus.sh`) — verbatim Wikidata shape
  (reified statements, `prov:wasDerivedFrom`). Current to the day, but
  versionless and awkward to query. Useful as a cross-check, and as the source
  of reference titles/dates/PMIDs, which the CSV lacks.

## Build the graph

```bash
# 1. get a release (v11 = 2026-04-13)
curl -LO https://zenodo.org/records/19360665/files/260413_frozen_metadata.csv.gz

# 2. (optional) reference titles, dates and PMIDs, absent from the CSV
./export_lotus.sh out/          # ~20 min, writes out/ref_*.nt among others

# 3. convert
./lotus_csv_to_rdf.py \
    --metadata 260413_frozen_metadata.csv.gz \
    --refs-nt out/ \
    --version v11 --issued 2026-04-13 \
    --out lotus_v11.nt.gz

# 4. verify before handing it over
gzcat lotus_v11.nt.gz > lotus_v11.nt
rapper -i ntriples -c lotus_v11.nt        # must report 0 errors
LC_ALL=C sort lotus_v11.nt | uniq -d | wc -l   # must be 0
```

Step 3 takes about 100 s and needs no third-party packages (stdlib only, ~400 MB
RAM for deduplication; `--no-dedupe` trades that for piping through
`LC_ALL=C sort -u`). v11 yields **9,137,465 triples**, 111 MB gzipped.

## Things that already bit us

* **QLever reports a timeout as HTTP 200 with a truncated body**, appending
  `!!!!>>#` and an error message to whatever it had streamed. Two of four
  slices were silently incomplete on the first run. `export_lotus.sh` checks
  every file for that marker and retries; do not trust the status code alone.
* **Wikidata's own endpoint is not usable for bulk export** — a hard 60 s
  limit, which six of twelve of LOTUS's published example queries exceeded on
  2026-09-15. Hence QLever.
* **Wiley DOIs contain `<` and `>`** (e.g.
  `10.1002/1099-0690(200104)2001:8<1459::AID-EJOC1459>3.0.CO;2-0`), which
  terminate an N-Triples IRI. The converter percent-encodes IRIs; without that,
  two lines in nine million are malformed and the other 9,094,796 parse fine.
* **NPClassifier cells pack several classes** as `Fatty acids $ Polyketides`,
  on up to 11.6% of rows. The converter splits them, so a class filter does not
  silently miss co-classified compounds.
* **Coverage per row ≠ coverage per entity.** NCBI taxon ids look like 86.6%
  counted over rows but are 78.0% of distinct organisms, because well-studied
  organisms recur in many rows. `lotus_schema.md` quotes per-entity figures.

## Status

Draft, unreviewed. The namespaces, graph name, endpoint, and the CC0-vs-CC-BY
licence question are all open — see the end of `lotus_schema.md`. The next step
after DBCLS review is an MIE file, which is what makes the database usable from
TogoMCP.
