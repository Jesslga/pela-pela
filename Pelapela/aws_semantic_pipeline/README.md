
# AWS Semantic Concept Pipeline

A cutting-edge, agent-driven concept mapping system using AWS Bedrock Agents and OpenSearch Serverless for intelligent Japanese learning concept discovery.

## 🎯 Vision

Replace manual concept mapping with an AI agent that:
- **Automatically discovers** semantic relationships in Japanese learning data
- **Dynamically generates** concept nodes using contextual reasoning
- **Scales infinitely** as your data grows
- **Provides explainable** concept groupings and learning paths

## 🏗️ Architecture

```
Raw Data → S3 → Bedrock Agent → OpenSearch Serverless → Dynamic Concept Network
   ↓         ↓         ↓              ↓                    ↓
JLPT/Anki/  Store    Extract &    Vector Search &    Real-time
Duo/Tae Kim  Data    Embed        Similarity         Learning Paths
```

## 🚀 Core Components

### 1. **Data Ingestion Layer**
- **S3 Buckets**: Store raw scraped data from all sources
- **EventBridge**: Trigger processing on new data
- **Lambda**: Pre-process and validate data

### 2. **AI Agent Layer (Bedrock)**
- **Claude 3.5 Sonnet**: Japanese language understanding
- **Custom Agent**: Concept extraction and normalization
- **Embedding Model**: Generate semantic vectors

### 3. **Vector Database (OpenSearch Serverless)**
- **Vector Search**: Fast similarity queries
- **Metadata Storage**: Rich concept information
- **Real-time Updates**: Dynamic concept expansion

### 4. **Query & Visualization Layer**
- **API Gateway**: RESTful concept queries
- **Lambda Functions**: Graph generation
- **Web Interface**: Interactive concept exploration

## 📊 Data Flow

### Phase 1: Concept Extraction
```
Raw Title → Agent Analysis → Normalized Concept → Vector Embedding → OpenSearch Index
"は (topic marker)" → "Topic Particle は" → "Basic Grammar: Topic Markers" → [0.1, 0.8, ...] → Concept Node
```

### Phase 2: Dynamic Querying
```
User Query → Vector Search → Similar Concepts → Agent Reasoning → Learning Path
"Show me concepts like は" → [は, が, を, ...] → "These are all particles" → "Start with は, then learn が"
```

## 💰 Cost Estimation

| Service | Monthly Cost (1K concepts) | Monthly Cost (10K concepts) |
|---------|---------------------------|----------------------------|
| OpenSearch Serverless | ~$15-30 | ~$50-100 |
| Bedrock Agents | ~$20-50 | ~$100-200 |
| S3 Storage | ~$1-5 | ~$5-10 |
| Lambda/API Gateway | ~$5-15 | ~$10-25 |
| **Total** | **~$40-100** | **~$165-335** |

## 🎯 Benefits Over Current Approach

### ✅ **Intelligence**
- **Contextual Understanding**: Agent understands Japanese grammar nuances
- **Dynamic Discovery**: Finds relationships you might miss
- **Explainable**: Shows why concepts are grouped together

### ✅ **Scalability**
- **Auto-scaling**: Handles any amount of data
- **Real-time**: Updates as new data arrives
- **Multi-source**: Integrates any Japanese learning content

### ✅ **User Experience**
- **Natural Queries**: "Show me concepts like X"
- **Learning Paths**: AI-generated study sequences
- **Interactive**: Real-time concept exploration

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up AWS infrastructure
- [ ] Create OpenSearch Serverless domain
- [ ] Build basic data ingestion pipeline
- [ ] Implement simple concept extraction

### Phase 2: AI Integration (Week 3-4)
- [ ] Configure Bedrock Agent
- [ ] Design concept extraction prompts
- [ ] Implement vector embedding pipeline
- [ ] Test with sample data

### Phase 3: Advanced Features (Week 5-6)
- [ ] Add similarity search
- [ ] Implement learning path generation
- [ ] Build web interface
- [ ] Performance optimization

### Phase 4: Production (Week 7-8)
- [ ] Full data migration
- [ ] Monitoring and alerting
- [ ] Documentation and training
- [ ] Go live!

## 🔧 Technical Details

### OpenSearch Schema
```json
{
  "concept": {
    "id": "unique_id",
    "title": "Normalized concept title",
    "original_titles": ["は", "topic marker は", "は (topic)"],
    "embedding": [0.1, 0.8, 0.3, ...],
    "category": "grammar",
    "difficulty": "N5",
    "sources": ["JLPT", "Tae Kim"],
    "examples": ["私は学生です", "これは本です"],
    "related_concepts": ["が", "を", "に"],
    "metadata": {
      "agent_reasoning": "This is a basic topic particle...",
      "confidence": 0.95,
      "extraction_date": "2024-01-01"
    }
  }
}
```

### Agent Prompt Template
```
You are a Japanese language learning expert. Analyze the following Japanese concept titles and:

1. Normalize them into a clear, consistent format
2. Categorize them (grammar, vocabulary, kanji, etc.)
3. Determine their JLPT level
4. Identify related concepts
5. Provide a brief explanation

Titles: {input_titles}

Format your response as JSON:
{
  "normalized_title": "...",
  "category": "...",
  "jlpt_level": "N5",
  "related_concepts": ["...", "..."],
  "explanation": "...",
  "confidence": 0.95
}
```

## 🛠️ Getting Started

1. **Prerequisites**:
   ```bash
   # Install AWS CLI and configure credentials
   aws configure
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

2. **Deploy Infrastructure**:
   ```bash
   cd infrastructure
   terraform init
   terraform apply
   ```

3. **Run Concept Extraction**:
   ```bash
   python extract_concepts.py --source jlpt --data-path ../JLPT/
   ```

4. **Query Concepts**:
   ```bash
   python query_concepts.py --query "topic particles"
   ```

## 📚 Documentation

- [Infrastructure Setup](./infrastructure/README.md)
- [Agent Configuration](./agents/README.md)
- [API Reference](./api/README.md)
- [Cost Optimization](./docs/cost-optimization.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

---

**Ready to revolutionize your Japanese learning concept network? Let's build this! 🚀** 