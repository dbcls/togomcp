#!/bin/bash
# Quick Start Script for TogoMCP Evaluation with Agent SDK

set -e

echo "============================================="
echo "TogoMCP Evaluation - Agent SDK Quick Start"
echo "============================================="
echo ""

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set"
    echo ""
    echo "Please set your API key:"
    echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
    echo ""
    exit 1
fi

echo "✓ API key found"

# Check if claude-agent-sdk is installed
if ! python3 -c "import claude_agent_sdk" 2>/dev/null; then
    echo ""
    echo "📦 Installing required packages..."
    pip install -r requirements.txt
else
    echo "✓ claude-agent-sdk installed"
fi

# Check if anthropic is installed
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "📦 Installing anthropic..."
    pip install anthropic
else
    echo "✓ anthropic installed"
fi

echo ""
echo "Running evaluation with example questions..."
echo ""

# Run the test runner
python3 automated_test_runner.py example_questions.json

echo ""
echo "============================================="
echo "Evaluation Complete!"
echo "============================================="
echo ""
echo "Results saved to: evaluation_results.csv"
echo ""
echo "Next steps:"
echo "  1. Review: open evaluation_results.csv"
echo "  2. Check tools_used column for MCP tool names"
echo "  3. Compare baseline_text vs togomcp_text"
echo "  4. Create your own questions: cp example_questions.json my_questions.json"
echo ""
echo "Documentation:"
echo "  - README.md - Full usage guide"
echo "  - MCP_CONFIGURATION.md - MCP server setup"
echo "  - CORRECTION_SUMMARY.md - What changed from scripts/"
echo ""
