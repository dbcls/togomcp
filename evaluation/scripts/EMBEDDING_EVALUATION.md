# Embedding and LLM-Based Evaluation Guide

This guide explains how to use the `add_embedding_and_llm_evaluation.py` script to add semantic similarity scores and LLM-based evaluation to existing evaluation results.

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

### 3. Download the Embedding Model

Pull the `nomic-embed-text` model (recommended for semantic similarity):

```bash
ollama pull nomic-embed-text
```

This model is ~274MB and provides high-quality embeddings for text similarity tasks.

### 4. Download a Generative LLM

For LLM-based evaluation, pull a generative model like `llama3.2`:

```bash
ollama pull llama3.2
```

### 5. Install Python Dependencies

```bash
pip install ollama scikit-learn numpy pandas
```

## Usage

### Basic Usage

Process a single CSV file and save with embeddings:

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv -o ../results/Q01_with_embeddings.csv
```

### Modify In-Place

Update the original file directly:

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv --inplace
```

### Process Multiple Files

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv ../results/Q02_out.csv ../results/Q11_out.csv
```

### Custom Threshold

Adjust the semantic similarity threshold (default: 0.75):

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv -t 0.6
```

### Use Different Model

Use an alternative Ollama embedding model:

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv -m mxbai-embed-large
```

### With LLM Evaluation

Add generative LLM evaluation (llama3.2):

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv --llm-model llama3.2
```

## With Embeddings and LLM Evaluation

```bash
python add_embedding_and_llm_evaluation.py ../results/Q01_out.csv --llm-model llama3.2 -o ../results/Q01_with_embeddings_and_llm.csv
```

This will process the file `Q01_out.csv`, add the semantic similarity columns and LLM evaluation using the `llama3.2` model, and save the result to `Q01_with_embeddings_and_llm.csv`.

## Command Line Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output CSV file path (only for single input) |
| `-t, --threshold` | Semantic similarity threshold (0.0-1.0, default: 0.75) |
| `-m, --model` | Ollama embedding model (default: nomic-embed-text) |
| `--llm-model` | Ollama generative model for LLM evaluation (e.g., llama3.2, mistral) |
| `--inplace` | Modify input files in place |
| `-q, --quiet` | Suppress progress output |
| `--no-summary` | Don't print summary statistics |

## Output Columns

### Embedding-Based Columns

The script adds the following columns to the CSV:

| Column | Description |
|--------|-------------|
| `baseline_semantic_similarity` | Cosine similarity between baseline response and expected answer (0.0-1.0) |
| `baseline_semantic_found` | True if similarity >= threshold |
| `togomcp_semantic_similarity` | Cosine similarity between TogoMCP response and expected answer (0.0-1.0) |
| `togomcp_semantic_found` | True if similarity >= threshold |
| `combined_baseline_found` | True if token-based OR semantic match found for baseline |
| `combined_togomcp_found` | True if token-based OR semantic match found for TogoMCP |
| `baseline_max_confidence` | Maximum of token confidence and semantic similarity |
| `togomcp_max_confidence` | Maximum of token confidence and semantic similarity |

### LLM-Based Columns 

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