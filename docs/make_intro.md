# Create an introductory HTML page for TogoMCP
TogoMCP is a comprehensive Model Context Protocol (MCP) server that provides LLM agents with access to a vast ecosystem of life sciences databases through SPARQL queries, RDF data exploration, and ID conversion services. It integrates over 20 major biological and biomedical databases, offering researchers a powerful toolkit for cross-database queries, data integration, and knowledge discovery.

The TogoMCP endpoint is available at https://togomcp.rdfportal.org/mcp.
It is developed by DBCLS.

## Goal
Create an HTML page for researchers in biology and medicine who are not necessarily familiar with bioinformatics, explaining what TogoMCP is and how it can help their research. It should contain the following.
- Summary of TogoMCP
- Usage examples
- Setup guide
- List of available databases
- List of available tools

## Style
- Follow the style of DBCLS's default CSS at https://dbcls.rois.ac.jp/style/default.css.
- However, make it readable both on PC and smartphone.
- Mind the contrast! 
- The hero section should show the MCP endpoint URL.

## Study TogoMCP
Explore the TogoMCP tools to study how they work and the available databases.

## Usage examples
Read the following files that contain example conversations. 
Give the prompt of each session, followed by a summary of the response.
Include the description of the TogoMCP tools used.

- /Users/arkinjo/work/GitHub/togo-mcp/docs/example1.md
- /Users/arkinjo/work/GitHub/togo-mcp/docs/example2.md
- /Users/arkinjo/work/GitHub/togo-mcp/docs/example3.md

Each example should be presented in the following form:
```
Example 1.
Prompt: (The prompt provided by the user)
Response: 
(The summary of the process of finding the results)
Tools Used: 
(the list of TogoMCP tools used along the way)
Key Results:
(The summary of findings)
```

## Setup guide
Read the following webpages carefully and write a concise, accurate setup guide for each.
- [Claude Desktop](https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp#h_3d1a65aded)
- [ChatGPT](https://help.openai.com/ja-jp/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta)
- [Gemini CLI](https://geminicli.com/docs/tools/mcp-server/#how-to-set-up-your-mcp-server) Note that TogoMCP is provided via **Streamable-HTTP, not SSE**.
For Gemini CLI, the settings.json should be 
```
{
  "mcpServers": {
    "togomcp": {
      "httpUrl": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

## List available databases
Create a list of available databases with a summary of each.

## List available tools.
Create a list of available tools, each with a brief description of its functionality.

## Other MCP servers
These MCP servers are strongly recommended to be used with TogoMCP.
- [PubDictionary MCP server](https://pubdictionaries.org/mcp) TogoMCP works well with PubDictionaries MCP server.
- [PubMed MCP server](https://support.claude.com/en/articles/12614801-using-the-pubmed-connector-in-claude)
- [OLS4 MCP server](https://www.ebi.ac.uk/ols4/mcp)

## Related resources
List the following resources with summaries. Search the Web if necessary.
- [TogoMCP server](https://togomcp.rdfportal.org/mcp)
- [RDF Portal](https://rdfportal.org)
- [TogoID](https://togoid.dbcls.jp)
- [DBCLS](https://dbcls.rois.jp)

## Footer
The footer should include the following
```html
    <img src="https://dbcls.rois.ac.jp/img/logo_dbcls.svg" alt="" class="footer__logo">
    <div class='footer__organism-text'>
        <p class="footer__organism-main">Database Center for Life Science</p>
        <p class="footer__organism-sub">Joint Support-Center for Data Science Research</p>
        <p class="footer__organism-sub">Research Organization of Information and Systems</p>
    </div>
```
**IMPORTANT!**
- Make sure to follow the style of DBCLS's default CSS at https://dbcls.rois.ac.jp/style/default.css in the footer.
- The footer should be center-aligned.

## Menu tab
- Add a menu tab near the top of the page.
- The menu tab should be sticky so the user can always see it when scrolling.
- In the menu tab, include [Contact](https://dbcls.rois.ac.jp/contact-en.html) as a link.

## Back-to-top button
- 🔵 Circular button in DBCLS blue (#004098)
- ⬆️ Simple arrow symbol (↑)
- 📍 Fixed position in bottom-right corner
- ✨ Smooth shadow and hover effects