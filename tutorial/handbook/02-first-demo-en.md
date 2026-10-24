# 02. The First Demo

First we run it. Then we open it up and look at **what happened underneath**. The second part matters more.

---

## Demo 1: a one-hop question

Paste this as it is.

```
Give me the UniProt entry for the human insulin (INS) gene product. Function and sequence length too.
```

**What comes back** (measured at 18–29 s; it varies by model):

| Item | Value |
|---|---|
| Accession | **P01308** |
| Mnemonic | INS_HUMAN |
| Name | Insulin [Cleaved into: Insulin B chain; Insulin A chain] |
| Organism | Homo sapiens (Human) |
| Sequence length | **110 aa** |
| Mass | 11,981 Da |

Function (verbatim from UniProt):

> Insulin decreases blood glucose concentration. It increases cell permeability to monosaccharides, amino acids and fatty acids. It accelerates glycolysis, the pentose phosphate cycle, and glycogen synthesis in liver.

### If "110 aa" stopped you

That is the right reaction. You were taught that **insulin is 51 amino acids** (A chain 21 + B chain 30).

110 is the length of the **preproinsulin precursor**. Signal peptide (24) + B chain (30) + C peptide (31) + A chain (21) + 4 residues cut out at the cleavage sites. What P01308 in UniProt points at is the translation product, not the mature hormone circulating in your blood. That is why the name in the answer says `[Cleaved into: Insulin B chain; Insulin A chain]`.

**This is the first thing you learn in this tutorial.**

> A database is **more precise** than your memory. And it can be pointing at **something other** than what you expected.

When an answer feels "wrong," the first thing to suspect is the gap between your expectation and the database's definition. The AI did not make a mistake.

---

## Demo 2: carrying an ID across to another database

Still in the same conversation, ask this next.

```
Convert that UniProt ID to an Ensembl gene ID and an HGNC ID. And the PDB structures too.
```

"That UniProt ID" is enough. The context of the previous exchange carries over.

**What comes back** (measured at 18–30 s):

| Converted to | ID |
|---|---|
| Ensembl Gene | **ENSG00000254647** |
| HGNC | **HGNC:6081** |
| PDB | a list of real structure IDs |

This is calling an ID conversion service called **TogoID**. It holds the **definition of the relation** — "you get from UniProt to Ensembl through *is product of gene*" — so this is not blind string matching.

> 💡 HGNC sometimes comes back as the bare number `6081`. The proper form is `HGNC:6081`.

---

## What happened underneath (this is the real subject)

Open the tool call log.

- **Claude desktop / Web:** expand the fold that appears while the answer is being written
- **Claude Code:** it is displayed as it runs

In Demo 1, this was the order of operations.

```
1. TogoMCP_Usage_Guide()          ← read the usage guide
2. search_uniprot_entity(...)     ← search UniProt for INS and pin down P01308
3. get_MIE_file("uniprot")        ← read UniProt's "schema documentation"
4. run_sparql("uniprot", "...")   ← build the SPARQL and run it
```

**Not magic. A procedure.**

| Step | What it does | Why it is needed |
|---|---|---|
| 1 | read the usage guide | learn which databases exist and in what order to use them |
| 2 | ambiguous word → stable ID | pin the string "insulin" to an ID that does not move: **P01308** |
| 3 | read the MIE file | learn UniProt's **predicate names, graph structure, and known pitfalls** |
| 4 | run the SPARQL | actually fetch the data |

**Step 3 is the core of TogoMCP.** The next chapter covers it in detail. Here, just hold on to the fact that **before writing any SPARQL, it always reads that database's schema documentation**.

### What we want you to notice

**Step 1 is designed to run every single time you say something.** Not once at the start of the session. (Whether the model complies every time is another matter — Chapter 4's failure demo shows a run where it is never called.)

> **📖 Terminology: "turn"**
>
> One round of the conversation. **You say something once, and the turn is over when the response to it is finished.**
>
> The point to hold on to: **however many tools get called inside a turn, it is still one turn.** Four tools ran in the example above — that is one turn. Demo 1 and Demo 2 were typed in separately, so that is two turns.
>
> ```
> [Turn 1] You: "The human insulin…"
>          → Usage_Guide, search_uniprot, get_MIE, run_sparql, answer
>             ↑ once, right here
> [Turn 2] You: "Convert that ID to Ensembl…"
>          → Usage_Guide, togoid_getRelation, togoid_convertId, answer
>             ↑ and once again
> ```

This happened because the tool description at the time of measurement (2.25 and earlier) said "call this every turn, before any other tool." The design assumes that **nothing from the previous turn's work carries over**, and the guide itself says a new question starts again at the first check (GATE 0). Since 2.27.0 the description states facts rather than orders ("meant to be read once, before the other tools are used"), so **whether it is called every time is up to the model**.

What arrives every time is the guide's **core, 33,813 characters** (2026-10-20, TogoMCP 2.27.0; five English markdown files plus the list of workflows, concatenated; a rough estimate of 8,000–10,000 tokens). Detail such as federated queries and the full troubleshooting table lives in six reference files that are fetched with `get_workflow` only when needed. The core grows with the database catalog each time a database is added (history: 44,570 characters in August 2026; 58,118 on 10-01 under 2.21, before the guide was split; 34,123 on 10-14 under 2.25.0). It stacks up as a conversation gets long, so if you care about your usage, keep it in mind.

> 💡 If you have KEGG enabled in a local installation, the KEGG section is added and it grows further.

---

## What these two demos show

**Demo 1:** we landed from an ambiguous word ("insulin") on a **verifiable ID** (P01308). The answer has a source.

**Demo 2:** we took that ID and **crossed to another database**. The single biggest nuisance in life-science databases — the same thing being called by a different name in every DB — got automated.

Combine the two and you reach the "questions that span multiple DBs" of Chapter 4.

---

## Try it yourself

**Repeat Demo 1 with a gene or protein you actually care about.**

```
Give me the UniProt entry for human [YOUR GENE / PROTEIN]. Function and sequence length too.
```

What to check:

1. Is the accession that came back the right one (five seconds on the UniProt website settles it)
2. Is the sequence length what you expected. **If not, why not** (a precursor? an isoform?)
3. Does `run_sparql` appear in the tool log. **If it does not, where did the answer come from?**

If number 3 is where you got snagged, go straight on to the second half of Chapter 4. That is the real subject.

---

Next → [03. How It Works](03-how-it-works-en.md)
