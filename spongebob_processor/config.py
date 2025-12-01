"""
Configuration settings for SpongeBob Wiki Data Processor
"""

# Input/Output paths
INPUT_FILE = "apify_export.json"
PINECONE_OUTPUT_FILE = "pinecone_chunks.jsonl"
SHEETS_OUTPUT_FILE = "sheets_chunks.csv"
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

# Main characters to detect in content and page titles
MAIN_CHARACTERS = [
    'SpongeBob SquarePants',
    'SpongeBob',
    'Patrick Star',
    'Patrick',
    'Squidward Tentacles',
    'Squidward',
    'Mr. Krabs',
    'Eugene H. Krabs',
    'Plankton',
    'Sheldon J. Plankton',
    'Sandy Cheeks',
    'Sandy',
    'Gary the Snail',
    'Gary',
    'Mrs. Puff',
    'Pearl Krabs',
    'Pearl',
    'Karen Plankton',
    'Karen'
]

# Main character names (for detecting in content)
CHARACTER_MENTION_NAMES = [
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

# CSV output settings
CSV_HEADERS = [
    'chunk_id',
    'namespace',
    'source_url',
    'page_title',
    'page_type',
    'content_category',
    'chunk_index',
    'total_chunks',
    'is_main_character',
    'characters_mentioned',
    'locations_mentioned',
    'full_text',
    'text_preview',
    'word_count'
]

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
