# Create a General Guideline for TogoMCP
I want to create a prompt template for using TogoMCP to answer the user's questions.
The prompt should follow the following steps:
1. Extract keywords from the user's question.
2. Run `list_databases()` and choose appropriate databases.
3. Run keyword searches on the selected databases to get database IDs.
3.1 Run `keyword_search_instructions` if necessary.
4. For each database, run `get_MIE_file` and study it well.
5. For each database, get relevant information using the IDs obtained above.
6. Use `togoid_*` tools to find the connections between database IDs.
7. Summarize the results.
## What to do
Do the following.
- Run `list_databases()` to see available databases.
- Run `keyword_search_instructions` for a few databases to study some instructions.
- Run `get_MIE_file` for a few databases to see what information is available in the MIE files.
- Create a **concise** Markdown file summarizing the steps.