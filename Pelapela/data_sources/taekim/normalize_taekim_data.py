#!/usr/bin/env python3
"""
Tae Kim Data Normalization with GiNZA Integration

This script normalizes Tae Kim grammar data for the concept network.
It handles cleaning, validation, and standardization of Tae Kim concepts.
Now includes GiNZA dependency parsing for Japanese text analysis.
"""

import json
import re
import jaconv
import sys
import os
sys.path.append('../network')  # Add network directory to path for BaseNormalizer
from base_normalizer import BaseNormalizer
from typing import List, Dict, Any, Optional
from collections import defaultdict
import hashlib

class TaeKimDataNormalizer(BaseNormalizer):
    def __init__(self, config: Dict[str, Any] = None):
        # Initialize base class (includes GiNZA setup)
        super().__init__()
        
        self.config = config or {
            'min_title_length': 2,
            'max_title_length': 300,
            'min_meaning_length': 3,
            'max_meaning_length': 1000,
            'max_examples_per_concept': 5,
            'enable_japanese_validation': True,
            'enable_content_cleaning': True
        }
        
        # Japanese character patterns
        self.japanese_patterns = {
            'hiragana': r'[\u3040-\u309F]',
            'katakana': r'[\u30A0-\u30FF]',
            'kanji': r'[\u4E00-\u9FAF]',
            'fullwidth': r'[\uFF00-\uFFEF]',
            'halfwidth': r'[\u0020-\u007F]'
        }
        
        # Common Japanese particles and auxiliaries
        self.common_particles = [
            'は', 'が', 'を', 'に', 'で', 'も', 'の', 'へ', 'から', 'まで', 'より', 'と', 'や',
            'です', 'だ', 'ます', 'いる', 'ある', 'する', 'なる', 'こと', 'もの', 'たり',
            'られる', 'れる', 'たい', 'た', 'て', 'で', 'ね', 'よ', 'ぞ', 'さ', 'か', 'な'
        ]
    
    def normalize_japanese_text(self, text: str) -> str:
        """Normalize Japanese text for consistency."""
        if not text:
            return ""
        
        # Convert to string
        text = str(text).strip()
        
        # Convert fullwidth to halfwidth
        text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def extract_japanese_content(self, text: str) -> Dict[str, str]:
        """Extract different types of Japanese content."""
        if not text:
            return {'hiragana': '', 'katakana': '', 'kanji': '', 'mixed': ''}
        
        hiragana = ''.join(re.findall(self.japanese_patterns['hiragana'], text))
        katakana = ''.join(re.findall(self.japanese_patterns['katakana'], text))
        kanji = ''.join(re.findall(self.japanese_patterns['kanji'], text))
        mixed = ''.join(re.findall(f"{self.japanese_patterns['hiragana']}|{self.japanese_patterns['katakana']}|{self.japanese_patterns['kanji']}", text))
        
        return {
            'hiragana': hiragana,
            'katakana': katakana,
            'kanji': kanji,
            'mixed': mixed
        }
    
    def extract_taekim_section(self, concept: Dict[str, Any]) -> str:
        """Extract Tae Kim section/chapter information."""
        # Check various fields for section information
        section_fields = ['section', 'chapter', 'category', 'topic', 'part']
        
        for field in section_fields:
            value = concept.get(field, '')
            if value:
                return str(value).strip()
        
        # Check title for section patterns
        title = concept.get('title', '')
        if title:
            # Look for common Tae Kim section patterns
            section_patterns = [
                r'Basic Grammar',
                r'Essential Grammar',
                r'Special Expressions',
                r'Advanced Topics',
                r'Basic Particles',
                r'Essential Particles',
                r'Basic Verb Conjugation',
                r'Essential Verb Conjugation'
            ]
            
            for pattern in section_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    return pattern
        
        return "Grammar"
    
    def validate_concept(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean a Tae Kim concept."""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'cleaned_concept': concept.copy()
        }
        
        cleaned = validation_result['cleaned_concept']
        
        # Check required fields
        if not cleaned.get('title'):
            validation_result['issues'].append("Missing required field: title")
            validation_result['is_valid'] = False
        
        # Validate title
        title = cleaned.get('title', '')
        if title:
            # Clean title
            original_title = title
            title = re.sub(r'\.{3,}', '...', title)
            title = re.sub(r'\s+', ' ', title)
            title = title.strip()
            
            # Truncate if too long
            if len(title) > self.config['max_title_length']:
                truncated = title[:self.config['max_title_length']-3]
                last_space = truncated.rfind(' ')
                if last_space > self.config['max_title_length'] * 0.7:
                    title = truncated[:last_space] + "..."
                else:
                    title = truncated + "..."
            
            # Clean title with Japanese normalization
            title = self.normalize_japanese_text(title)
            cleaned['title'] = title
            
            # Check length after cleaning
            if len(title) < self.config['min_title_length']:
                validation_result['issues'].append(f"Title too short: {len(title)} chars")
                validation_result['is_valid'] = False
        
        # Validate meaning
        meaning = cleaned.get('meaning', '')
        if meaning:
            meaning = self.normalize_japanese_text(meaning)
            cleaned['meaning'] = meaning
            
            if len(meaning) < self.config['min_meaning_length']:
                validation_result['issues'].append(f"Meaning too short: {len(meaning)} chars")
            elif len(meaning) > self.config['max_meaning_length']:
                cleaned['meaning'] = meaning[:self.config['max_meaning_length']] + "..."
        
        # Clean examples
        if cleaned.get('examples'):
            cleaned_examples = []
            examples = cleaned['examples']
            
            if isinstance(examples, list):
                for example in examples:
                    if isinstance(example, dict):
                        cleaned_example = {}
                        for key, value in example.items():
                            if isinstance(value, str):
                                cleaned_example[key] = self.normalize_japanese_text(value)
                            else:
                                cleaned_example[key] = value
                        cleaned_examples.append(cleaned_example)
                    elif isinstance(example, str):
                        cleaned_examples.append(self.normalize_japanese_text(example))
            
            # Limit examples
            cleaned['examples'] = cleaned_examples[:self.config['max_examples_per_concept']]
        
        # Extract and validate Tae Kim section
        section = self.extract_taekim_section(cleaned)
        if section:
            cleaned['taekim_section'] = section
        
        return validation_result
    
    def generate_embedding_input(self, concept: Dict[str, Any]) -> str:
        """Generate standardized input for embeddings."""
        parts = []
        
        # Title
        if concept.get('title'):
            parts.append(f"Title: {concept['title']}")
        
        # Meaning
        if concept.get('meaning'):
            parts.append(f"Meaning: {concept['meaning']}")
        
        # Usage
        if concept.get('usage'):
            parts.append(f"Usage: {concept['usage']}")
        
        # Notes
        if concept.get('notes'):
            parts.append(f"Notes: {concept['notes']}")
        
        # Examples
        if concept.get('examples'):
            examples = concept['examples']
            if isinstance(examples, list):
                for i, example in enumerate(examples[:3]):  # Limit to 3 examples
                    if isinstance(example, dict):
                        jp = example.get('jp', '')
                        en = example.get('en', '')
                        if jp and en:
                            parts.append(f"Example {i+1}: {jp} - {en}")
                        elif jp:
                            parts.append(f"Example {i+1}: {jp}")
                        elif en:
                            parts.append(f"Example {i+1}: {en}")
                    elif isinstance(example, str):
                        parts.append(f"Example {i+1}: {example}")
            elif isinstance(examples, str):
                parts.append(f"Examples: {examples}")
        
        # Tae Kim Section
        if concept.get('taekim_section'):
            parts.append(f"Section: {concept['taekim_section']}")
        
        # Tags
        if concept.get('tags'):
            tags = concept['tags']
            if isinstance(tags, list):
                parts.append(f"Tags: {', '.join(tags)}")
            elif isinstance(tags, str):
                parts.append(f"Tags: {tags}")
        
        return " | ".join(parts)
    
    def normalize_taekim_data(self, taekim_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize Tae Kim grammar data."""
        print(f"🔧 Normalizing {len(taekim_data)} Tae Kim concepts...")
        
        normalized_concepts = []
        validation_stats = {
            'total': len(taekim_data),
            'valid': 0,
            'invalid': 0,
            'issues': defaultdict(int),
            'sections': defaultdict(int)
        }
        
        for i, concept in enumerate(taekim_data):
            if i % 100 == 0:
                print(f"  Processing concept {i+1}/{len(taekim_data)}...")
            
            # Validate and clean
            validation = self.validate_concept(concept)
            
            if validation['is_valid']:
                cleaned_concept = validation['cleaned_concept']
                
                # Process with GiNZA for dependency parsing
                cleaned_concept = self.process_concept_with_ginza(cleaned_concept)
                
                # Ensure all required fields are present for 100% network coverage
                cleaned_concept = self.ensure_required_fields(cleaned_concept)
                
                # Generate embedding input
                cleaned_concept['embedding_input'] = self.generate_embedding_input(cleaned_concept)
                
                # Add source information
                cleaned_concept['sources'] = ['Tae Kim Grammar Guide']
                cleaned_concept['source_priority'] = 8  # High priority
                
                # Generate ID if not present
                if not cleaned_concept.get('id'):
                    title_hash = hashlib.md5(cleaned_concept['title'].encode()).hexdigest()[:8]
                    section = cleaned_concept.get('taekim_section', 'basic')
                    cleaned_concept['id'] = f"taekim_{section.lower().replace(' ', '_')}_{title_hash}"
                
                # Track section distribution
                section = cleaned_concept.get('taekim_section', 'Unknown')
                validation_stats['sections'][section] += 1
                
                normalized_concepts.append(cleaned_concept)
                validation_stats['valid'] += 1
            else:
                validation_stats['invalid'] += 1
                for issue in validation['issues']:
                    validation_stats['issues'][issue] += 1
        
        print(f"✅ Normalization complete:")
        print(f"  - Valid concepts: {validation_stats['valid']}")
        print(f"  - Invalid concepts: {validation_stats['invalid']}")
        print(f"  - Total issues: {sum(validation_stats['issues'].values())}")
        
        if validation_stats['sections']:
            print("  - Section distribution:")
            for section, count in sorted(validation_stats['sections'].items()):
                print(f"    * {section}: {count} concepts")
        
        if validation_stats['issues']:
            print("  - Common issues:")
            for issue, count in sorted(validation_stats['issues'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    * {issue}: {count} occurrences")
        
        return normalized_concepts
    
    def ensure_required_fields(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields are present for 100% network coverage."""
        # Call parent method to get base fields including GiNZA
        required_fields = super().ensure_required_fields(concept)
        
        # Add Tae Kim-specific field processing
        # Ensure romaji has meaningful content
        if not required_fields['romaji']:
            required_fields['romaji'] = "Reading not provided"
        
        # Ensure usage has meaningful content
        if not required_fields['usage'] or required_fields['usage'] == 'nan':
            required_fields['usage'] = "Tae Kim grammar point"
        
        # Ensure notes has meaningful content
        if not required_fields['notes'] or required_fields['notes'] == 'nan':
            section = concept.get('taekim_section', '')
            if section:
                required_fields['notes'] = f"Tae Kim {section} section"
            else:
                required_fields['notes'] = "Tae Kim grammar point"
        
        return required_fields

def main():
    """Main function to normalize Tae Kim data."""
    print("🔧 Tae Kim Data Normalization")
    print("=" * 50)
    
    # Load Tae Kim data
    input_file = "taekim_grammar_data_final.json"
    output_file = "taekim_concepts_normalized.json"
    
    print(f"📖 Loading Tae Kim data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        taekim_data = json.load(f)
    
    print(f"✅ Loaded {len(taekim_data)} Tae Kim concepts")
    
    # Normalize data
    normalizer = TaeKimDataNormalizer()
    normalized_data = normalizer.normalize_taekim_data(taekim_data)
    
    # Save normalized data
    print(f"\n💾 Saving normalized data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved {len(normalized_data)} normalized concepts")
    print("🎉 Tae Kim data normalization complete!")

if __name__ == "__main__":
    main() 