#!/usr/bin/env python3
"""
Anki Data Normalization with Multi-Network Separation and GiNZA Integration

This script normalizes Anki flashcard data for the concept network and automatically
separates concepts into four different network layers for multi-network analysis.
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

class AnkiDataNormalizer(BaseNormalizer):
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
        
        # Grammar-related keywords for classification
        self.grammar_keywords = [
            'grammar', 'conjugation', 'particle', 'verb form', 'verb conjugation',
            'adjective', 'adverb', 'preposition', 'auxiliary', 'copula', 'tense',
            'aspect', 'mood', 'voice', 'case', 'number', 'gender', 'declension',
            'inflection', 'morphology', 'syntax', 'clause', 'phrase', 'sentence',
            'subject', 'object', 'predicate', 'modifier', 'connector', 'marker'
        ]
        
        # Topic keywords for classification
        self.topic_keywords = [
            'food', 'travel', 'shopping', 'greetings', 'family', 'work', 'school',
            'weather', 'time', 'numbers', 'colors', 'animals', 'plants', 'body',
            'clothing', 'transportation', 'hobbies', 'sports', 'music', 'art',
            'technology', 'business', 'health', 'emotions', 'directions', 'places',
            'culture', 'history', 'politics', 'economy', 'science', 'nature',
            'home', 'kitchen', 'bathroom', 'bedroom', 'office', 'restaurant',
            'hospital', 'bank', 'post office', 'library', 'museum', 'park'
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
    
    def is_grammar_concept(self, concept: Dict[str, Any]) -> bool:
        """Check if a concept is grammar-related."""
        # Check tags
        tags = concept.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        
        for tag in tags:
            if any(keyword in tag.lower() for keyword in self.grammar_keywords):
                return True
        
        # Check notes
        notes = concept.get('notes', '').lower()
        if any(keyword in notes for keyword in self.grammar_keywords):
            return True
        
        # Check meaning
        meaning = concept.get('meaning', '').lower()
        if any(keyword in meaning for keyword in self.grammar_keywords):
            return True
        
        # Check title for particle patterns
        title = concept.get('title', '')
        if any(particle in title for particle in self.common_particles):
            return True
        
        return False
    
    def extract_topic(self, concept: Dict[str, Any]) -> Optional[str]:
        """Extract topic from concept tags or notes."""
        # Check tags
        tags = concept.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        
        for tag in tags:
            tag_lower = tag.lower()
            for keyword in self.topic_keywords:
                if keyword in tag_lower:
                    return keyword
        
        # Check notes
        notes = concept.get('notes', '').lower()
        for keyword in self.topic_keywords:
            if keyword in notes:
                return keyword
        
        return None
    
    def extract_examples(self, concept: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all examples from a concept."""
        examples = []
        concept_examples = concept.get('examples', [])
        
        if not concept_examples:
            return examples
        
        if isinstance(concept_examples, list):
            for i, example in enumerate(concept_examples):
                if isinstance(example, dict):
                    example_entry = {
                        'concept_id': concept.get('id', ''),
                        'concept_title': concept.get('title', ''),
                        'example_index': i,
                        'japanese': example.get('jp', example.get('japanese', '')),
                        'english': example.get('en', example.get('english', '')),
                        'romaji': example.get('romaji', ''),
                        'notes': example.get('notes', '')
                    }
                    examples.append(example_entry)
                elif isinstance(example, str):
                    example_entry = {
                        'concept_id': concept.get('id', ''),
                        'concept_title': concept.get('title', ''),
                        'example_index': i,
                        'japanese': example,
                        'english': '',
                        'romaji': '',
                        'notes': ''
                    }
                    examples.append(example_entry)
        elif isinstance(concept_examples, str):
            example_entry = {
                'concept_id': concept.get('id', ''),
                'concept_title': concept.get('title', ''),
                'example_index': 0,
                'japanese': concept_examples,
                'english': '',
                'romaji': '',
                'notes': ''
            }
            examples.append(example_entry)
        
        return examples
    
    def validate_concept(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean an Anki concept."""
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
        
        # Tags
        if concept.get('tags'):
            tags = concept['tags']
            if isinstance(tags, list):
                parts.append(f"Tags: {', '.join(tags)}")
            elif isinstance(tags, str):
                parts.append(f"Tags: {tags}")
        
        return " | ".join(parts)
    
    def normalize_anki_data(self, anki_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize Anki flashcard data and separate into network layers."""
        print(f"🔧 Normalizing {len(anki_data)} Anki concepts...")
        
        # Initialize validation statistics
        validation_stats = {
            'valid': 0,
            'invalid': 0,
            'issues': defaultdict(int)
        }
        
        # Initialize network separation lists
        grammar_network = []
        example_network = []
        topic_network = []
        tone_network = []
        
        normalized_concepts = []
        
        for i, concept in enumerate(anki_data):
            if i % 500 == 0:
                print(f"  Processing concept {i+1}/{len(anki_data)}...")
            
            # Validate and clean concept
            validation = self.validate_concept(concept)
            
            if validation['is_valid']:
                validation_stats['valid'] += 1
                cleaned_concept = validation['cleaned_concept']
                
                # Process with GiNZA for dependency parsing
                cleaned_concept = self.process_concept_with_ginza(cleaned_concept)
                
                # Ensure all required fields are present
                normalized_concept = self.ensure_required_fields(cleaned_concept)
                
                # Generate embedding input if not present
                if not normalized_concept['embedding_input']:
                    normalized_concept['embedding_input'] = self.generate_embedding_input(normalized_concept)
                
                # Add source information
                normalized_concept['sources'] = ['Anki Flashcards']
                normalized_concept['source_priority'] = 5  # Lower priority than JLPT/Tae Kim
                
                # Generate ID if not present
                if not normalized_concept.get('id'):
                    title_hash = hashlib.md5(normalized_concept['title'].encode()).hexdigest()[:8]
                    normalized_concept['id'] = f"anki_{title_hash}"
                
                normalized_concepts.append(normalized_concept)
                
                # Separate into network layers
                self.separate_into_networks(
                    normalized_concept, 
                    grammar_network, 
                    example_network, 
                    topic_network, 
                    tone_network
                )
            else:
                validation_stats['invalid'] += 1
                for issue in validation['issues']:
                    validation_stats['issues'][issue] += 1
        
        print(f"✅ Normalization complete:")
        print(f"  - Valid concepts: {validation_stats['valid']}")
        print(f"  - Invalid concepts: {validation_stats['invalid']}")
        print(f"  - Total issues: {sum(validation_stats['issues'].values())}")
        
        if validation_stats['issues']:
            print("  - Common issues:")
            for issue, count in sorted(validation_stats['issues'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    * {issue}: {count} occurrences")
        
        # Print network separation statistics
        print(f"\n📊 Network Separation Statistics:")
        print(f"  - Grammar Network: {len(grammar_network)} concepts")
        print(f"  - Example Network: {len(example_network)} examples")
        print(f"  - Topic Network: {len(topic_network)} concepts")
        print(f"  - Tone Network: {len(tone_network)} concepts")
        
        return {
            'normalized_concepts': normalized_concepts,
            'grammar_network': grammar_network,
            'example_network': example_network,
            'topic_network': topic_network,
            'tone_network': tone_network
        }
    
    def separate_into_networks(self, concept: Dict[str, Any], grammar_network: List[Dict[str, Any]], 
                              example_network: List[Dict[str, Any]], topic_network: List[Dict[str, Any]], 
                              tone_network: List[Dict[str, Any]]):
        """Separate a concept into appropriate network layers."""
        
        # 1. Grammar Network
        if self.is_grammar_concept(concept):
            grammar_concept = {
                'id': concept.get('id', ''),
                'title': concept.get('title', ''),
                'meaning': concept.get('meaning', ''),
                'examples': concept.get('examples', []),
                'tags': concept.get('tags', [])
            }
            grammar_network.append(grammar_concept)
        
        # 2. Example Network
        examples = self.extract_examples(concept)
        example_network.extend(examples)
        
        # 3. Topic Network
        topic = self.extract_topic(concept)
        if topic:
            topic_concept = {
                'id': concept.get('id', ''),
                'title': concept.get('title', ''),
                'meaning': concept.get('meaning', ''),
                'tags': concept.get('tags', []),
                'examples': concept.get('examples', []),
                'topic': topic
            }
            topic_network.append(topic_concept)
        
        # 4. Tone Network (empty structure for future tone tagging)
        tone_concept = {
            'id': concept.get('id', ''),
            'tone': ''
        }
        tone_network.append(tone_concept)
    
    def ensure_required_fields(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields are present for 100% network coverage."""
        # Call parent method to get base fields including GiNZA
        required_fields = super().ensure_required_fields(concept)
        
        # Add Anki-specific field processing
        # Ensure romaji is properly set
        if not required_fields['romaji'] and concept.get('reading'):
            required_fields['romaji'] = concept['reading']
        
        # Ensure usage has meaningful content
        if not required_fields['usage'] or required_fields['usage'] == 'nan':
            pos = concept.get('part_of_speech', '')
            if pos:
                required_fields['usage'] = f"Part of speech: {pos}"
            else:
                required_fields['usage'] = "Japanese vocabulary word"
        
        # Ensure notes has meaningful content
        if not required_fields['notes'] or required_fields['notes'] == 'nan':
            deck_name = concept.get('deck_name', '')
            anki_step = concept.get('anki_step', '')
            if deck_name:
                required_fields['notes'] = f"Anki deck: {deck_name}"
                if anki_step:
                    required_fields['notes'] += f", Step: {anki_step}"
            else:
                required_fields['notes'] = "Anki flashcard"
        
        return required_fields

def main():
    """Main function to normalize Anki data and create multi-network files."""
    print("🔧 Anki Data Normalization with Multi-Network Separation")
    print("=" * 70)
    
    # Load Anki data
    input_file = "anki_concepts_for_network.json"
    output_file = "anki_concepts_normalized.json"
    
    print(f"📖 Loading Anki data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        anki_data = json.load(f)
    
    print(f"✅ Loaded {len(anki_data)} Anki concepts")
    
    # Normalize data and separate into networks
    normalizer = AnkiDataNormalizer()
    results = normalizer.normalize_anki_data(anki_data)
    
    # Save normalized data (existing functionality)
    print(f"\n💾 Saving normalized data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results['normalized_concepts'], f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved {len(results['normalized_concepts'])} normalized concepts")
    
    # Save multi-network files
    print(f"\n🌐 Saving multi-network files...")
    
    # 1. Grammar Network
    grammar_file = "anki_grammar_network.json"
    with open(grammar_file, 'w', encoding='utf-8') as f:
        json.dump(results['grammar_network'], f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(results['grammar_network'])} grammar concepts to {grammar_file}")
    
    # 2. Example Network
    example_file = "anki_example_network.json"
    with open(example_file, 'w', encoding='utf-8') as f:
        json.dump(results['example_network'], f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(results['example_network'])} examples to {example_file}")
    
    # 3. Topic Network
    topic_file = "anki_topic_network.json"
    with open(topic_file, 'w', encoding='utf-8') as f:
        json.dump(results['topic_network'], f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(results['topic_network'])} topic concepts to {topic_file}")
    
    # 4. Tone Network
    tone_file = "anki_tone_network.json"
    with open(tone_file, 'w', encoding='utf-8') as f:
        json.dump(results['tone_network'], f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(results['tone_network'])} tone entries to {tone_file}")
    
    print("\n🎉 Anki data normalization and multi-network separation complete!")
    print("\n📁 Generated files:")
    print(f"  - {output_file} (full normalized data)")
    print(f"  - {grammar_file} (grammar network)")
    print(f"  - {example_file} (example network)")
    print(f"  - {topic_file} (topic network)")
    print(f"  - {tone_file} (tone network)")

if __name__ == "__main__":
    main() 