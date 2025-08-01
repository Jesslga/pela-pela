from typing import List, Dict, Optional
from pydantic import BaseModel

# 1. Kanji
class Kanji(BaseModel):
    kanji: str
    meanings: List[str]
    onyomi: List[str]
    kunyomi: List[str]
    stroke_count: int
    jlpt_level: Optional[int] = None
    radical: Optional[str] = None
    example_ids: Optional[List[str]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    topics: Optional[List[str]] = None

# 2. Example Sentences
class ExampleToken(BaseModel):
    word: str
    reading: str
    part_of_speech: str

class ExampleSentence(BaseModel):
    id: str
    sentence: str
    translation: str
    furigana: str
    tokens: List[ExampleToken]
    tone: Optional[str] = None
    politeness_level: Optional[str] = None
    level: Optional[str] = None
    tags: Optional[List[str]] = None
    topics: Optional[List[str]] = None

# 3. Speech Component (Parent)
class SpeechComponent(BaseModel):
    word: str
    reading: str
    meaning: str
    type: str  # e.g., "verb", "expression", "particle"
    jlpt_level: Optional[int] = None
    tone: Optional[str] = None
    politeness_levels: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    example_ids: Optional[List[str]] = None
    topics: Optional[List[str]] = None

# 4. Verb (inherits from SpeechComponent)
class Verb(SpeechComponent):
    verb_type: Optional[str] = None  # e.g., "ichidan", "godan"
    conjugations: Optional[Dict[str, str]] = None  # form_name: result
    example_ids: Optional[List[str]] = None
    topics: Optional[List[str]] = None

# 5. Expression (inherits from SpeechComponent)
class Expression(SpeechComponent):
    context: Optional[str] = None
    notes: Optional[str] = None
    example_ids: Optional[List[str]] = None
    topics: Optional[List[str]] = None

# 6. Topic
class Topic(BaseModel):
    topic: str
    description: Optional[str] = None
    related_words: List[str]
    tags: Optional[List[str]] = None

# 7. Conjugation Rule
class ConjugationRule(BaseModel):
    verb_type: str
    rules: Dict[str, Dict[str, Optional[str]]]
    tags: Optional[List[str]] = None 