"""
Lambda function for querying Japanese learning concepts
from OpenSearch Serverless using vector similarity search.
"""

import json
import boto3
import logging
import os
from typing import Dict, List, Any
import requests
from requests_aws4auth import AWS4Auth

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
project_name = os.environ['PROJECT_NAME']

# OpenSearch authentication
session = boto3.Session()
credentials = session.get_credentials()
region = session.region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'aoss', session_token=credentials.token)

class ConceptQueryEngine:
    """Query engine for Japanese learning concepts using vector similarity"""
    
    def __init__(self):
        self.bedrock_client = bedrock
        self.opensearch_endpoint = opensearch_endpoint
        self.awsauth = awsauth
    
    def search_similar_concepts(self, query: str, limit: int = 10, category: str = None, jlpt_level: str = None) -> List[Dict[str, Any]]:
        """
        Search for concepts similar to the query using vector similarity
        
        Args:
            query: Search query (will be embedded)
            limit: Maximum number of results
            category: Filter by category (optional)
            jlpt_level: Filter by JLPT level (optional)
            
        Returns:
            List of similar concepts
        """
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)
            
            # Build OpenSearch query
            search_query = self._build_search_query(query_embedding, limit, category, jlpt_level)
            
            # Execute search
            results = self._execute_search(search_query)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in concept search: {e}")
            return []
    
    def get_concept_by_id(self, concept_id: str) -> Dict[str, Any]:
        """
        Get a specific concept by ID
        
        Args:
            concept_id: Concept ID to retrieve
            
        Returns:
            Concept object or None if not found
        """
        try:
            url = f"{self.opensearch_endpoint}/concepts/_doc/{concept_id}"
            response = requests.get(url, auth=self.awsauth)
            
            if response.status_code == 200:
                return response.json()['_source']
            else:
                logger.warning(f"Concept {concept_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving concept {concept_id}: {e}")
            return None
    
    def get_concepts_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all concepts in a specific category
        
        Args:
            category: Category to filter by
            limit: Maximum number of results
            
        Returns:
            List of concepts in the category
        """
        try:
            query = {
                "size": limit,
                "query": {
                    "term": {
                        "category.keyword": category
                    }
                },
                "sort": [
                    {"confidence": {"order": "desc"}},
                    {"normalized_title.keyword": {"order": "asc"}}
                ]
            }
            
            results = self._execute_search(query)
            return results
            
        except Exception as e:
            logger.error(f"Error getting concepts by category {category}: {e}")
            return []
    
    def get_concepts_by_jlpt_level(self, jlpt_level: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all concepts for a specific JLPT level
        
        Args:
            jlpt_level: JLPT level (N5, N4, N3, N2, N1)
            limit: Maximum number of results
            
        Returns:
            List of concepts for the JLPT level
        """
        try:
            query = {
                "size": limit,
                "query": {
                    "term": {
                        "jlpt_level.keyword": jlpt_level
                    }
                },
                "sort": [
                    {"confidence": {"order": "desc"}},
                    {"normalized_title.keyword": {"order": "asc"}}
                ]
            }
            
            results = self._execute_search(query)
            return results
            
        except Exception as e:
            logger.error(f"Error getting concepts by JLPT level {jlpt_level}: {e}")
            return []
    
    def get_learning_path(self, starting_concept: str, target_level: str = None) -> List[Dict[str, Any]]:
        """
        Generate a learning path starting from a concept
        
        Args:
            starting_concept: Starting concept ID or title
            target_level: Target JLPT level (optional)
            
        Returns:
            List of concepts in learning order
        """
        try:
            # Get starting concept
            if starting_concept.startswith('jlpt_') or starting_concept.startswith('anki_'):
                # It's a concept ID
                start_concept = self.get_concept_by_id(starting_concept)
            else:
                # It's a title, search for it
                results = self.search_similar_concepts(starting_concept, limit=1)
                start_concept = results[0] if results else None
            
            if not start_concept:
                return []
            
            # Get related concepts
            related_concepts = []
            for related_title in start_concept.get('related_concepts', []):
                related = self.search_similar_concepts(related_title, limit=1)
                if related:
                    related_concepts.append(related[0])
            
            # Sort by JLPT level and confidence
            all_concepts = [start_concept] + related_concepts
            all_concepts.sort(key=lambda x: (
                self._jlpt_level_to_number(x.get('jlpt_level', 'N5')),
                x.get('confidence', 0)
            ))
            
            # Filter by target level if specified
            if target_level:
                target_num = self._jlpt_level_to_number(target_level)
                all_concepts = [
                    c for c in all_concepts 
                    if self._jlpt_level_to_number(c.get('jlpt_level', 'N5')) <= target_num
                ]
            
            return all_concepts[:20]  # Limit to 20 concepts
            
        except Exception as e:
            logger.error(f"Error generating learning path: {e}")
            return []
    
    def get_concept_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored concepts
        
        Returns:
            Dictionary with concept statistics
        """
        try:
            # Get total count
            count_query = {
                "size": 0,
                "aggs": {
                    "total_concepts": {
                        "value_count": {
                            "field": "id"
                        }
                    },
                    "by_category": {
                        "terms": {
                            "field": "category.keyword",
                            "size": 20
                        }
                    },
                    "by_jlpt_level": {
                        "terms": {
                            "field": "jlpt_level.keyword",
                            "size": 10
                        }
                    },
                    "by_source": {
                        "terms": {
                            "field": "source.keyword",
                            "size": 10
                        }
                    },
                    "avg_confidence": {
                        "avg": {
                            "field": "confidence"
                        }
                    }
                }
            }
            
            response = requests.post(
                f"{self.opensearch_endpoint}/concepts/_search",
                auth=self.awsauth,
                json=count_query,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                aggs = result.get('aggregations', {})
                
                return {
                    'total_concepts': aggs.get('total_concepts', {}).get('value', 0),
                    'categories': {
                        bucket['key']: bucket['doc_count'] 
                        for bucket in aggs.get('by_category', {}).get('buckets', [])
                    },
                    'jlpt_levels': {
                        bucket['key']: bucket['doc_count'] 
                        for bucket in aggs.get('by_jlpt_level', {}).get('buckets', [])
                    },
                    'sources': {
                        bucket['key']: bucket['doc_count'] 
                        for bucket in aggs.get('by_source', {}).get('buckets', [])
                    },
                    'average_confidence': aggs.get('avg_confidence', {}).get('value', 0)
                }
            else:
                logger.error(f"Error getting statistics: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting concept statistics: {e}")
            return {}
    
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
            return [0.0] * 1536
    
    def _build_search_query(self, query_embedding: List[float], limit: int, category: str = None, jlpt_level: str = None) -> Dict[str, Any]:
        """Build OpenSearch query with vector similarity"""
        
        # Base query with vector similarity
        query = {
            "size": limit,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": limit
                    }
                }
            },
            "_source": [
                "id", "normalized_title", "original_title", "category", 
                "jlpt_level", "related_concepts", "explanation", 
                "confidence", "examples", "source", "extraction_date"
            ]
        }
        
        # Add filters if specified
        if category or jlpt_level:
            filter_conditions = []
            
            if category:
                filter_conditions.append({
                    "term": {
                        "category.keyword": category
                    }
                })
            
            if jlpt_level:
                filter_conditions.append({
                    "term": {
                        "jlpt_level.keyword": jlpt_level
                    }
                })
            
            if filter_conditions:
                query["query"] = {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_embedding,
                                        "k": limit
                                    }
                                }
                            }
                        ],
                        "filter": filter_conditions
                    }
                }
        
        return query
    
    def _execute_search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute search query against OpenSearch"""
        try:
            response = requests.post(
                f"{self.opensearch_endpoint}/concepts/_search",
                auth=self.awsauth,
                json=query,
                headers={'Content-Type': 'application/json'}
            )
            
            logger.info(f"OpenSearch response status: {response.status_code}")
            logger.info(f"OpenSearch response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('hits', [])
                logger.info(f"Hits: {hits}")
                if hits is None:
                    logger.warning("Hits is None, returning empty list")
                    return []
                return [hit['_source'] for hit in hits]
            else:
                logger.error(f"Search failed: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error executing search: {e}")
            return []
    
    def _jlpt_level_to_number(self, level: str) -> int:
        """Convert JLPT level to number for sorting"""
        level_map = {
            'N5': 1,
            'N4': 2,
            'N3': 3,
            'N2': 4,
            'N1': 5
        }
        return level_map.get(level, 1)


def lambda_handler(event, context):
    """
    Lambda handler for concept queries
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Event: {event}")
        
        # Parse request
        http_method = event.get('httpMethod', 'GET')
        logger.info(f"HTTP Method: {http_method}")
        
        path_parameters = event.get('pathParameters', {})
        logger.info(f"Path Parameters: {path_parameters}")
        
        query_string_parameters = event.get('queryStringParameters', {}) or {}
        logger.info(f"Query String Parameters: {query_string_parameters}")
        
        # Initialize query engine
        logger.info("Initializing query engine...")
        query_engine = ConceptQueryEngine()
        logger.info("Query engine initialized successfully")
        
        # Route requests
        logger.info("Starting routing logic...")
        if http_method == 'GET':
            logger.info("Processing GET request...")
            logger.info(f"Checking path_parameters: {path_parameters}")
            if path_parameters and 'concept_id' in path_parameters:
                # Get specific concept
                concept_id = path_parameters['concept_id']
                concept = query_engine.get_concept_by_id(concept_id)
                
                if concept:
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps(concept)
                    }
                else:
                    return {
                        'statusCode': 404,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({'error': 'Concept not found'})
                    }
            
            elif query_string_parameters and 'search' in query_string_parameters:
                logger.info("Processing search request...")
                # Search for concepts
                query = query_string_parameters['search']
                limit = int(query_string_parameters.get('limit', 10))
                category = query_string_parameters.get('category')
                jlpt_level = query_string_parameters.get('jlpt_level')
                
                results = query_engine.search_similar_concepts(query, limit, category, jlpt_level)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'query': query,
                        'results': results,
                        'count': len(results)
                    })
                }
            
            elif query_string_parameters and 'category' in query_string_parameters:
                logger.info("Processing category request...")
                # Get concepts by category
                category = query_string_parameters['category']
                limit = int(query_string_parameters.get('limit', 50))
                
                results = query_engine.get_concepts_by_category(category, limit)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'category': category,
                        'results': results,
                        'count': len(results)
                    })
                }
            
            elif query_string_parameters and 'jlpt_level' in query_string_parameters:
                logger.info("Processing JLPT level request...")
                # Get concepts by JLPT level
                jlpt_level = query_string_parameters['jlpt_level']
                limit = int(query_string_parameters.get('limit', 50))
                
                results = query_engine.get_concepts_by_jlpt_level(jlpt_level, limit)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'jlpt_level': jlpt_level,
                        'results': results,
                        'count': len(results)
                    })
                }
            
            elif query_string_parameters and 'statistics' in query_string_parameters:
                logger.info("Processing statistics request...")
                # Get concept statistics
                stats = query_engine.get_concept_statistics()
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps(stats)
                }
            
            else:
                # Return available endpoints
                logger.info("No specific query parameters found, returning available endpoints")
                try:
                    logger.info("Creating response body...")
                    response_body = {
                        'message': 'Japanese Learning Concepts API',
                        'endpoints': {
                            'search': 'GET /concepts?search=<query>&limit=<number>&category=<category>&jlpt_level=<level>',
                            'concept': 'GET /concepts/{concept_id}',
                            'category': 'GET /concepts?category=<category>&limit=<number>',
                            'jlpt_level': 'GET /concepts?jlpt_level=<level>&limit=<number>',
                            'statistics': 'GET /concepts?statistics=true',
                            'learning_path': 'POST /concepts with {"starting_concept": "<concept>", "target_level": "<level>"}'
                        }
                    }
                    logger.info(f"Response body created: {response_body}")
                    logger.info("Converting to JSON...")
                    json_body = json.dumps(response_body)
                    logger.info(f"JSON body: {json_body}")
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json_body
                    }
                except Exception as e:
                    logger.error(f"Error creating response: {e}")
                    logger.error(f"Error type: {type(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
        
        elif http_method == 'POST':
            # Handle POST requests (learning path generation)
            body = json.loads(event.get('body', '{}'))
            starting_concept = body.get('starting_concept')
            target_level = body.get('target_level')
            
            if starting_concept:
                learning_path = query_engine.get_learning_path(starting_concept, target_level)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'starting_concept': starting_concept,
                        'target_level': target_level,
                        'learning_path': learning_path,
                        'concept_count': len(learning_path)
                    })
                }
            else:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'starting_concept is required'})
                }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        logger.error(f"Error in concept query: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        } 