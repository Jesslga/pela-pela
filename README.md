# Pelapela - Japanese Learning Network

## Quick Start - Launch the Network

To visualize the PelaPela  network:

1. **Run the data pipeline** to generate clean data:
   ```bash
   python3 pipeline/data_pipeline.py
   ```

2. **Build the network** from the clean data:
   ```bash
   python3 pipeline/build_network.py
   ```

3. **Open the network visualization** in your browser:
   ```bash
   open network_output/index.html
   ```
   
   Or navigate to `network_output/index.html` in your web browser.

---

## ✅ Reproduce Results and Evaluation

Generate the network JSON and open the visualization (above). To run the baseline evaluation (no annotations required):

```bash
python3 evaluation/evaluate_network.py
```

This prints precision (heuristic), direction accuracy, Cohen’s κ (proxy), core coverage (%), orphans share, main-component share, and reproducibility (edge Jaccard). To get JSON:

```bash
python3 evaluation/evaluate_network.py --json
```

Optional: provide a reproducibility baseline by copying the current edges before a rebuild:

```bash
cp network_output/edges.json network_output/edges_prev.json
```

For human-judged correctness, use the notebook `evaluation/EvaluateNetwork.ipynb` to export an annotation CSV, collect labels, and compute precision with 95% CIs and κ.

---

## Project Structure

### Pipeline Files
- **`pipeline/data_pipeline.py`** - Main data processing pipeline that:
  - Loads raw JSON data from `data/raw/`
  - Cleans and normalizes the data according to schemas
  - **Enhanced POS detection** using spaCy (ja-ginza) and rule-based fallbacks
  - **Improved data cleaning** with better example filtering and validation
  - **Unified JLPT data processing** for better grammar pattern extraction
  - Outputs clean, validated data to `data/clean/`
  - Handles JLPT, Duolingo, and Anki data sources

- **`pipeline/build_network.py`** - Network construction script that:
  - Reads clean data from `data/clean/`
  - **Creates meaningful connections** based on JLPT levels, parts of speech, and semantic relationships
  - **Enhanced edge creation** with weighted relationships and intelligent clustering
  - **Guidebook lesson enrichment** with contextual information and examples
  - Builds a graph structure connecting grammar patterns and vocabulary
  - Exports network data to `network_output/` for visualization

### Data Files

#### Raw Data (`data/raw/`)
- **`jlpt_raw.json`** - Japanese Language Proficiency Test grammar and vocabulary data
- **`duo_raw.json`** - Duolingo Japanese course guidebook content
- **`anki_raw.json`** - Anki flashcard deck data for Japanese learning

#### Clean Data (`data/clean/`)
- **`grammar_pattern.json`** - Processed and validated grammar patterns
- **`vocabulary_entry.json`** - Processed and validated vocabulary entries

#### Network Output (`network_output/`)
- **`nodes.json`** - Network nodes (grammar patterns and vocabulary)
- **`edges.json` - Network connections between nodes with weighted relationships
- **`index.html`** - Interactive network visualization

### Evaluation (`evaluation/`)
- **`evaluate_network.py`** - CLI evaluator that prints all metrics as numbers (no NaN), using only project files
- **`EvaluateNetwork.ipynb`** - Optional notebook for deeper analysis and annotation workflows

### Schema Files (`schemas/`)
- **`grammar_pattern.schema.json`** - JSON schema for grammar pattern validation
- **`vocabulary_entry.schema.json`** - JSON schema for vocabulary entry validation

---

## Requirements

Install dependencies:
```bash
pip install -r requirements.txt
```

Required packages (see `requirements.txt`):
- `spacy` and `ja-ginza` for POS detection
- `jsonschema` for schema validation
- `networkx` for evaluation metrics
- `matplotlib` (optional; for figures if you extend evaluation)

---

## Data Processing Flow

1. **Raw Data Loading** → Loads JSON files from `data/raw/`
2. **Data Cleaning** → Normalizes and validates against schemas
   - **Enhanced POS Detection** → Uses spaCy + rule-based fallbacks for accurate part-of-speech tagging
   - **Improved Example Filtering** → Removes fragments and duplicates, preserves meaningful examples
   - **Better Validation** → Comprehensive schema validation with detailed error reporting
3. **Data Merging** → Combines data from multiple sources with deduplication
4. **Network Building** → Creates intelligent graph structure with meaningful connections
   - **JLPT Level Connections** → Links related grammar patterns and vocabulary by proficiency level
   - **Semantic Relationships** → Connects items with similar meanings and usage patterns
   - **Cross-Reference Links** → Links vocabulary that appears in grammar examples
5. **Visualization** → Generates interactive network view with rich node content

---

## Recent Improvements

### Enhanced Data Processing
- **Better POS Detection**: Improved part-of-speech tagging using spaCy and rule-based fallbacks
- **Smarter Example Filtering**: Removes incomplete examples and preserves meaningful content
- **Unified JLPT Processing**: Better handling of JLPT data structure for improved grammar extraction

### Improved Network Building
- **Meaningful Connections**: Creates relationships based on JLPT levels, parts of speech, and semantic similarity
- **Weighted Edges**: Assigns importance weights to different types of connections
- **Guidebook Enrichment**: Adds contextual information and examples to lesson nodes
- **Intelligent Clustering**: Groups related items by difficulty level and part of speech

### Better Data Quality
- **Comprehensive Validation**: Full schema validation with detailed error reporting
- **Deduplication**: Removes duplicate entries across data sources
- **Quality Filtering**: Drops incomplete or corrupted entries

---

## Data Access Statement

This project reads:
- Raw JSON in `data/raw/` (e.g., `jlpt_raw.json`, `anki_raw.json`, `duo_raw.json`) provided locally by the user. Do not redistribute without permission of the data owners.

Clean outputs are written to `data/clean/grammar_pattern.json` and `data/clean/vocabulary_entry.json` and are derived works intended for local use.

Licensing: Raw data remains owned by its respective providers (e.g., JLPT sources, Duolingo, Anki decks). This repository does not redistribute proprietary datasets. Verify rights before sharing derived artifacts.

---

## Clean Code & Security

- No absolute paths; project root is discovered at runtime.
- No API keys or secrets are stored in this repo.
- Unused bytecode caches are ignored.
- Evaluation and pipeline scripts rely on local files only.

---

## Attribution

- All code in this repository was authored for this project, except standard library usage and open-source libraries listed in `requirements.txt`.
- If you reuse code from external sources, add an inline attribution comment above the reused block and ensure the source license permits reuse.
- **Development Tools**: This project was developed using [Cursor](https://cursor.sh/) (AI-powered code editor) and [ChatGPT](https://chat.openai.com/) (AI assistant) for code generation, debugging, and development assistance.
