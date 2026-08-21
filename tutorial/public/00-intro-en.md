# TogoMCP Tutorial

A hands-on tutorial for querying life-science databases in plain language — **without writing SPARQL**.

Written for life-science researchers and graduate students. No informatics background is assumed. You can work through it without knowing RDF or SPARQL.

---

## What you will be able to do

1. Connect TogoMCP to your own environment and query the major life-science databases in plain language
2. Tell whether an answer came **from a database or from the AI's memory**
3. Keep your results in a **reproducible form** — good enough to put in a paper

**The third one matters most.** The first one alone takes ten minutes.

Most of this tutorial is spent not on examples that work, but on **examples that fail**. In Chapter 4 we deliberately ask a vague question. It returns a fluent answer in about a dozen seconds — and that answer **never touched a database**. Nothing on the screen tells you so.

> **Being fast and confidently wrong is more dangerous than being slow and failing.**

Learning to tell the difference is what this tutorial is for.

---

## How to read this

**About 90 minutes end to end.** You do not have to read all of it.

| Chapter | Contents | Time |
|---|---|---|
| **00 Overview** | Why TogoMCP exists | 5 min |
| **★01 Setup** | Connect (there is a no-install route) | 10 min |
| **★02 First demo** | Run it. Then look at what happened underneath | 10 min |
| 03 How it works | MCP and MIE — why correct SPARQL comes out | 15 min |
| 04 Harder questions | Cross-database queries, and **questions that fail** | 20 min |
| 05 Skills | Methodology packaged as a workflow | 10 min |
| **★06 How to ask a good question** | The chapter most worth taking away | 10 min |
| 07 Verification and reproducibility | What to do before a number goes into a paper | 10 min |
| 08 Troubleshooting | Read when things break | as needed |
| Appendix | Local install, KEGG | 15 min |
| Exercises / Answers | Self-check | 30 min |

**In a hurry? The three ★ chapters alone are enough to be useful** (01 → 02 → 06, about 30 minutes).

Using this page:

- Navigate from the table of contents on the left; your position updates as you scroll
- **Prompts and queries copy with one click** — hover over a code block and a Copy button appears
- `◐` toggles dark/light, `⎙` prints (save as PDF from there)
- It reads fine on a phone

---

## ⚠️ About the numbers in this tutorial — please read this first

The text is full of **actual results**: accession numbers, counts, resolutions. **Every one of them was measured.**

**Measurement conditions:**

| | |
|---|---|
| Dates | 2026-08-20 (initial) / 2026-08-21 (everything re-measured and corrected) |
| Model | Session configured as `claude-opus-5` and as `claude-sonnet-5`, both measured |
| Server | Hosted instance, `https://togomcp.rdfportal.org/mcp` |
| Language | Prompts in Japanese |

**And when you run the same queries, your numbers will be different.**

That is not a malfunction. **It is what a living database looks like.** While this tutorial was being written, the PDB counts moved within a matter of days.

So what this tutorial wants you to take away is **not the numbers — it is the queries, and the reasoning that produced them.** That is why it consistently gives you the query text rather than a table of results.

> **This is not a weakness of the material. It is the very practice the material teaches.** Chapter 7 explains why "record the query and the date" is the rule.

One more thing. **How long a query takes, and which tools get used, depend on the model you are using.** Faced with the same question, one model ran a single search; another **never touched a database at all**. The values that came back agreed — but **how they were reached did not.**

---

## If you want to run a workshop with this material

**The complete teaching kit is on GitHub** — 90- and 60-minute schedules, a verbatim instructor script, full transcripts of every demo (for when the network fails), exercises with answers, and projection slides.

> https://github.com/dbcls/togomcp — see the `tutorial/` directory

The Markdown sources and the build script are included, so **adapt it to your own field** as you see fit.

---

## Citation

If you use TogoMCP in your research, please cite:

> Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

For the evidence behind the MIE file design (an ablation study):

> Kinjo, A. R., & Yamamoto, Y. (2026). Measure before you rewrite: ablation-driven redesign of LLM-facing RDF schema documentation in TogoMCP. *BioHackrXiv*. https://doi.org/10.37044/osf.io/6v5ra_v1

**Please also cite the individual databases you actually used.** TogoMCP is the doorway, not the source of the data.

- Hosted server: https://togomcp.rdfportal.org/
- Repository: https://github.com/dbcls/togomcp
- RDF Portal: https://rdfportal.org/
