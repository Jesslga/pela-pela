"""
Lambda function for extracting and embedding Japanese learning concepts
using AWS Bedrock and OpenSearch Serverless.
"""

import json
import boto3
import logging
import os
from typing import Dict, List, Any
from datetime import datetime
import requests
from requests_aws4auth import AWS4Auth
import sys
import os

# Add the schema and services to the path
sys.path.append('/opt/python/lib/python3.9/site-packages')
sys.path.append('/opt/python')

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
s3 = boto3.client('s3')
opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
s3_bucket = os.environ['S3_BUCKET']
project_name = os.environ['PROJECT_NAME']

# OpenSearch authentication
session = boto3.Session()
credentials = session.get_credentials()
region = session.region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'aoss', session_token=credentials.token)

# Try to import semantic deduplication components
try:
    from schema.unified_concept_schema import UnifiedConcept, ConceptSchemaValidator
    from services.semantic_deduplicator import SemanticDeduplicator
    SEMANTIC_DEDUP_AVAILABLE = True
    logger.info("Semantic deduplication components loaded successfully")
except ImportError as e:
    logger.warning(f"Semantic deduplication components not available: {e}")
    SEMANTIC_DEDUP_AVAILABLE = False

class ConceptExtractor:
    """Extracts and processes Japanese learning concepts using AI agents"""
    
    def __init__(self):
        self.bedrock_client = bedrock
        self.opensearch_endpoint = opensearch_endpoint
        self.awsauth = awsauth
    
    def extract_concepts_from_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract concepts from raw data using Bedrock agent
        
        Args:
            data: List of raw data items with titles
            
        Returns:
            List of processed concepts
        """
        concepts = []
        
        # Group data by source for batch processing
        sources = {}
        for item in data:
            source = item.get('source', 'unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(item)
        
        # Process each source
        for source, items in sources.items():
            logger.info(f"Processing {len(items)} items from {source}")
            
            # Extract titles for this source
            titles = [item.get('title', '') for item in items if item.get('title')]
            
            if not titles:
                continue
            
            # Use Bedrock to analyze titles
            try:
                processed_concepts = self._analyze_titles_with_bedrock(titles, source)
                concepts.extend(processed_concepts)
            except Exception as e:
                logger.error(f"Error processing {source}: {e}")
                # Fallback to simple processing
                concepts.extend(self._simple_concept_processing(items, source))
        
        return concepts
    
    def _analyze_titles_with_bedrock(self, titles: List[str], source: str) -> List[Dict[str, Any]]:
        """
        Use Bedrock to analyze Japanese titles and extract concepts
        
        Args:
            titles: List of Japanese titles
            source: Source of the data
            
        Returns:
            List of processed concepts
        """
        # Prepare prompt for Bedrock
        prompt = self._create_analysis_prompt(titles)
        
        # Call Bedrock
        try:
            response = self.bedrock_client.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Parse the response
            concepts = self._parse_bedrock_response(content, titles, source)
            return concepts
            
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            # Fallback to simple processing with embeddings
            return self._simple_concept_processing_with_embeddings(titles, source)
    
    def _create_analysis_prompt(self, titles: List[str]) -> str:
        """Create a prompt for Bedrock to analyze Japanese titles"""
        
        titles_text = "\n".join([f"- {title}" for title in titles[:50]])  # Limit to 50 titles
        
        prompt = f"""
You are a Japanese language learning expert. Analyze the following Japanese concept titles and extract meaningful concepts.

For each title, provide:
1. A normalized, clear concept name
2. Category (grammar, vocabulary, kanji, culture, etc.)
3. JLPT level (N5, N4, N3, N2, N1)
4. Related concepts
5. Brief explanation
6. Confidence score (0.0-1.0)

Titles to analyze:
{titles_text}

Format your response as a JSON array:
[
  {{
    "original_title": "は (topic marker)",
    "normalized_title": "Topic Particle は",
    "category": "grammar",
    "jlpt_level": "N5",
    "related_concepts": ["が", "を", "に"],
    "explanation": "Basic topic particle used to mark the subject of a sentence",
    "confidence": 0.95,
    "examples": ["私は学生です", "これは本です"]
  }}
]

Focus on:
- Normalizing similar concepts (e.g., "は (topic)" and "topic marker は" should be the same concept)
- Identifying grammar patterns and relationships
- Providing accurate JLPT levels
- Including relevant examples when possible
"""
        
        return prompt
    
    def _parse_bedrock_response(self, response: str, original_titles: List[str], source: str) -> List[Dict[str, Any]]:
        """Parse Bedrock response into concept objects"""
        concepts = []
        
        try:
            # Extract JSON from response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON array found in Bedrock response")
                return self._simple_concept_processing_from_titles(original_titles, source)
            
            json_str = response[start_idx:end_idx]
            parsed_concepts = json.loads(json_str)
            
            for concept_data in parsed_concepts:
                # Convert to unified schema if available
                if SEMANTIC_DEDUP_AVAILABLE:
                    concept = self._create_unified_concept(concept_data, source)
                else:
                    # Fallback to original format
                    concept = {
                        'id': f"{source}_{len(concepts)}",
                        'original_title': concept_data.get('original_title', ''),
                        'normalized_title': concept_data.get('normalized_title', ''),
                        'category': concept_data.get('category', 'unknown'),
                        'jlpt_level': concept_data.get('jlpt_level', 'N5'),
                        'related_concepts': concept_data.get('related_concepts', []),
                        'explanation': concept_data.get('explanation', ''),
                        'confidence': concept_data.get('confidence', 0.5),
                        'examples': concept_data.get('examples', []),
                        'source': source,
                        'extraction_date': datetime.now().isoformat(),
                        'agent_reasoning': response[:500]  # Store first 500 chars of reasoning
                    }
                    
                    # Generate embedding
                    concept['embedding'] = self._generate_embedding(concept['normalized_title'])
                
                concepts.append(concept)
        
        except Exception as e:
            logger.error(f"Error parsing Bedrock response: {e}")
            return self._simple_concept_processing_from_titles(original_titles, source)
        
        return concepts
    
    def _create_unified_concept(self, concept_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Create a unified concept from Bedrock response data"""
        try:
            # Create UnifiedConcept object
            unified_concept = UnifiedConcept(
                concept_title=concept_data.get('normalized_title', concept_data.get('original_title', '')),
                concept_type=concept_data.get('category', 'vocabulary'),
                description=concept_data.get('explanation', ''),
                jlpt_level=concept_data.get('jlpt_level', 'N5'),
                example_sentences=concept_data.get('examples', []),
                english_translations=[],  # Could be extracted from examples
                tags=concept_data.get('related_concepts', []),
                category=concept_data.get('category', 'vocabulary'),
                sources=[source],
                source_ids={source: f"{source}_{len(concept_data.get('original_title', ''))}"},
                confidence=concept_data.get('confidence', 0.5),
                extraction_date=datetime.now().isoformat(),
                original_metadata={
                    'original_title': concept_data.get('original_title', ''),
                    'related_concepts': concept_data.get('related_concepts', []),
                    'agent_reasoning': concept_data.get('explanation', '')[:500]
                }
            )
            
            # Generate embedding
            embedding = self._generate_embedding(unified_concept.concept_title)
            if embedding:
                unified_concept.embedding = embedding
            
            # Convert to dict for storage
            return unified_concept.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating unified concept: {e}")
            # Fallback to simple format
            return {
                'id': f"{source}_{len(concept_data.get('original_title', ''))}",
                'original_title': concept_data.get('original_title', ''),
                'normalized_title': concept_data.get('normalized_title', ''),
                'category': concept_data.get('category', 'unknown'),
                'jlpt_level': concept_data.get('jlpt_level', 'N5'),
                'related_concepts': concept_data.get('related_concepts', []),
                'explanation': concept_data.get('explanation', ''),
                'confidence': concept_data.get('confidence', 0.5),
                'examples': concept_data.get('examples', []),
                'source': source,
                'extraction_date': datetime.now().isoformat(),
                'agent_reasoning': concept_data.get('explanation', '')[:500],
                'embedding': self._generate_embedding(concept_data.get('normalized_title', ''))
            }
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Bedrock"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({
                    "inputText": text
                })
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body['embedding']
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536  # Titan embedding dimension
    
    def _simple_concept_processing_with_embeddings(self, titles: List[str], source: str) -> List[Dict[str, Any]]:
        """Simple processing with Titan embeddings for semantic deduplication"""
        concepts = []
        
        for i, title in enumerate(titles):
            # Generate embedding for semantic deduplication
            embedding = self._generate_embedding(title)
            
            concept = {
                'id': f"{source}_{i}",
                'original_title': title,
                'normalized_title': title,
                'category': 'unknown',
                'jlpt_level': 'N5',
                'embedding': embedding,
                'source': source,
                'extraction_date': datetime.now().isoformat()
            }
            
            # Convert to unified schema if available
            if SEMANTIC_DEDUP_AVAILABLE:
                try:
                    unified_concept = UnifiedConcept(
                        concept_title=title,
                        concept_type='vocabulary',
                        description=f"Concept from {source}: {title}",
                        jlpt_level='N5',
                        example_sentences=[],
                        english_translations=[],
                        tags=[],
                        category='vocabulary',
                        sources=[source],
                        source_ids={source: f"{source}_{i}"},
                        confidence=0.5,
                        extraction_date=datetime.now().isoformat(),
                        original_metadata={'original_title': title},
                        embedding=embedding
                    )
                    concept = unified_concept.to_dict()
                except Exception as e:
                    logger.error(f"Error creating unified concept: {e}")
                    # Keep the simple format if unified schema fails
            
            concepts.append(concept)
        
        return concepts
    
    def _simple_concept_processing_from_titles(self, titles: List[str], source: str) -> List[Dict[str, Any]]:
        """Simple fallback processing when Bedrock fails"""
        concepts = []
        
        for i, title in enumerate(titles):
            concept = {
                'id': f"{source}_{i}",
                'original_title': title,
                'normalized_title': title,
                'category': 'unknown',
                'jlpt_level': 'N5',
                'related_concepts': [],
                'explanation': f'Concept from {source}',
                'confidence': 0.3,
                'examples': [],
                'source': source,
                'extraction_date': datetime.now().isoformat(),
                'agent_reasoning': 'Simple fallback processing'
            }
            
            # Generate simple embedding
            concept['embedding'] = self._generate_embedding(title)
            concepts.append(concept)
        
        return concepts
    
    def _simple_concept_processing(self, items: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """Simple processing for raw data items"""
        concepts = []
        
        for i, item in enumerate(items):
            title = item.get('title', f'Concept {i}')
            concept = {
                'id': f"{source}_{i}",
                'original_title': title,
                'normalized_title': title,
                'category': item.get('type', 'unknown'),
                'jlpt_level': item.get('level', 'N5'),
                'related_concepts': [],
                'explanation': item.get('meaning', f'Concept from {source}'),
                'confidence': 0.3,
                'examples': item.get('examples', []),
                'source': source,
                'extraction_date': datetime.now().isoformat(),
                'agent_reasoning': 'Simple fallback processing'
            }
            
            # Generate embedding
            concept['embedding'] = self._generate_embedding(title)
            concepts.append(concept)
        
        return concepts
    
    def store_concepts_in_opensearch(self, concepts: List[Dict[str, Any]]) -> bool:
        """
        Store concepts in OpenSearch Serverless with semantic deduplication
        
        Args:
            concepts: List of concept objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create index if it doesn't exist
            self._create_index_if_not_exists()
            
            # Use semantic deduplication if available
            if SEMANTIC_DEDUP_AVAILABLE:
                return self._store_concepts_with_deduplication(concepts)
            else:
                # Fallback to simple storage
                for concept in concepts:
                    self._store_concept(concept)
                
                logger.info(f"Successfully stored {len(concepts)} concepts in OpenSearch")
                return True
            
        except Exception as e:
            logger.error(f"Error storing concepts in OpenSearch: {e}")
            return False
    
    def _store_concepts_with_deduplication(self, concepts: List[Dict[str, Any]]) -> bool:
        """
        Store concepts with semantic deduplication
        
        Args:
            concepts: List of concept objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize deduplicator
            deduplicator = SemanticDeduplicator(
                opensearch_endpoint=self.opensearch_endpoint,
                region='us-east-1'
            )
            
            # Convert concepts to UnifiedConcept objects
            unified_concepts = []
            for concept in concepts:
                try:
                    if 'concept_title' in concept:
                        # Already in unified format
                        unified_concept = UnifiedConcept.from_dict(concept)
                    else:
                        # Convert from old format
                        unified_concept = UnifiedConcept(
                            concept_title=concept.get('normalized_title', concept.get('original_title', '')),
                            concept_type=concept.get('category', 'vocabulary'),
                            description=concept.get('explanation', ''),
                            jlpt_level=concept.get('jlpt_level', 'N5'),
                            example_sentences=concept.get('examples', []),
                            english_translations=[],
                            tags=concept.get('related_concepts', []),
                            category=concept.get('category', 'vocabulary'),
                            sources=[concept.get('source', 'unknown')],
                            source_ids={concept.get('source', 'unknown'): concept.get('id', '')},
                            confidence=concept.get('confidence', 0.5),
                            extraction_date=concept.get('extraction_date', datetime.now().isoformat()),
                            original_metadata=concept,
                            embedding=concept.get('embedding')
                        )
                    
                    unified_concepts.append(unified_concept)
                    
                except Exception as e:
                    logger.error(f"Error converting concept to unified format: {e}")
                    # Store as-is using old method
                    self._store_concept(concept)
            
            # Process with deduplication
            if unified_concepts:
                results = deduplicator.batch_process_concepts(unified_concepts)
                
                logger.info(f"Deduplication results: {results['inserted']} inserted, "
                           f"{results['merged']} merged, {results['errors']} errors")
                
                return results['errors'] == 0
            
            return True
            
        except Exception as e:
            logger.error(f"Error in semantic deduplication: {e}", exc_info=True)
            # Fallback to simple storage
            for concept in concepts:
                self._store_concept(concept)
            return True
    
    def _create_index_if_not_exists(self):
        """Create the concepts index if it doesn't exist"""
        index_name = 'concepts'
        index_url = f"{self.opensearch_endpoint}/{index_name}"
        
        # Check if index exists
        response = requests.head(index_url, auth=self.awsauth)
        
        if response.status_code == 404:
            # Create index with unified schema support
            index_mapping = {
                "mappings": {
                    "properties": {
                        # Unified schema fields
                        "concept_title": {"type": "text"},
                        "concept_type": {"type": "keyword"},
                        "description": {"type": "text"},
                        "jlpt_level": {"type": "keyword"},
                        "example_sentences": {"type": "text"},
                        "english_translations": {"type": "text"},
                        "tags": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "sources": {"type": "keyword"},
                        "source_ids": {"type": "object"},
                        "confidence": {"type": "float"},
                        "extraction_date": {"type": "date"},
                        "original_metadata": {"type": "object"},
                        
                        # Legacy fields (for backward compatibility)
                        "id": {"type": "keyword"},
                        "normalized_title": {"type": "text"},
                        "original_title": {"type": "text"},
                        "related_concepts": {"type": "keyword"},
                        "explanation": {"type": "text"},
                        "examples": {"type": "text"},
                        "source": {"type": "keyword"},
                        "agent_reasoning": {"type": "text"},
                        
                        # Vector embedding for semantic search
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1536,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib"
                            }
                        }
                    }
                }
            }
            
            response = requests.put(
                index_url,
                auth=self.awsauth,
                json=index_mapping,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("Created concepts index in OpenSearch")
            else:
                logger.error(f"Failed to create index: {response.text}")
    
    def _store_concept(self, concept: Dict[str, Any]):
        """Store a single concept in OpenSearch"""
        index_url = f"{self.opensearch_endpoint}/concepts/_doc/{concept['id']}"
        
        # Prepare document for OpenSearch
        doc = {
            'id': concept['id'],
            'normalized_title': concept['normalized_title'],
            'original_title': concept['original_title'],
            'category': concept['category'],
            'jlpt_level': concept['jlpt_level'],
            'related_concepts': concept['related_concepts'],
            'explanation': concept['explanation'],
            'confidence': concept['confidence'],
            'examples': concept['examples'],
            'source': concept['source'],
            'extraction_date': concept['extraction_date'],
            'agent_reasoning': concept['agent_reasoning'],
            'embedding': concept['embedding']
        }
        
        response = requests.put(
            index_url,
            auth=self.awsauth,
            json=doc,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to store concept {concept['id']}: {response.status_code} - {response.text}")


def lambda_handler(event, context):
    """
    Lambda handler for concept extraction
    
    Args:
        event: S3 event or manual trigger
        context: Lambda context
        
    Returns:
        Response object
    """
    try:
        logger.info("Starting concept extraction")
        
        # Initialize extractor
        extractor = ConceptExtractor()
        
        # Get data from S3 or event
        if 'Records' in event:
            # S3 trigger
            data = []
            for record in event['Records']:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                
                logger.info(f"Processing S3 object: {bucket}/{key}")
                
                # Download and parse data
                response = s3.get_object(Bucket=bucket, Key=key)
                file_data = json.loads(response['Body'].read())
                data.extend(file_data)
        else:
            # Manual trigger
            data = event.get('data', [])
        
        if not data:
            logger.warning("No data to process")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No data to process'})
            }
        
        # Extract concepts
        logger.info(f"Extracting concepts from {len(data)} items")
        concepts = extractor.extract_concepts_from_data(data)
        
        # Store in OpenSearch
        success = extractor.store_concepts_in_opensearch(concepts)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Concept extraction completed successfully',
                    'concepts_processed': len(concepts),
                    'concepts_stored': len(concepts)
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Concept extraction failed',
                    'error': 'Failed to store concepts in OpenSearch'
                })
            }
            
    except Exception as e:
        logger.error(f"Error in concept extraction: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Concept extraction failed',
                'error': str(e)
            })
        } 