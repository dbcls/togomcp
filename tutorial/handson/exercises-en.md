<!-- workshop-only -->
# Hands-on Exercises
<!-- /workshop-only --><!-- public-only -->
# Exercises for Self-Assessment
<!-- /public-only -->

Worked solutions are in [solutions-en.md](solutions-en.md). **Do them yourself first, then look.**

Difficulty: ★ basic ／ ★★ applied ／ ★★★ advanced

> ⚠️ The numbers you get **change from day to day**. If your figures differ from the worked solutions, that alone is not an error. Check **the reasoning, and the steps that led there**.

---

## Exercise 1 ★ — Check the connection and ask your first question

**(a)** Confirm that TogoMCP is connected.

**(b)** Pick one human protein you care about and look up its UniProt entry. Get the accession, the sequence length, and the function.

**(c)** Check the accession you got back on the UniProt website. Was it right?

**(d)** Was the sequence length what you expected? **If not, find out why.**

> Hint: precursor? isoform? does it include the signal peptide?

---

## Exercise 2 ★ — Travel across databases carrying an ID

Use the accession from Exercise 1.

**(a)** Convert that UniProt ID into an Ensembl gene ID, an HGNC ID, and PDB IDs.

**(b)** How many PDB structures were there? **If the answer was 0, does that mean "there is no structure"?** Check.

**(c)** If anything failed to convert, make it say so explicitly.

> 💡 **A count that shrank silently is the most dangerous kind.** Get into the habit of making conversion failures be reported.

---

## Exercise 3 ★★ — TogoVar: variants in the Japanese population

```
How many pathogenic variants are there in GBA1?
Which of them are frequent in the Japanese population?
```

**(a)** Run it.

**(b)** **Search with both "GBA1" and "GBA"** and compare the `match_type`. What is different?

> ⚠️ Both put GBA1 on the first row. **There is still a difference.** Make sure you look at the `match_type` that came back.

**(b2)** Get the HGVS notation (`NM_...` / `p....`) out. **It does not come back on the first call.** What do you have to add?

**(c)** Does the number of pathogenic + likely pathogenic variants match the total number of `significance` classification records? **If not, what is each of them counting?**

**(d)** How much did the frequencies differ between the Japanese cohorts and the international cohorts?

> ⚠️ These results include disease names as registered by ClinVar. **Treat them as ClinVar classifications.** They are not medical advice.

---

## Exercise 4 ★★ — Experience how changing the definition changes the answer

Take Demo 3' from [Chapter 4](../handbook/04-advanced-queries-en.md) and **break it yourself.**

**(a)** Look up "human lysosomal enzymes that are targets of approved drugs" using the UniProt keyword **KW-0458**.

**(b)** Ask the same question using GO **GO:0043202 (lysosomal lumen)**.

**(c)** Compare the two answers. **Why are they this different?**

**(d)** Name one term in your own field where the same trap could occur.

> This is the most important exercise here. **When an answer looks strange, what to suspect is not the syntax — it is the definition of the target.**

---

## Exercise 5 ★★ — Run through the four verification steps

Take the results from Exercise 3 or 4 and actually walk through the verification procedure in [Chapter 7](../handbook/07-verification-en.md).

**(a)** Get the executed SPARQL printed in full and save it (**do not let it be summarized**)

**(b)** Get both `COUNT(DISTINCT ...)` and `COUNT(*)`. **If they differ, make it explain what is being duplicated**

**(c)** On the original database's website, eyeball **the top hit and one "surprising" hit**

**(d)** Record the date of execution, the endpoint, and the original text of your question

**(e)** Save all of this together in one folder

> Is it in a form that you, six months from now, could reproduce?

---

## Exercise 6 ★★★ — Write a bad question and a good question yourself

**(a)** For your own research topic, write **a deliberately vague question** and send it.

**(b)** Open the tool log and check:
- Were `run_sparql` or the search tools called?
- Did the specific names in the answer (gene names, compound names, etc.) **actually exist in the tool output**?
- Were accessions or IDs attached?

**(c)** Using [the five elements from Chapter 6](../handbook/06-good-questions-en.md), specify the same intent and ask again.

**(d)** What changed? The time taken, the number and kind of tool calls, the content of the answer.

**(e)** **Does the specified version still have limitations left in it?**

> (e) is the real point. A good question makes the answer better; it does not make the limitations disappear.

---

## Exercise 7 ★★★ — Make it look for counter-evidence

Pick one claim in your field that you believe is correct.

**(a)** Ask "is this claim correct?"

**(b)** Then ask **"find evidence in the databases that contradicts this claim."**

**(c)** Did the answer change? Which was more useful?

> An AI tends to agree with you. **In practice, "find the counter-evidence" works, and "is this right?" does not.**

---

<!-- public-only -->
## Finally — with your own topic
<!-- /public-only --><!-- workshop-only -->
## Free exercise
<!-- /workshop-only -->

**Ask one thing you actually want to know, from your own research topic.**

It is fine if it does not work. **When it does not work is exactly when you should isolate what happened.**

Worth recording:

- What you asked (the original wording, verbatim)
- Which tools were called
- What came back
- **Where it differed from what you expected. Was that the AI's problem, the database's problem, or the question's problem?**

<!-- workshop-only -->That last line is what you should take away from this workshop.<!-- /workshop-only --><!-- public-only -->**That last line is what you should take away from this tutorial.**<!-- /public-only -->
