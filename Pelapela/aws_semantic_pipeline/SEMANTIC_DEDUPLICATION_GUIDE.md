# Semantic Deduplication System for Japanese Learning Concepts

## Overview

This system provides intelligent semantic deduplication for Japanese language learning concepts from multiple sources (Duolingo, Anki, JLPT, Tae Kim, etc.). Instead of relying on exact string matching, it uses vector embeddings and semantic similarity to identify and merge related concepts.

## Key Features

- **Semantic Similarity**: Uses AWS Bedrock embeddings to find conceptually similar concepts
- **Intelligent Merging**: Combines metadata from multiple sources intelligently
- **Unified Schema**: Consistent data format across all sources
- **Source Tracking**: Maintains full traceability of concept origins
- **Configurable Thresholds**: Adjustable similarity thresholds for different use cases

## Architecture

```
Data Sources → Unified Schema → Vector Embeddings → Semantic Search → Intelligent Merging → OpenSearch
     ↓              ↓              ↓                ↓                ↓              ↓
  Duolingo    UnifiedConcept   Bedrock Titan   OpenSearch KNN    Merge Logic   Vector Store
  Anki        Validation       Embeddings      Vector Search     Source Merge   + Metadata
  JLPT        Normalization    (1536 dim)      (Cosine Sim)      JLPT Logic     + Relationships
  Tae Kim     Type Mapping     Japanese Text   Threshold Filter  Tag Union      + Examples
```

## Components

### 1. Unified Schema (`schema/unified_concept_schema.py`)

Defines the standard format for all concepts:

```python
@dataclass
class UnifiedConcept:
    concept_title: str          # Normalized concept name
    concept_type: str           # verb, noun, grammar, etc.
    description: str            # English explanation
    jlpt_level: Optional[str]   # N5, N4, N3, N2, N1
    example_sentences: List[str] # Japanese examples
    english_translations: List[str] # English translations
    tags: List[str]             # Related concepts, categories
    sources: List[str]          # ["Duolingo", "Anki", etc.]
    source_ids: Dict[str, str]  # {"Duolingo": "card_123"}
    confidence: float           # 0.0-1.0 confidence score
    embedding: Optional[List[float]] # Vector embedding
```

### 2. Semantic Deduplicator (`services/semantic_deduplicator.py`)

Core deduplication service with these key methods:

- `find_semantic_duplicates()`: Find similar concepts using vector search
- `merge_duplicate_concepts()`: Intelligently merge concept metadata
- `process_concept_with_deduplication()`: Complete workflow for single concept
- `batch_process_concepts()`: Process multiple concepts efficiently

### 3. Lambda Integration (`lambda/concept_extractor.py`)

Updated Lambda function that:
- Converts incoming data to unified schema
- Uses semantic deduplication when available
- Falls back to simple processing if needed
- Updates OpenSearch index mapping for unified schema

## Usage Examples

### Basic Concept Creation

```python
from schema.unified_concept_schema import UnifiedConcept

# Create a concept from Duolingo
duolingo_concept = UnifiedConcept(
    concept_title="食べる",
    concept_type="verb",
    description="to eat",
    jlpt_level="N5",
    example_sentences=["私はリンゴを食べる。"],
    sources=["Duolingo"],
    source_ids={"Duolingo": "card_123"}
)
```

### Semantic Deduplication

```python
from services.semantic_deduplicator import SemanticDeduplicator

# Initialize deduplicator
deduplicator = SemanticDeduplicator(
    opensearch_endpoint="your-opensearch-endpoint",
    region='us-east-1'
)

# Process a concept
result = deduplicator.process_concept_with_deduplication(concept)

if result['status'] == 'merged':
    print(f"Merged with similarity: {result['similarity_score']:.3f}")
elif result['status'] == 'inserted':
    print("Inserted as new concept")
```

### Batch Processing

```python
# Process multiple concepts
concepts = [concept1, concept2, concept3]
results = deduplicator.batch_process_concepts(concepts)

print(f"Inserted: {results['inserted']}")
print(f"Merged: {results['merged']}")
print(f"Errors: {results['errors']}")
```

## Configuration

### Similarity Thresholds

Adjust the similarity threshold in `SemanticDeduplicator`:

```python
# More strict (fewer merges)
self.similarity_threshold = 0.90

# More lenient (more merges)
self.similarity_threshold = 0.80
```

### Embedding Model

The system uses AWS Bedrock Titan Embeddings by default:

```python
# In semantic_deduplicator.py
response = self.bedrock.invoke_model(
    modelId='amazon.titan-embed-text-v1',
    body=json.dumps({
        'inputText': text_to_embed
    })
)
```

## Merging Logic

### Concept Merging Rules

1. **Title**: Keep the original title
2. **Type**: Keep the original type
3. **Description**: Keep the original description (could be enhanced)
4. **JLPT Level**: Keep the more advanced level (N1 > N2 > N3 > N4 > N5)
5. **Examples**: Combine all unique examples
6. **Tags**: Union of all tags
7. **Sources**: Combine all sources
8. **Source IDs**: Merge source ID mappings
9. **Confidence**: Keep the highest confidence score
10. **Embedding**: Use the better embedding (higher confidence wins)

### Example Merge

**Original Concept 1 (Duolingo):**
```json
{
  "concept_title": "食べる",
  "jlpt_level": "N5",
  "example_sentences": ["私はリンゴを食べる。"],
  "sources": ["Duolingo"],
  "confidence": 0.9
}
```

**Original Concept 2 (Anki):**
```json
{
  "concept_title": "食べる", 
  "jlpt_level": "N4",
  "example_sentences": ["彼は寿司を食べる。"],
  "sources": ["Anki"],
  "confidence": 0.85
}
```

**Merged Result:**
```json
{
  "concept_title": "食べる",
  "jlpt_level": "N4",  // More advanced level
  "example_sentences": ["私はリンゴを食べる。", "彼は寿司を食べる。"],
  "sources": ["Duolingo", "Anki"],
  "confidence": 0.9,   // Higher confidence
  "source_ids": {"Duolingo": "card_123", "Anki": "note_456"}
}
```

## Testing

### Run Basic Tests

```bash
cd aws_semantic_pipeline
python test_deduplication.py
```

### Test with Real Data

```bash
# Update file paths in upload_with_deduplication.py
python upload_with_deduplication.py
```

## Deployment

### Lambda Function Updates

1. **Add Dependencies**: Include schema and services in Lambda package
2. **Update Requirements**: Add any new dependencies to `requirements_lambda.txt`
3. **Deploy**: Update Lambda function with new code
4. **Test**: Verify deduplication works in production

### OpenSearch Index

The system automatically creates/updates the index with unified schema support:

```json
{
  "mappings": {
    "properties": {
      "concept_title": {"type": "text"},
      "concept_type": {"type": "keyword"},
      "description": {"type": "text"},
      "jlpt_level": {"type": "keyword"},
      "example_sentences": {"type": "text"},
      "sources": {"type": "keyword"},
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil"
        }
      }
    }
  }
}
```

## Performance Considerations

### Vector Search Optimization

- **Index Size**: OpenSearch Serverless handles scaling automatically
- **Search Results**: Limit to 10-20 results for efficiency
- **Batch Processing**: Process concepts in batches of 50-100

### Embedding Generation

- **Caching**: Consider caching embeddings for repeated concepts
- **Batch Embeddings**: Generate embeddings in batches when possible
- **Fallback**: Use zero vectors if embedding generation fails

## Monitoring and Debugging

### Logging

The system provides detailed logging:

```python
logger.info(f"Found {len(duplicates)} semantic duplicates")
logger.warning(f"Could not generate embedding for concept: {concept_title}")
logger.error(f"Error in semantic deduplication: {e}")
```

### Metrics

Track these key metrics:

- **Deduplication Rate**: Percentage of concepts that get merged
- **Similarity Scores**: Distribution of similarity scores
- **Processing Time**: Time per concept/batch
- **Error Rate**: Failed processing attempts

### Common Issues

1. **Import Errors**: Ensure schema and services are in Lambda package
2. **OpenSearch Connection**: Verify endpoint and credentials
3. **Bedrock Permissions**: Check IAM permissions for embedding generation
4. **Memory Issues**: Monitor Lambda memory usage with large batches

## Future Enhancements

### Planned Features

1. **Advanced Merging**: AI-powered description enhancement
2. **Clustering**: Automatic concept clustering for better organization
3. **Confidence Scoring**: ML-based confidence scoring
4. **Multi-language**: Support for other languages beyond Japanese
5. **Real-time Updates**: WebSocket-based real-time concept updates

### Customization Options

1. **Custom Embedding Models**: Support for different embedding models
2. **Domain-Specific Rules**: Custom merging rules for specific domains
3. **A/B Testing**: Compare different similarity thresholds
4. **Analytics Dashboard**: Web interface for monitoring and management

## Support

For issues or questions:

1. Check the logs for detailed error messages
2. Verify AWS credentials and permissions
3. Test with small batches first
4. Review the similarity threshold settings
5. Ensure all dependencies are properly installed

## Contributing

To contribute to the semantic deduplication system:

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Test with real data before submitting
5. Consider performance implications of changes 