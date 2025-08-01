import json
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from typing import List, Dict, Any
import logging
from difflib import SequenceMatcher
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'language-concept-nodes.c5wimqww00fl.us-east-2.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'jessg',
    'password': 'pelapela!',
    'sslmode': 'require'
}

def normalize_text(text):
    """Normalize text for comparison"""
    if not text:
        return ""
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized

def similarity_score(text1, text2):
    """Calculate similarity between two texts"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    return SequenceMatcher(None, norm1, norm2).ratio()

def find_existing_matches(new_entries: List[Dict], source_id: int):
    """Find matches between new entries and existing database entries"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get all existing entries from other sources
        cursor.execute("""
            SELECT id, word, meaning, type, source_id
            FROM speech_components 
            WHERE source_id != %s
            ORDER BY word
        """, (source_id,))
        existing_entries = cursor.fetchall()
        
        matches = []
        
        for new_entry in new_entries:
            for existing in existing_entries:
                # Exact word match
                if new_entry['word'] == existing['word']:
                    matches.append({
                        'new_id': new_entry.get('db_id'),
                        'existing_id': existing['id'],
                        'new_word': new_entry['word'],
                        'existing_word': existing['word'],
                        'new_meaning': new_entry['meaning'],
                        'existing_meaning': existing['meaning'],
                        'match_type': 'exact_word',
                        'confidence': 1.0
                    })
                    continue
                
                # Meaning similarity
                meaning_similarity = similarity_score(new_entry['meaning'], existing['meaning'])
                if meaning_similarity > 0.8:
                    matches.append({
                        'new_id': new_entry.get('db_id'),
                        'existing_id': existing['id'],
                        'new_word': new_entry['word'],
                        'existing_word': existing['word'],
                        'new_meaning': new_entry['meaning'],
                        'existing_meaning': existing['meaning'],
                        'match_type': 'meaning_similarity',
                        'confidence': meaning_similarity
                    })
        
        return matches
        
    except Exception as e:
        logger.error(f"Error finding existing matches: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def create_cross_source_relationships(matches):
    """Create relationships between matched entries"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Ensure cross_source_relationships table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cross_source_relationships (
                id SERIAL PRIMARY KEY,
                source1_id INTEGER REFERENCES speech_components(id) ON DELETE CASCADE,
                source2_id INTEGER REFERENCES speech_components(id) ON DELETE CASCADE,
                relationship_type VARCHAR(50),
                confidence DECIMAL(3,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source1_id, source2_id)
            )
        """)
        
        created_count = 0
        
        for match in matches:
            if match['confidence'] >= 0.7:  # Minimum confidence threshold
                try:
                    cursor.execute("""
                        INSERT INTO cross_source_relationships (
                            source1_id, source2_id, relationship_type, confidence
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (source1_id, source2_id) DO NOTHING
                    """, (
                        match['new_id'],
                        match['existing_id'],
                        match['match_type'],
                        match['confidence']
                    ))
                    created_count += 1
                    
                except Exception as e:
                    logger.warning(f"Could not create relationship: {e}")
                    continue
        
        conn.commit()
        logger.info(f"✅ Created {created_count} cross-source relationships")
        return created_count
        
    except Exception as e:
        logger.error(f"Error creating relationships: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()
        conn.close()

def load_data_with_relationships(speech_file: Path, examples_file: Path, source_name: str, source_description: str, source_priority: int):
    """Load data and automatically create cross-source relationships"""
    logger.info(f"Starting enhanced data load for {source_name}...")
    
    # Load data files
    try:
        with open(speech_file, 'r', encoding='utf-8') as f:
            speech_data = json.load(f)
        with open(examples_file, 'r', encoding='utf-8') as f:
            examples_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data files: {e}")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Load source
        source_id = None
        cursor.execute("SELECT id FROM sources WHERE name = %s", (source_name,))
        result = cursor.fetchone()
        if result:
            source_id = result[0]
        else:
            cursor.execute(
                "INSERT INTO sources (name, description, priority) VALUES (%s, %s, %s) RETURNING id",
                (source_name, source_description, source_priority)
            )
            source_id = cursor.fetchone()[0]
        
        # Load speech components
        for speech in speech_data:
            try:
                cursor.execute("""
                    INSERT INTO speech_components (
                        word, reading, meaning, type, jlpt_level, tone, 
                        politeness_levels, tags, topics, source_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    speech['word'],
                    speech['reading'],
                    speech['meaning'],
                    speech['type'],
                    speech['jlpt_level'],
                    speech['tone'],
                    speech['politeness_levels'],
                    json.dumps(speech['tags']),
                    json.dumps(speech['topics']),
                    source_id
                ))
                speech_id = cursor.fetchone()[0]
                speech['db_id'] = speech_id
                
            except Exception as e:
                logger.error(f"Error inserting speech component {speech['word']}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        logger.info(f"Loaded {len(speech_data)} speech components")
        
        # Find cross-source matches
        matches = find_existing_matches(speech_data, source_id)
        logger.info(f"Found {len(matches)} potential cross-source matches")
        
        # Create relationships
        if matches:
            relationship_count = create_cross_source_relationships(matches)
            logger.info(f"Created {relationship_count} cross-source relationships")
        
        # Load examples and create speech-example relationships
        example_to_speech = {}
        for speech in speech_data:
            for ex_id in speech.get('example_ids', []):
                example_to_speech[ex_id] = speech['db_id']
        
        loaded_count = 0
        relationship_count = 0
        
        for example in examples_data:
            try:
                cursor.execute("""
                    INSERT INTO examples (
                        sentence, translation, furigana, tokens, tone,
                        politeness_level, level, tags, topics
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    example['sentence'],
                    example['translation'],
                    example['furigana'],
                    json.dumps(example['tokens']),
                    example['tone'],
                    example['politeness_level'],
                    example['level'],
                    json.dumps(example['tags']),
                    json.dumps(example['topics'])
                ))
                example_id = cursor.fetchone()[0]
                loaded_count += 1
                
                # Create speech-example relationship
                speech_id = example_to_speech.get(example['id'])
                if speech_id:
                    try:
                        cursor.execute("""
                            INSERT INTO speech_example_relationships (
                                speech_component_id, example_id, relationship_type
                            ) VALUES (%s, %s, %s)
                        """, (speech_id, example_id, 'example'))
                        relationship_count += 1
                    except Exception as rel_error:
                        logger.warning(f"Could not create relationship for example {example['id']}: {rel_error}")
                
            except Exception as e:
                logger.error(f"Error inserting example {example['id']}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        logger.info(f"Loaded {loaded_count} examples and created {relationship_count} relationships")
        logger.info(f"Enhanced data load for {source_name} completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during enhanced data load: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Example usage for JLPT data loading"""
    # This will be used when we load JLPT data
    # load_data_with_relationships(
    #     Path('jlpt_speech_components.json'),
    #     Path('jlpt_examples.json'),
    #     'JLPT Grammar',
    #     'Japanese Language Proficiency Test grammar points',
    #     3
    # )
    print("Enhanced data loader ready for JLPT data!")

if __name__ == "__main__":
    main() 