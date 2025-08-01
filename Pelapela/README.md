# Japanese Language Learning Concept Network

A streamlined hybrid system for processing Japanese learning data locally and leveraging AWS for semantic concept analysis.

## 🏗️ Architecture

```
Local Data Processing → AWS Semantic Pipeline → Concept Network
       ↓                       ↓                    ↓
   Clean & Normalize      Semantic Analysis     Learning Paths
```

## 📁 Project Structure

```
Pelapela/
├── 📊 data_sources/              # Local data processing (4 sources)
│   ├── anki/
│   │   ├── normalize_anki_data.py
│   │   └── anki_concepts_for_network.json
│   ├── jlpt/
│   │   ├── normalize_jlpt_data.py
│   │   └── jlpt_concepts_for_network.json
│   ├── taekim/
│   │   ├── normalize_taekim_data.py
│   │   └── taekim_concepts_for_network.json
│   └── duo/
│       ├── normalize_duo_data.py
│       └── duo_concepts_for_network.json
├── 🌉 aws_bridge/               # Local ↔ AWS integration
│   └── prepare_for_aws.py       # Upload local data to AWS
├── ☁️ aws_semantic_pipeline/     # AWS cloud processing
│   ├── deploy.py                # Deploy infrastructure
│   ├── demo.py                  # Test pipeline
│   ├── lambda/
│   │   ├── concept_extractor.py
│   │   └── concept_query.py
│   ├── services/
│   │   └── semantic_deduplicator.py
│   ├── schema/
│   │   └── unified_concept_schema.py
│   └── infrastructure/
│       └── main.tf
├── 🕸️ network/                  # Visualization
│   ├── app.py                   # Web viewer
│   ├── unified_network_manager.py
│   └── enhanced_network_viewer.html
├── 🔧 config.py                 # Database config
├── 📊 enhanced_data_loader.py   # Data utilities
└── 🏗️ models.py                 # Database models
```

## 🚀 Quick Start

### 1. Process Data Sources Locally
```bash
# Process each data source
cd data_sources/anki && python normalize_anki_data.py
cd ../jlpt && python normalize_jlpt_data.py  
cd ../taekim && python normalize_taekim_data.py
cd ../duo && python normalize_duo_data.py
```

### 2. Prepare for AWS Upload
```bash
cd aws_bridge/
python prepare_for_aws.py --upload --environment dev
```

### 3. Deploy AWS Infrastructure
```bash
cd aws_semantic_pipeline/
python deploy.py --environment dev
```

### 4. View Results
```bash
cd network/
python app.py  # Start web viewer
# Or open enhanced_network_viewer.html
```

## 📊 Data Flow

1. **Local Processing**: Each source (Anki, JLPT, Tae Kim, Duo) normalizes its data
2. **AWS Bridge**: Combines all local data and uploads to S3
3. **AWS Pipeline**: Processes data with Bedrock AI and OpenSearch
4. **Visualization**: View semantic concept networks and relationships

## 🎯 Key Features

- **4 Data Sources**: JLPT, Anki, Tae Kim, Duolingo
- **Semantic Deduplication**: AWS Bedrock intelligently merges similar concepts
- **Vector Search**: OpenSearch Serverless for fast similarity queries
- **Interactive Visualization**: Web-based concept network exploration
- **Scalable**: Cloud-based processing for unlimited data growth

## 🔧 Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r aws_semantic_pipeline/requirements.txt
```
