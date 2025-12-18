# Independent Mode Test Runner - Cost Optimization

## Problem: Conversation Accumulation

Your current test runner creates cache accumulation:

```
Q1:  CREATE 23k + READ 23k    = 46k tokens
Q2:  CREATE 23k + READ 0      = 23k tokens  
Q3:  CREATE 17k + READ 83k    = 100k tokens  ← Growing!
...
Q24: CREATE 13k + READ 295k   = 308k tokens  ← 10x larger!

Total cache tokens: 2,971k
Cache cost: $2.10
```

**Why?** The Agent SDK accumulates conversation history in cache entries.

## Solution: Independent Mode

New runner ensures complete isolation between questions:

```
Expected Pattern:
Q1:  CREATE 14k + READ 0      = 14k tokens (first time)
Q2:  CREATE 0   + READ 14k    = 14k tokens (reuse cache)
Q3:  CREATE 0   + READ 14k    = 14k tokens (reuse cache)
...
Q24: CREATE 0   + READ 14k    = 14k tokens (reuse cache)

Total cache tokens: ~350k
Expected cache cost: ~$0.15 (93% savings!)
```

## Files Created

### 1. `automated_test_runner_independent.py`
- **NEW**: Runs each question in complete isolation
- **Key feature**: No conversation history between questions
- **Expected behavior**: Cache created once, then reused
- **Cost savings**: ~80-93% reduction in cache costs

### 2. Original `automated_test_runner.py`
- **Unchanged**: Still available for conversation-based eval
- **Use case**: When you need conversation context
- **Trade-off**: Higher cache costs due to accumulation

## Usage

### Run Independent Mode (Recommended for Cost):
```bash
cd /Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts

# Run with independent mode
python automated_test_runner_independent.py example_questions.json

# Output to custom file
python automated_test_runner_independent.py example_questions.json \
  -o results_independent.csv

# Then compute costs
python compute_costs.py results_independent.csv
```

### Run Standard Mode (For Conversation Context):
```bash
# Original runner (with conversation accumulation)
python automated_test_runner.py example_questions.json
```

## Expected Cost Comparison (24 Questions)

| Component | Standard Mode | Independent Mode | Savings |
|-----------|--------------|------------------|---------|
| **Baseline** | $0.08 | $0.08 | Same |
| **TogoMCP (no cache)** | $0.38 | $0.38 | Same |
| **Cache creation** | $1.31 | $0.05 | **96% ↓** |
| **Cache reads** | $0.79 | $0.10 | **87% ↓** |
| **TOTAL** | **$2.56** | **$0.61** | **76% ↓** |

## How It Works

### Standard Mode (Original):
```python
# Each question adds to conversation state
async with ClaudeSDKClient(options=options) as client:
    await client.query(question_1)  # Creates cache with schemas
    # ... tool calls ...
    await client.query(question_2)  # Adds to cache (schemas + Q1 history)
    # ... tool calls ...
    await client.query(question_3)  # Adds to cache (schemas + Q1 + Q2 history)
    # Cache grows: 23k → 100k → 308k tokens
```

### Independent Mode (New):
```python
# Each question starts fresh
for question in questions:
    async with ClaudeSDKClient(options=options) as client:
        await client.query(question)  # Only this question, no history
        # ... tool calls ...
    # Client closes - no state persists
    # Next question starts completely fresh
    # Cache stays constant: 14k tokens per question
```

## Key Differences

| Aspect | Standard Mode | Independent Mode |
|--------|--------------|------------------|
| **Conversation** | Accumulates across questions | Isolated per question |
| **Cache growth** | Grows with each question | Stays constant |
| **Use case** | Multi-turn conversations | Single-question evaluation |
| **Cost** | High (accumulation) | Low (optimal reuse) |
| **Suitable for** | Research conversations | Benchmark testing |

## What Gets Cached?

### Both Modes Cache:
- ✅ MCP tool schemas (~14k tokens)
- ✅ System prompt (~500 tokens)

### Only Standard Mode Caches:
- ⚠️ Previous questions
- ⚠️ Previous answers
- ⚠️ Previous tool calls
- ⚠️ Previous tool results

This is why standard mode costs 4x more in cache!

## Testing Independent Mode

Run a small test first:

```bash
# Create a test file with 3 questions
cat > test_3questions.json << 'EOFTEST'
[
  {
    "id": 1,
    "question": "What is the UniProt ID for Cas9?",
    "category": "Precision",
    "expected_answer": "Q99ZW2"
  },
  {
    "id": 2,
    "question": "What is the molecular weight of caffeine?",
    "category": "Precision",
    "expected_answer": "194.19"
  },
  {
    "id": 3,
    "question": "What organism produces tetrodotoxin?",
    "category": "Precision",
    "expected_answer": "pufferfish"
  }
]
EOFTEST

# Run independent mode
python automated_test_runner_independent.py test_3questions.json -o test_results.csv

# Check cache pattern
python << 'EOFPY'
import csv
with open('test_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, 1):
        create = int(row.get('togomcp_cache_creation_input_tokens', 0))
        read = int(row.get('togomcp_cache_read_input_tokens', 0))
        print(f"Q{i}: create={create:,}, read={read:,}")
EOFPY
```

**Expected output:**
```
Q1: create=14,000, read=0       ← Cache created
Q2: create=0, read=14,000       ← Cache reused!
Q3: create=0, read=14,000       ← Cache reused!
```

If you see this pattern, it's working! 🎉

## When to Use Which Mode?

### Use Independent Mode When:
- ✅ Running benchmark evaluations
- ✅ Testing individual questions
- ✅ Cost is a concern
- ✅ Questions are unrelated
- ✅ You want consistent per-question metrics

### Use Standard Mode When:
- 🔄 Questions build on each other
- 🔄 Testing conversation flow
- 🔄 Multi-turn interactions needed
- 🔄 Context accumulation is desired
- 🔄 Cost is not a constraint

## Troubleshooting

### If cache still accumulates:
1. Check you're using the `_independent.py` script
2. Verify each question gets fresh client (check logs)
3. Ensure no shared state between questions

### If cache is never reused:
1. Check system prompt is identical between questions
2. Verify MCP server URLs are same
3. May need to wait between questions for cache to settle

## Summary

- ✅ Created `automated_test_runner_independent.py`
- ✅ Ensures complete question isolation
- ✅ Expected: 76% cost reduction
- ✅ Cache pattern: CREATE once, READ thereafter
- ✅ Same evaluation quality, much lower cost

**Recommendation**: Use independent mode for your 24-question benchmark. You'll save ~$2 per run while getting the same quality results!
