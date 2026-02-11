# TogoMCP Evaluation - File Index

## Quick Start

**To create a question, say:** "Use the worksheet"  
**I will read:** `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_WORKSHEET.md`

**For output format:** See `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_FORMAT.md` ⭐

---

## Dataset Composition Target

**⚠️ Multi-Database Priority:** 60-80% of questions (30-40 out of 50) should integrate **2-4 databases** to showcase TogoMCP's cross-database capabilities.

**Current Status:** Track progress in `coverage_tracker.yaml`

---

## File Locations

### Working Files (Use These)
```
Worksheet:     /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_WORKSHEET.md
Quick Guide:   /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUICK_GUIDE.md
Keywords:      /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv
Tracker:       /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml
```

### Format Specification ⭐
```
Format Spec:   /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_FORMAT.md
```

### Reference Only
```
Detailed Guide: /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QA_CREATION_GUIDE.md
```

### Output
```
Questions: /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml
```

---

## Usage Patterns

| You Say | I Should Read |
|---------|---------------|
| "Use the worksheet" | QUESTION_WORKSHEET.md |
| "Check the tracker" | coverage_tracker.yaml |
| "Read the keywords" | keywords.tsv |
| "Quick reference" | QUICK_GUIDE.md |
| "Detailed explanation" | QA_CREATION_GUIDE.md |
| "Show format" | QUESTION_FORMAT.md ⭐ |

---

## Workflow

1. You: "Create question N" or "Use the worksheet"
2. Me: Reads QUESTION_WORKSHEET.md using `Filesystem:read_text_file`
3. Me: Follows worksheet, fills each blank
4. Me: Writes question_XXX.yaml **directly to user's filesystem** using `Filesystem:write_file`
5. Me: Updates coverage_tracker.yaml **directly to user's filesystem** using `Filesystem:write_file`

---

## Critical File Handling Rules

**✓ ALWAYS DO:**
- Use `Filesystem:read_text_file` to read files from `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/`
- Use `Filesystem:write_file` to write files directly to `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/`
- Write question files directly to: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml`
- Update tracker directly at: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml`

**✗ NEVER DO:**
- Create files in `/home/claude/` (Claude's computer)
- Use `/mnt/user-data/outputs/` for this workflow
- Use `create_file` or `bash_tool cp` commands
- Use `present_files` tool - files are already on user's filesystem where they belong

---

## Important Notes

⚠️ **All question YAML files MUST follow the canonical format in QUESTION_FORMAT.md**

The format specification includes:
- Required and optional fields
- Field types and constraints
- Format by question type
- RDF triples comment format
- Validation rules
- Complete examples
- **Dataset composition target: 60-80% multi-database questions**

---

**Version:** 4.3
**Last Updated:** 2025-02-11  
**Change:** Clarified file handling - always use Filesystem tools for user's computer, never create files on Claude's computer
