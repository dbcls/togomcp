# LLM-Based Evaluation Guide

This guide explains how to use the `add_llm_evaluation.py` script to add LLM-based evaluation to existing evaluation results.

## Prerequisites

### 1. Install Ollama

Ollama is required to generate embeddings locally.

**Windows:**
```powershell
winget install Ollama.Ollama
```

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or download directly from: https://ollama.com/download

### 2. Start Ollama Server

After installation, ensure Ollama is running:

```bash
ollama serve
```

On Windows, Ollama typically starts automatically after installation.

### 3. Download a Generative LLM

Pull a generative model like `llama3.2`:

```bash
ollama pull llama3.2
```

### 4. Install Python Dependencies

```bash
pip install ollama pandas
```

## Usage

### Basic Usage

Process a single CSV file:

```bash
python add_llm_evaluation.py ../results/Q01_out.csv -o ../results/Q01_with_llm_evaluation.csv
```

### Modify In-Place

Update the original file directly:

```bash
python add_llm_evaluation.py ../results/Q01_out.csv
```

### Use Different Model

Use an alternative model:

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv --llm-model mistral
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output CSV file path (only for single input) |
| `--llm-model` | Ollama generative model for LLM evaluation (e.g., llama3.2, mistral) |
| `-q, --quiet` | Suppress progress output |
| `--no-summary` | Don't print summary statistics |

## Output Columns

| Column | Description |
|--------|-------------|
| `baseline_llm_match` | True if LLM judges baseline contains the expected answer |
| `baseline_llm_confidence` | LLM confidence level: high, medium, or low |
| `baseline_llm_explanation` | Brief explanation from LLM about the match decision |
| `togomcp_llm_match` | True if LLM judges TogoMCP contains the expected answer |
| `togomcp_llm_confidence` | LLM confidence level: high, medium, or low |
| `togomcp_llm_explanation` | Brief explanation from LLM about the match decision |
| `full_combined_baseline_found` | True if token OR semantic OR LLM match for baseline |
| `full_combined_togomcp_found` | True if token OR semantic OR LLM match for TogoMCP |

## How LLM Evaluation Works

The LLM evaluator sends a structured prompt to the generative model asking it to determine if the response text contains the expected answer. The LLM returns:

- **MATCH**: YES or NO
- **CONFIDENCE**: HIGH, MEDIUM, or LOW
- **REASON**: A brief explanation

This is useful because:
1. **Semantic understanding**: LLMs can understand paraphrasing and different ways of expressing the same information
2. **Context awareness**: Can identify if the core information is present even with additional details
3. **Complements embeddings**: Catches matches that embedding similarity might miss