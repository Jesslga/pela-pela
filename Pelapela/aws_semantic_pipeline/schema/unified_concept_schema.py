"""
Unified schema for Japanese learning concepts across multiple data sources
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


@dataclass
class UnifiedConcept:
    """Unified concept format for all data sources"""
    
    # Core concept information
    concept_title: str
    concept_type: str  # "verb", "noun", "adjective", "grammar", "vocabulary", etc.
    description: str
    jlpt_level: Optional[str] = None  # N5, N4, N3, N2, N1
    
    # Examples and usage
    example_sentences: List[str] = field(default_factory=list)
    english_translations: List[str] = field(default_factory=list)
    
    # Categorization
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    # Source tracking
    sources: List[str] = field(default_factory=list)  # ["Duolingo", "Anki", etc.]
    source_ids: Dict[str, str] = field(default_factory=dict)  # {"Duolingo": "card_123", "Anki": "note_456"}
    
    # Metadata
    confidence: float = 1.0
    extraction_date: str = field(default_factory=lambda: datetime.now().isoformat())
    original_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Vector embedding (for semantic similarity)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "concept_title": self.concept_title,
            "concept_type": self.concept_type,
            "description": self.description,
            "jlpt_level": self.jlpt_level,
            "example_sentences": self.example_sentences,
            "english_translations": self.english_translations,
            "tags": self.tags,
            "category": self.category,
            "sources": self.sources,
            "source_ids": self.source_ids,
            "confidence": self.confidence,
            "extraction_date": self.extraction_date,
            "original_metadata": self.original_metadata,
            "embedding": self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedConcept':
        """Create from dictionary"""
        return cls(**data)
    
    def merge_with(self, other: 'UnifiedConcept') -> 'UnifiedConcept':
        """
        Merge this concept with another, combining metadata intelligently
        """
        merged = UnifiedConcept(
            concept_title=self.concept_title,  # Keep original title
            concept_type=self.concept_type,
            description=self.description,  # Could be enhanced with better description
            jlpt_level=self._merge_jlpt_levels(self.jlpt_level, other.jlpt_level),
            example_sentences=list(set(self.example_sentences + other.example_sentences)),
            english_translations=list(set(self.english_translations + other.english_translations)),
            tags=list(set(self.tags + other.tags)),
            category=self.category or other.category,
            sources=list(set(self.sources + other.sources)),
            source_ids={**self.source_ids, **other.source_ids},
            confidence=max(self.confidence, other.confidence),
            extraction_date=min(self.extraction_date, other.extraction_date),
            original_metadata={**self.original_metadata, **other.original_metadata}
        )
        
        # Use the better embedding if available
        if other.embedding and (not self.embedding or other.confidence > self.confidence):
            merged.embedding = other.embedding
        
        return merged
    
    def _merge_jlpt_levels(self, level1: Optional[str], level2: Optional[str]) -> Optional[str]:
        """Merge JLPT levels, keeping the lower (more advanced) level"""
        if not level1:
            return level2
        if not level2:
            return level1
        
        # JLPT levels in order of difficulty (N5 is easiest, N1 is hardest)
        jlpt_order = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}
        
        level1_num = jlpt_order.get(level1, 0)
        level2_num = jlpt_order.get(level2, 0)
        
        # Return the higher number (more advanced level)
        return level1 if level1_num >= level2_num else level2


class ConceptSchemaValidator:
    """Validates and normalizes concept data"""
    
    @staticmethod
    def normalize_concept_type(concept_type: str) -> str:
        """Normalize concept type to standard categories"""
        type_mapping = {
            "verb": "verb",
            "v": "verb",
            "noun": "noun", 
            "n": "noun",
            "adjective": "adjective",
            "adj": "adjective",
            "adverb": "adverb",
            "adv": "adverb",
            "grammar": "grammar",
            "grammatical": "grammar",
            "vocabulary": "vocabulary",
            "vocab": "vocabulary",
            "phrase": "phrase",
            "expression": "expression",
            "particle": "particle",
            "counter": "counter"
        }
        
        normalized = type_mapping.get(concept_type.lower(), concept_type.lower())
        return normalized
    
    @staticmethod
    def normalize_jlpt_level(level: str) -> Optional[str]:
        """Normalize JLPT level format"""
        if not level:
            return None
        
        level = level.upper().strip()
        if level in ["N5", "N4", "N3", "N2", "N1"]:
            return level
        
        # Handle variations
        level_mapping = {
            "JLPT5": "N5",
            "JLPT4": "N4", 
            "JLPT3": "N3",
            "JLPT2": "N2",
            "JLPT1": "N1",
            "5": "N5",
            "4": "N4",
            "3": "N3", 
            "2": "N2",
            "1": "N1"
        }
        
        return level_mapping.get(level, None)
    
    @staticmethod
    def validate_concept(concept: UnifiedConcept) -> List[str]:
        """Validate a concept and return list of validation errors"""
        errors = []
        
        if not concept.concept_title or not concept.concept_title.strip():
            errors.append("concept_title is required")
        
        if not concept.concept_type or not concept.concept_type.strip():
            errors.append("concept_type is required")
        
        if not concept.description or not concept.description.strip():
            errors.append("description is required")
        
        if concept.jlpt_level and concept.jlpt_level not in ["N5", "N4", "N3", "N2", "N1"]:
            errors.append(f"invalid jlpt_level: {concept.jlpt_level}")
        
        if concept.confidence < 0 or concept.confidence > 1:
            errors.append("confidence must be between 0 and 1")
        
        return errors


# Example usage and testing
if __name__ == "__main__":
    # Example concept from Duolingo
    duolingo_concept = UnifiedConcept(
        concept_title="食べる",
        concept_type="verb",
        description="to eat",
        jlpt_level="N5",
        example_sentences=["私はリンゴを食べる。"],
        english_translations=["I eat an apple."],
        tags=["food", "action"],
        sources=["Duolingo"],
        source_ids={"Duolingo": "card_123"}
    )
    
    # Example concept from Anki (same concept, different source)
    anki_concept = UnifiedConcept(
        concept_title="食べる",
        concept_type="verb", 
        description="to eat, to consume",
        jlpt_level="N5",
        example_sentences=["彼は寿司を食べる。"],
        english_translations=["He eats sushi."],
        tags=["food", "action", "basic"],
        sources=["Anki"],
        source_ids={"Anki": "note_456"}
    )
    
    # Merge the concepts
    merged = duolingo_concept.merge_with(anki_concept)
    print("Merged concept:")
    print(json.dumps(merged.to_dict(), indent=2, ensure_ascii=False)) 