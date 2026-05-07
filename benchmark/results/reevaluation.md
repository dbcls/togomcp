# Evaluation Prompt (Opus 4.7) – For revision 1
Date: 2026-05-04
I have created 50 questions to evaluate TogoMCP, following the instructions in `benchmark/QA_CREATION_GUIDE.md.`
These questions are evaluated using the scripts `benchmark/scripts/automated_test_runner.py` and `benchmark/scripts/add_llm_evaluation.py`.
The results are in 
`benchmark/results/{condition}-yyyy-mm-dd.csv`,
Where “condition” should be one of the following:
with_guide
ng1
ng2
no_mie

I want you to independently evaluate the results from scratch, following the instructions below.
**DON’T** use API calls. Evaluate DIRECTLY here on this platform.
The evaluation results should be saved in the exact same CSV format as the original results, replacing the original scores and explanations with yours. But don’t edit the original file; make a copy.

Run 5 independent evaluations and save the results in
`benchmark/results/{condition}-yyyy-mm-dd-Opus4.7-v1.csv`
`benchmark/results/{condition}-yyyy-mm-dd-Opus4.7-v2.csv`
`benchmark/results/{condition}-yyyy-mm-dd-Opus4.7-v3.csv`
`benchmark/results/{condition}-yyyy-mm-dd-Opus4.7-v4.csv`
`benchmark/results/{condition}-yyyy-mm-dd-Opus4.7-v5.csv`
Assuming you are Opus 4.7.
—
You are an expert evaluator of scientific and biomedical research. Your task is to evaluate the quality of a given answer by comparing it to an ideal reference answer.

## EVALUATION CRITERIA

Evaluate the answer on four criteria using a 1-5 scale:

### 1. INFORMATION RECALL (1-5)
Does the answer contain all the necessary information from the ideal answer?
- 5 (Excellent): Contains all key information from the ideal answer
- 4 (Good): Contains most key information, minor omissions
- 3 (Adequate): Contains essential information but misses some important details
- 2 (Poor): Missing significant information
- 1 (Very Poor): Missing most or all key information

### 2. INFORMATION PRECISION (1-5)
Does the answer contain only relevant information, without unnecessary or irrelevant content?
- 5 (Excellent): All information is relevant and on-topic
- 4 (Good): Mostly relevant with minimal unnecessary content
- 3 (Adequate): Some irrelevant or tangential information
- 2 (Poor): Significant amount of irrelevant content
- 1 (Very Poor): Mostly irrelevant or off-topic information

### 3. INFORMATION REPETITION (1-5)
Does the answer avoid repeating the same information multiple times?
- 5 (Excellent): No repetition, each point made once clearly
- 4 (Good): Minimal repetition, does not detract from answer
- 3 (Adequate): Some repetition that could be condensed
- 2 (Poor): Significant repetition that affects clarity
- 1 (Very Poor): Excessive repetition throughout

### 4. READABILITY (1-5)
Is the answer easily readable, fluent, and well-structured?
- 5 (Excellent): Clear, fluent, well-organized prose
- 4 (Good): Generally readable with good flow
- 3 (Adequate): Understandable but somewhat awkward or poorly structured
- 2 (Poor): Difficult to read, poor grammar or structure
- 1 (Very Poor): Nearly unreadable, very poor language quality

## OUTPUT FORMAT

You must respond using this exact format:

RECALL: [score 1-5]
PRECISION: [score 1-5]
REPETITION: [score 1-5]
READABILITY: [score 1-5]
TOTAL: [sum of all four scores, 4-20]
EXPLANATION: [Brief 1-2 sentence summary of the evaluation]

## EVALUATION INSTRUCTIONS

1. Read the ideal answer carefully to understand what information should be present
2. Compare the answer to evaluate against the ideal answer
3. Assign scores for each of the four criteria
4. Calculate the total score (sum of all four)
5. Provide a brief explanation

Be objective and consistent in your scoring. Focus on the quality of the answer content and presentation.

