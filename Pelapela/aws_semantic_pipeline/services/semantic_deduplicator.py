"""
Semantic deduplication service using vector embeddings
"""

import json
import logging
import boto3
import requests
from typing import Dict, List, Any, Optional, Tuple
from requests_aws4auth import AWS4Auth
import numpy as np

from schema.unified_concept_schema import UnifiedConcept, ConceptSchemaValidator

logger = logging.getLogger(__name__)


class SemanticDeduplicator:
    """Service for semantic deduplication using vector embeddings"""
    
    def __init__(self, opensearch_endpoint: str, region: str = 'us-east-1'):
        """
        Initialize the deduplicator
        
        Args:
            opensearch_endpoint: OpenSearch Serverless endpoint
            region: AWS region
        """
        self.opensearch_endpoint = opensearch_endpoint
        self.region = region
        
        # Initialize AWS credentials for OpenSearch
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'aoss',
            session_token=credentials.token
        )
        
        # Initialize Bedrock client for embeddings
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        
        # Configuration
        self.similarity_threshold = 0.85  # Cosine similarity threshold for duplicates
        self.max_search_results = 10  # Maximum results to check for similarity
        
    def find_semantic_duplicates(self, concept: UnifiedConcept) -> List[Tuple[UnifiedConcept, float]]:
        """
        Find semantic duplicates of a concept using vector similarity
        
        Args:
            concept: Concept to find duplicates for
            
        Returns:
            List of (concept, similarity_score) tuples
        """
        try:
            # Generate embedding for the concept
            embedding = self._generate_embedding(concept)
            if not embedding:
                logger.warning(f"Could not generate embedding for concept: {concept.concept_title}")
                return []
            
            # Search for similar concepts in OpenSearch
            similar_concepts = self._search_similar_concepts(embedding, concept.concept_title)
            
            # Filter by similarity threshold
            duplicates = []
            for similar_concept, score in similar_concepts:
                if score >= self.similarity_threshold:
                    duplicates.append((similar_concept, score))
            
            # Sort by similarity score (highest first)
            duplicates.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Found {len(duplicates)} semantic duplicates for '{concept.concept_title}'")
            return duplicates
            
        except Exception as e:
            logger.error(f"Error finding semantic duplicates: {e}")
            return []
    
    def merge_duplicate_concepts(self, new_concept: UnifiedConcept, 
                               existing_concept: UnifiedConcept) -> UnifiedConcept:
        """
        Merge a new concept with an existing duplicate
        
        Args:
            new_concept: New concept to merge
            existing_concept: Existing concept to merge with
            
        Returns:
            Merged concept
        """
        try:
            # Merge the concepts using the schema's merge logic
            merged_concept = existing_concept.merge_with(new_concept)
            
            # Update the extraction date to reflect the merge
            merged_concept.extraction_date = new_concept.extraction_date
            
            # Generate a new embedding if we have better information
            if new_concept.embedding and (not existing_concept.embedding or 
                                        new_concept.confidence > existing_concept.confidence):
                merged_concept.embedding = new_concept.embedding
            elif not merged_concept.embedding:
                # Generate embedding for the merged concept
                merged_concept.embedding = self._generate_embedding(merged_concept)
            
            logger.info(f"Merged concept '{new_concept.concept_title}' with existing concept")
            return merged_concept
            
        except Exception as e:
            logger.error(f"Error merging concepts: {e}")
            return new_concept
    
    def process_concept_with_deduplication(self, concept: UnifiedConcept) -> Dict[str, Any]:
        """
        Process a concept with full deduplication workflow
        
        Args:
            concept: Concept to process
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Validate the concept
            validator = ConceptSchemaValidator()
            errors = validator.validate_concept(concept)
            if errors:
                return {
                    "status": "error",
                    "message": f"Validation errors: {', '.join(errors)}",
                    "concept": concept.to_dict()
                }
            
            # Normalize the concept
            concept.concept_type = validator.normalize_concept_type(concept.concept_type)
            if concept.jlpt_level:
                concept.jlpt_level = validator.normalize_jlpt_level(concept.jlpt_level)
            
            # Generate embedding
            concept.embedding = self._generate_embedding(concept)
            
            # Find semantic duplicates
            duplicates = self.find_semantic_duplicates(concept)
            
            if duplicates:
                # Merge with the most similar duplicate
                best_match, similarity_score = duplicates[0]
                merged_concept = self.merge_duplicate_concepts(concept, best_match)
                
                # Update the existing concept in OpenSearch
                self._update_concept_in_opensearch(merged_concept)
                
                return {
                    "status": "merged",
                    "message": f"Merged with existing concept (similarity: {similarity_score:.3f})",
                    "original_concept": concept.to_dict(),
                    "merged_concept": merged_concept.to_dict(),
                    "similarity_score": similarity_score,
                    "total_duplicates_found": len(duplicates)
                }
            else:
                # No duplicates found, insert as new concept
                self._insert_concept_to_opensearch(concept)
                
                return {
                    "status": "inserted",
                    "message": "Inserted as new concept",
                    "concept": concept.to_dict()
                }
                
        except Exception as e:
            logger.error(f"Error processing concept: {e}")
            return {
                "status": "error",
                "message": str(e),
                "concept": concept.to_dict()
            }
    
    def _generate_embedding(self, concept: UnifiedConcept) -> Optional[List[float]]:
        """
        Generate embedding for a concept using Bedrock
        
        Args:
            concept: Concept to embed
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            # Create text to embed (combine title and description)
            text_to_embed = f"{concept.concept_title} {concept.description}"
            
            # Use Bedrock Titan Embeddings
            response = self.bedrock.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({
                    'inputText': text_to_embed
                })
            )
            
            response_body = json.loads(response.get('body').read())
            embedding = response_body.get('embedding')
            
            if embedding and len(embedding) > 0:
                return embedding
            else:
                logger.warning(f"Empty embedding returned for concept: {concept.concept_title}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def _search_similar_concepts(self, embedding: List[float], 
                               concept_title: str) -> List[Tuple[UnifiedConcept, float]]:
        """
        Search for similar concepts using vector similarity
        
        Args:
            embedding: Query embedding
            concept_title: Concept title for additional filtering
            
        Returns:
            List of (concept, similarity_score) tuples
        """
        try:
            # Build vector search query
            query = {
                "size": self.max_search_results,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": embedding,
                                        "k": self.max_search_results
                                    }
                                }
                            }
                        ],
                        "filter": [
                            {
                                "bool": {
                                    "should": [
                                        {"term": {"concept_title.keyword": concept_title}},
                                        {"wildcard": {"concept_title": f"*{concept_title}*"}},
                                        {"wildcard": {"concept_title": f"{concept_title}*"}}
                                    ]
                                }
                            }
                        ]
                    }
                },
                "_source": True
            }
            
            # Execute search
            response = requests.post(
                f"{self.opensearch_endpoint}/concepts/_search",
                auth=self.awsauth,
                json=query,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('hits', [])
                
                similar_concepts = []
                for hit in hits:
                    source = hit['_source']
                    score = hit.get('_score', 0)
                    
                    # Convert score to similarity (0-1 range)
                    similarity = min(score / 100, 1.0)  # Normalize score
                    
                    # Create UnifiedConcept from source
                    concept = UnifiedConcept.from_dict(source)
                    similar_concepts.append((concept, similarity))
                
                return similar_concepts
            else:
                logger.error(f"OpenSearch search failed: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching similar concepts: {e}")
            return []
    
    def _insert_concept_to_opensearch(self, concept: UnifiedConcept) -> bool:
        """
        Insert a new concept into OpenSearch
        
        Args:
            concept: Concept to insert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            concept_dict = concept.to_dict()
            
            response = requests.post(
                f"{self.opensearch_endpoint}/concepts/_doc",
                auth=self.awsauth,
                json=concept_dict,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully inserted concept: {concept.concept_title}")
                return True
            else:
                logger.error(f"Failed to insert concept: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting concept: {e}")
            return False
    
    def _update_concept_in_opensearch(self, concept: UnifiedConcept) -> bool:
        """
        Update an existing concept in OpenSearch
        
        Args:
            concept: Concept to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            concept_dict = concept.to_dict()
            
            # First, find the document ID
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"concept_title.keyword": concept.concept_title}},
                            {"term": {"sources": concept.sources[0] if concept.sources else ""}}
                        ]
                    }
                },
                "size": 1
            }
            
            search_response = requests.post(
                f"{self.opensearch_endpoint}/concepts/_search",
                auth=self.awsauth,
                json=search_query,
                headers={'Content-Type': 'application/json'}
            )
            
            if search_response.status_code == 200:
                search_result = search_response.json()
                hits = search_result.get('hits', {}).get('hits', [])
                
                if hits:
                    doc_id = hits[0]['_id']
                    
                    # Update the document
                    update_response = requests.put(
                        f"{self.opensearch_endpoint}/concepts/_doc/{doc_id}",
                        auth=self.awsauth,
                        json=concept_dict,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if update_response.status_code in [200, 201]:
                        logger.info(f"Successfully updated concept: {concept.concept_title}")
                        return True
                    else:
                        logger.error(f"Failed to update concept: {update_response.text}")
                        return False
                else:
                    logger.warning(f"Could not find existing concept to update: {concept.concept_title}")
                    return False
            else:
                logger.error(f"Search failed during update: {search_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating concept: {e}")
            return False
    
    def batch_process_concepts(self, concepts: List[UnifiedConcept]) -> Dict[str, Any]:
        """
        Process multiple concepts with deduplication
        
        Args:
            concepts: List of concepts to process
            
        Returns:
            Summary of processing results
        """
        results = {
            "total_concepts": len(concepts),
            "inserted": 0,
            "merged": 0,
            "errors": 0,
            "details": []
        }
        
        for concept in concepts:
            result = self.process_concept_with_deduplication(concept)
            results["details"].append(result)
            
            if result["status"] == "inserted":
                results["inserted"] += 1
            elif result["status"] == "merged":
                results["merged"] += 1
            else:
                results["errors"] += 1
        
        logger.info(f"Batch processing complete: {results['inserted']} inserted, "
                   f"{results['merged']} merged, {results['errors']} errors")
        
        return results


# Example usage
if __name__ == "__main__":
    # Initialize deduplicator
    deduplicator = SemanticDeduplicator(
        opensearch_endpoint="https://26fskibo8x82c4z03pp2.us-east-1.aoss.amazonaws.com"
    )
    
    # Test concepts
    concept1 = UnifiedConcept(
        concept_title="食べる",
        concept_type="verb",
        description="to eat",
        jlpt_level="N5",
        example_sentences=["私はリンゴを食べる。"],
        sources=["Duolingo"]
    )
    
    concept2 = UnifiedConcept(
        concept_title="食べる",
        concept_type="verb",
        description="to eat, to consume",
        jlpt_level="N5",
        example_sentences=["彼は寿司を食べる。"],
        sources=["Anki"]
    )
    
    # Process concepts
    result1 = deduplicator.process_concept_with_deduplication(concept1)
    result2 = deduplicator.process_concept_with_deduplication(concept2)
    
    print("Processing Results:")
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    print(json.dumps(result2, indent=2, ensure_ascii=False)) 