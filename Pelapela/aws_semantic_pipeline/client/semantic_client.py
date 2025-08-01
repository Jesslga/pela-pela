"""
Python client library for the AWS Semantic Concept Pipeline
"""

import requests
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Concept:
    """Represents a Japanese learning concept"""
    id: str
    normalized_title: str
    original_title: str
    category: str
    jlpt_level: str
    related_concepts: List[str]
    explanation: str
    confidence: float
    examples: List[str]
    source: str
    extraction_date: str
    agent_reasoning: str = ""


@dataclass
class SearchResult:
    """Represents a search result"""
    query: str
    results: List[Concept]
    count: int


@dataclass
class LearningPath:
    """Represents a learning path"""
    starting_concept: str
    target_level: Optional[str]
    concepts: List[Concept]
    concept_count: int


@dataclass
class Statistics:
    """Represents concept statistics"""
    total_concepts: int
    categories: Dict[str, int]
    jlpt_levels: Dict[str, int]
    sources: Dict[str, int]
    average_confidence: float


class SemanticConceptClient:
    """Client for interacting with the AWS Semantic Concept Pipeline"""
    
    def __init__(self, api_base_url: str):
        """
        Initialize the client
        
        Args:
            api_base_url: Base URL of the API Gateway (e.g., https://abc123.execute-api.us-east-1.amazonaws.com/prod)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Pelapela-Semantic-Client/1.0'
        })
    
    def search_concepts(self, query: str, limit: int = 10, 
                       category: Optional[str] = None, 
                       jlpt_level: Optional[str] = None) -> SearchResult:
        """
        Search for concepts similar to the query
        
        Args:
            query: Search query
            limit: Maximum number of results
            category: Filter by category
            jlpt_level: Filter by JLPT level
            
        Returns:
            SearchResult object
        """
        params = {
            'search': query,
            'limit': limit
        }
        
        if category:
            params['category'] = category
        if jlpt_level:
            params['jlpt_level'] = jlpt_level
        
        response = self.session.get(f"{self.api_base_url}/concepts", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        concepts = [self._dict_to_concept(concept) for concept in data['results']]
        
        return SearchResult(
            query=data['query'],
            results=concepts,
            count=data['count']
        )
    
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """
        Get a specific concept by ID
        
        Args:
            concept_id: Concept ID
            
        Returns:
            Concept object or None if not found
        """
        response = self.session.get(f"{self.api_base_url}/concepts/{concept_id}")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        return self._dict_to_concept(data)
    
    def get_concepts_by_category(self, category: str, limit: int = 50) -> List[Concept]:
        """
        Get all concepts in a specific category
        
        Args:
            category: Category to filter by
            limit: Maximum number of results
            
        Returns:
            List of concepts
        """
        params = {
            'category': category,
            'limit': limit
        }
        
        response = self.session.get(f"{self.api_base_url}/concepts", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return [self._dict_to_concept(concept) for concept in data['results']]
    
    def get_concepts_by_jlpt_level(self, jlpt_level: str, limit: int = 50) -> List[Concept]:
        """
        Get all concepts for a specific JLPT level
        
        Args:
            jlpt_level: JLPT level (N5, N4, N3, N2, N1)
            limit: Maximum number of results
            
        Returns:
            List of concepts
        """
        params = {
            'jlpt_level': jlpt_level,
            'limit': limit
        }
        
        response = self.session.get(f"{self.api_base_url}/concepts", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return [self._dict_to_concept(concept) for concept in data['results']]
    
    def get_learning_path(self, starting_concept: str, 
                         target_level: Optional[str] = None) -> LearningPath:
        """
        Generate a learning path starting from a concept
        
        Args:
            starting_concept: Starting concept ID or title
            target_level: Target JLPT level (optional)
            
        Returns:
            LearningPath object
        """
        payload = {
            'starting_concept': starting_concept
        }
        
        if target_level:
            payload['target_level'] = target_level
        
        response = self.session.post(f"{self.api_base_url}/concepts", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        concepts = [self._dict_to_concept(concept) for concept in data['learning_path']]
        
        return LearningPath(
            starting_concept=data['starting_concept'],
            target_level=data.get('target_level'),
            concepts=concepts,
            concept_count=data['concept_count']
        )
    
    def get_statistics(self) -> Statistics:
        """
        Get statistics about stored concepts
        
        Returns:
            Statistics object
        """
        params = {'statistics': 'true'}
        
        response = self.session.get(f"{self.api_base_url}/concepts", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return Statistics(
            total_concepts=data['total_concepts'],
            categories=data['categories'],
            jlpt_levels=data['jlpt_levels'],
            sources=data['sources'],
            average_confidence=data['average_confidence']
        )
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get API information and available endpoints
        
        Returns:
            API information dictionary
        """
        response = self.session.get(f"{self.api_base_url}/concepts")
        response.raise_for_status()
        
        return response.json()
    
    def _dict_to_concept(self, data: Dict[str, Any]) -> Concept:
        """Convert dictionary to Concept object"""
        return Concept(
            id=data['id'],
            normalized_title=data['normalized_title'],
            original_title=data['original_title'],
            category=data['category'],
            jlpt_level=data['jlpt_level'],
            related_concepts=data.get('related_concepts', []),
            explanation=data['explanation'],
            confidence=data['confidence'],
            examples=data.get('examples', []),
            source=data['source'],
            extraction_date=data['extraction_date'],
            agent_reasoning=data.get('agent_reasoning', '')
        )


class SemanticConceptAnalyzer:
    """Advanced analysis tools for the semantic concept pipeline"""
    
    def __init__(self, client: SemanticConceptClient):
        self.client = client
    
    def analyze_learning_progress(self, known_concepts: List[str]) -> Dict[str, Any]:
        """
        Analyze learning progress based on known concepts
        
        Args:
            known_concepts: List of concept IDs or titles that the user knows
            
        Returns:
            Analysis results
        """
        # Get all known concepts
        known_concept_objects = []
        for concept_id in known_concepts:
            concept = self.client.get_concept(concept_id)
            if concept:
                known_concept_objects.append(concept)
        
        if not known_concept_objects:
            return {'error': 'No valid concepts found'}
        
        # Analyze by category
        category_counts = {}
        jlpt_counts = {}
        
        for concept in known_concept_objects:
            category_counts[concept.category] = category_counts.get(concept.category, 0) + 1
            jlpt_counts[concept.jlpt_level] = jlpt_counts.get(concept.jlpt_level, 0) + 1
        
        # Find gaps and next steps
        gaps = self._find_learning_gaps(known_concept_objects)
        next_steps = self._suggest_next_steps(known_concept_objects)
        
        return {
            'total_known_concepts': len(known_concept_objects),
            'category_distribution': category_counts,
            'jlpt_distribution': jlpt_counts,
            'estimated_level': self._estimate_jlpt_level(known_concept_objects),
            'learning_gaps': gaps,
            'recommended_next_steps': next_steps
        }
    
    def find_concept_clusters(self, category: Optional[str] = None, 
                            jlpt_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find clusters of related concepts
        
        Args:
            category: Filter by category
            jlpt_level: Filter by JLPT level
            
        Returns:
            List of concept clusters
        """
        # Get concepts
        if category:
            concepts = self.client.get_concepts_by_category(category)
        elif jlpt_level:
            concepts = self.client.get_concepts_by_jlpt_level(jlpt_level)
        else:
            # Get all concepts (this might be slow for large datasets)
            stats = self.client.get_statistics()
            concepts = []
            for level in ['N5', 'N4', 'N3', 'N2', 'N1']:
                concepts.extend(self.client.get_concepts_by_jlpt_level(level, limit=100))
        
        # Group by related concepts
        clusters = {}
        
        for concept in concepts:
            # Use normalized title as cluster key
            cluster_key = concept.normalized_title.lower()
            
            if cluster_key not in clusters:
                clusters[cluster_key] = {
                    'main_concept': concept,
                    'variations': [],
                    'related': set()
                }
            
            # Add related concepts
            for related in concept.related_concepts:
                clusters[cluster_key]['related'].add(related)
        
        # Convert to list format
        result = []
        for cluster_key, cluster_data in clusters.items():
            result.append({
                'main_concept': cluster_data['main_concept'],
                'variations': cluster_data['variations'],
                'related_concepts': list(cluster_data['related']),
                'cluster_size': len(cluster_data['variations']) + 1
            })
        
        # Sort by cluster size
        result.sort(key=lambda x: x['cluster_size'], reverse=True)
        
        return result
    
    def generate_study_plan(self, target_level: str, 
                          current_level: Optional[str] = None,
                          focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive study plan
        
        Args:
            target_level: Target JLPT level
            current_level: Current JLPT level (optional)
            focus_areas: Areas to focus on (grammar, vocabulary, etc.)
            
        Returns:
            Study plan
        """
        # Get concepts for target level
        target_concepts = self.client.get_concepts_by_jlpt_level(target_level, limit=200)
        
        # Filter by focus areas if specified
        if focus_areas:
            target_concepts = [
                c for c in target_concepts 
                if c.category.lower() in [area.lower() for area in focus_areas]
            ]
        
        # Group by category
        by_category = {}
        for concept in target_concepts:
            if concept.category not in by_category:
                by_category[concept.category] = []
            by_category[concept.category].append(concept)
        
        # Generate learning paths for each category
        study_paths = {}
        for category, concepts in by_category.items():
            if concepts:
                # Use the first concept as starting point
                starting_concept = concepts[0].id
                learning_path = self.client.get_learning_path(starting_concept, target_level)
                study_paths[category] = learning_path
        
        return {
            'target_level': target_level,
            'current_level': current_level,
            'focus_areas': focus_areas,
            'total_concepts': len(target_concepts),
            'concepts_by_category': {cat: len(concepts) for cat, concepts in by_category.items()},
            'study_paths': study_paths,
            'estimated_study_time': self._estimate_study_time(target_concepts)
        }
    
    def _find_learning_gaps(self, known_concepts: List[Concept]) -> List[Dict[str, Any]]:
        """Find gaps in learning based on known concepts"""
        gaps = []
        
        # Get all concepts by JLPT level
        for level in ['N5', 'N4', 'N3', 'N2', 'N1']:
            level_concepts = self.client.get_concepts_by_jlpt_level(level, limit=100)
            
            # Find concepts in this level that are not known
            known_titles = {c.normalized_title.lower() for c in known_concepts}
            missing_concepts = [
                c for c in level_concepts 
                if c.normalized_title.lower() not in known_titles
            ]
            
            if missing_concepts:
                gaps.append({
                    'jlpt_level': level,
                    'missing_concepts': missing_concepts[:10],  # Limit to 10
                    'missing_count': len(missing_concepts)
                })
        
        return gaps
    
    def _suggest_next_steps(self, known_concepts: List[Concept]) -> List[Concept]:
        """Suggest next concepts to learn"""
        # Find the highest JLPT level known
        known_levels = [c.jlpt_level for c in known_concepts]
        current_level = max(known_levels) if known_levels else 'N5'
        
        # Get next level concepts
        next_level_map = {'N5': 'N4', 'N4': 'N3', 'N3': 'N2', 'N2': 'N1', 'N1': 'N1'}
        next_level = next_level_map.get(current_level, 'N1')
        
        next_concepts = self.client.get_concepts_by_jlpt_level(next_level, limit=20)
        
        # Sort by confidence and return top 5
        next_concepts.sort(key=lambda x: x.confidence, reverse=True)
        return next_concepts[:5]
    
    def _estimate_jlpt_level(self, known_concepts: List[Concept]) -> str:
        """Estimate current JLPT level based on known concepts"""
        if not known_concepts:
            return 'N5'
        
        # Count concepts by level
        level_counts = {}
        for concept in known_concepts:
            level_counts[concept.jlpt_level] = level_counts.get(concept.jlpt_level, 0) + 1
        
        # Estimate based on distribution
        total_concepts = len(known_concepts)
        
        if total_concepts < 10:
            return 'N5'
        elif level_counts.get('N1', 0) > total_concepts * 0.3:
            return 'N1'
        elif level_counts.get('N2', 0) > total_concepts * 0.3:
            return 'N2'
        elif level_counts.get('N3', 0) > total_concepts * 0.3:
            return 'N3'
        elif level_counts.get('N4', 0) > total_concepts * 0.3:
            return 'N4'
        else:
            return 'N5'
    
    def _estimate_study_time(self, concepts: List[Concept]) -> Dict[str, int]:
        """Estimate study time for concepts"""
        # Rough estimates: 10 minutes per concept for basic understanding
        total_minutes = len(concepts) * 10
        
        return {
            'total_minutes': total_minutes,
            'hours': total_minutes // 60,
            'days': (total_minutes // 60) // 2,  # Assuming 2 hours per day
            'weeks': ((total_minutes // 60) // 2) // 7  # Assuming 2 hours per day, 7 days per week
        }


# Convenience functions
def create_client(api_url: str) -> SemanticConceptClient:
    """Create a semantic concept client"""
    return SemanticConceptClient(api_url)


def create_analyzer(api_url: str) -> SemanticConceptAnalyzer:
    """Create a semantic concept analyzer"""
    client = create_client(api_url)
    return SemanticConceptAnalyzer(client) 