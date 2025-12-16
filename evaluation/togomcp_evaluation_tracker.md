# TogoMCP Evaluation Tracker (TSV Format)

Copy the content below into a spreadsheet application (Excel, Google Sheets, etc.)

---

```tsv
Question_ID	Date	Category	Question_Text	Baseline_Summary	TogoMCP_Summary	Tools_Used	Accuracy	Precision	Completeness	Verifiability	Currency	Impossibility	Total_Score	Assessment	Include	Key_Difference	Notes
1	2025-01-15	Precision	What is the UniProt ID for human BRCA1?	Mentioned it's a tumor suppressor but no ID	P38398	search_uniprot_entity	2	3	2	3	1	2	13	VALUABLE	YES	Exact database ID provided	Good baseline test
2	2025-01-15	Completeness	How many human genes in GO term DNA repair?						0	0	0	0	0	0	0	REDUNDANT	NO		Example only - fill in actual data
```

---

## Instructions for Use:

1. Copy the TSV content above (between the ```tsv``` markers)
2. Create a new spreadsheet in Excel or Google Sheets
3. Paste the content (it should automatically separate into columns)
4. Fill in one row per evaluation

## Column Definitions:

- **Question_ID**: Sequential number or unique identifier
- **Date**: YYYY-MM-DD format
- **Category**: Precision | Completeness | Integration | Currency | Specificity | Structured Query
- **Question_Text**: The full question (keep concise)
- **Baseline_Summary**: 1-2 sentence summary of baseline answer
- **TogoMCP_Summary**: 1-2 sentence summary of enhanced answer
- **Tools_Used**: Comma-separated list of tools used
- **Accuracy**: Score 0-3
- **Precision**: Score 0-3
- **Completeness**: Score 0-3
- **Verifiability**: Score 0-3
- **Currency**: Score 0-3
- **Impossibility**: Score 0-3
- **Total_Score**: Sum of dimension scores (0-18)
- **Assessment**: CRITICAL | VALUABLE | MARGINAL | REDUNDANT
- **Include**: YES | NO
- **Key_Difference**: Brief description of main improvement
- **Notes**: Any additional observations

## Analysis Tips:

Once you have data:
- Sort by Total_Score to find best questions
- Filter by Category to check coverage
- Count Assessment types to check distribution
- Use pivot tables to analyze by organism/domain if you add that column

## Suggested Additional Columns (Optional):

- Organism
- Domain (gene/protein/compound/pathway/disease)
- Complexity (simple/medium/complex)
- Verification_Status (verified/not_verified/failed)
- Reviewer
- Response_Time (seconds)

