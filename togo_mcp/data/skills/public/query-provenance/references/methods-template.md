# Methods paragraph template

Fill every `<…>` from the ledger and its verification results. Nothing from memory:
if a value is not in the ledger, leave the placeholder for the author and say so.
Delete sentences that do not apply (e.g. the REST sentence when every call was
SPARQL). Keep it short — a Methods subsection, not a tutorial.

## Template

> **Data retrieval.** Database queries were performed with TogoMCP (Kinjo et al.,
> 2026), a Model Context Protocol server that gives a large language model access to
> the RDF Portal knowledge graphs and selected REST APIs, version
> `<server version reported by the re-run script, or: [VERSION — fill in]>`
> (`<server_url>`). `<Name the assistant and model, if the author wants to: [ASSISTANT — fill in]>`
> issued the queries. The `<n>` queries supporting the results reported here
> were run on `<date range from executed_at>` against
> `<databases, each with its endpoint URL, e.g. "UniProt (https://rdfportal.org/sib/sparql)">`.
> `<If any non-SPARQL calls:>` Identifier lookups and conversions used
> `<tools, e.g. "the UniProt REST search and TogoID identifier conversion">`.
>
> **Reproducibility.** Every query, with its exact text and the result it returned,
> is provided in Supplementary File `<n>` (`ledger.yaml`; human-readable version
> `PROVENANCE.md`). All queries were re-executed on `<verification date>`, and
> `<k of n>` reproduced the recorded results exactly.
> `<If any data_changed:>` `<m>` returned different values because of database updates
> since the original run (`<list, with both values>`); the values reported here are
> from `<original | re-run>` on `<date>`. The ledger can be re-executed with the
> script `togomcp_reproduce.py` (`<pinned URL from references/reproduce.md>`). It sends
> SPARQL queries directly to the endpoints, independently of TogoMCP.

## Rules for filling it in

- **Database versions.** RDF Portal does not expose a release number for most
  databases. Write the retrieval date and the graph IRIs from `graphs` (e.g.
  "UniProt graph `http://sparql.uniprot.org/uniprot`, retrieved 2026-11-02"). Name a
  release only if a query in the ledger returned it.
- **Counts.** "k of n reproduced" counts `evidence` calls only; say how many
  `lookup` calls also matched if any did not.
- **Do not overstate.** Write "re-executed and reproduced", not "verified correct": a
  match shows the record is consistent, not that the query asks the right question.
- **Retrospective ledgers.** Add: "The query record was reconstructed after the
  analysis from the session transcript."

## Citation

Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T.
(2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via
Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042.
https://doi.org/10.1093/database/baag042

Cite the source databases as well, following each database's own citation
guidance; the ledger's `database` values list which ones were used.
