"""
Configuration settings for SpongeBob Wiki Data Processor
"""

# Input/Output paths
INPUT_FILE = "apify_export.json"
OUTPUT_FILE = "spongebob_chunks.jsonl"
STATS_FILE = "processing_stats.json"

# Chunking settings
MAX_CHUNK_CHARS = 1600      # ~400 tokens
OVERLAP_CHARS = 200         # ~50 tokens
MIN_CONTENT_LENGTH = 200    # Skip pages shorter than this

# Pinecone settings (for reference)
PINECONE_INDEX = "spongebob-research"
PINECONE_HOST = "https://spongebob-research-gztg2m2.svc.aped-4627-b74a.pinecone.io"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Namespaces
NAMESPACES = {
    'character': 'wiki-characters',
    'episode': 'wiki-episodes',
    'transcript': 'wiki-transcripts',
    'location': 'wiki-locations',
    'other': 'wiki-other'
}

# Main characters to detect in content
MAIN_CHARACTERS = [
    'SpongeBob', 'Patrick', 'Squidward', 'Mr. Krabs', 'Plankton',
    'Sandy', 'Gary', 'Mrs. Puff', 'Pearl', 'Karen',
    'Mermaid Man', 'Barnacle Boy', 'Larry', 'Flying Dutchman',
    'Bubble Bass', 'Squilliam', 'DoodleBob', 'Man Ray'
]

# Main locations to detect in content
MAIN_LOCATIONS = [
    'Bikini Bottom', 'Krusty Krab', 'Chum Bucket', 'Pineapple',
    'Easter Island Head', 'Rock', 'Treedome', 'Boating School',
    'Jellyfish Fields', 'Goo Lagoon', 'Rock Bottom', 'Shady Shoals'
]

# URL patterns to skip (junk pages)
SKIP_URL_PATTERNS = [
    '?action=',
    '?from=',
    '?offset=',
    '?diff=',
    '?oldid=',
    '/Category:',
    '/Special:',
    '/User:',
    '/User_talk:',
    '/Talk:',
    '/File:',
    '/Template:',
    '/Thread:',
    '/Message_Wall:',
    '/Blog:',
    '/Forum:',
]

# Section categories for content classification
SECTION_CATEGORIES = {
    # Character sections
    'personality': ['personality', 'traits', 'behavior', 'characteristics'],
    'biography': ['biography', 'history', 'background', 'early life', 'life'],
    'relationships': ['relationships', 'friends', 'family', 'enemies'],
    'appearance': ['appearance', 'looks', 'physical'],
    'abilities': ['abilities', 'powers', 'skills', 'talents'],
    'quotes': ['quotes', 'catchphrases', 'sayings'],

    # Episode sections
    'plot': ['plot', 'synopsis', 'summary', 'storyline'],
    'characters': ['characters', 'cast', 'appearances'],

    # Location sections
    'description': ['description', 'overview', 'about'],
    'features': ['features', 'layout', 'interior', 'exterior', 'design'],
    'residents': ['residents', 'employees', 'inhabitants', 'staff'],
}

# Lines to remove from content
JUNK_LINES = [
    'Encyclopedia SpongeBobia',
    'Sign In',
    'Register',
    'Advertisement',
    'Skip to content',
    'View source',
    'History',
    'Talk (0)',
    'Trending pages',
    'Community content is available under',
    'Fandom Apps',
    'Take your favorite fandoms',
    'FANDOM',
    'Games',
    'Anime',
    'Movies',
    'TV',
    'Video',
    'Wikis',
]
