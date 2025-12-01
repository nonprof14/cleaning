#!/usr/bin/env python3
"""
SpongeBob Wiki Data Processor v2.0
Cleans and processes Apify wiki scrape for Pinecone vector database and Google Sheets
"""

import json
import re
import os
import sys
import csv
import hashlib
from collections import defaultdict
from datetime import datetime
from tqdm import tqdm

# Import configuration
from config import (
    INPUT_FILE, PINECONE_OUTPUT_FILE, SHEETS_OUTPUT_FILE, STATS_FILE,
    MAX_CHUNK_CHARS, OVERLAP_CHARS, MIN_CONTENT_LENGTH,
    MAIN_CHARACTERS, CHARACTER_MENTION_NAMES, MAIN_LOCATIONS,
    SKIP_URL_PATTERNS, JUNK_LINES, NAMESPACES, CSV_HEADERS
)


def print_header():
    """Print script header"""
    print("\n" + "=" * 60)
    print("SpongeBob Wiki Data Processor v2.0")
    print("=" * 60)
    print()


def should_skip_page(url: str, title: str, content: str) -> tuple[bool, str]:
    """
    Check if a page should be skipped based on URL patterns and content.
    Returns (should_skip, reason)
    """
    # Check URL patterns
    for pattern in SKIP_URL_PATTERNS:
        if pattern in url:
            return True, f"URL contains '{pattern}'"

    # Check for gallery/credits pages
    if 'gallery' in url.lower() or 'credits' in url.lower():
        return True, "Gallery/Credits page"

    if 'gallery' in title.lower():
        return True, "Gallery in title"

    # Check content length
    if len(content.strip()) < MIN_CONTENT_LENGTH:
        return True, f"Content too short ({len(content)} chars)"

    return False, ""


def classify_page(url: str, title: str, content: str) -> str:
    """
    Classify page type based on URL and content.
    Returns: 'character', 'episode', 'transcript', 'location', or 'other'
    """
    url_lower = url.lower()

    # Transcripts
    if '/transcript' in url_lower or url_lower.endswith('_transcript'):
        return 'transcript'

    # Episodes - check URL patterns
    if any(x in url_lower for x in ['_(episode)', '_(short)', '_(special)']):
        return 'episode'

    # Locations
    location_keywords = [
        'bikini_bottom', 'krusty_krab', 'chum_bucket', 'treedome',
        'rock_bottom', 'jellyfish_fields', 'goo_lagoon', '_house',
        'boating_school', 'shady_shoals', 'weenie_hut', 'conch_street',
        'shell_shack', 'barg-n-mart', 'reef_blower'
    ]
    if any(x in url_lower for x in location_keywords):
        return 'location'

    # Characters - check for character indicators in content
    content_lower = content[:3000].lower()
    character_indicators = [
        'voiced by', 'first appearance', 'portrayed by',
        'species:', 'occupation:', 'residence:', 'gender:',
        'born:', 'age:', 'relatives:'
    ]
    if any(x in content_lower for x in character_indicators):
        return 'character'

    # Check URL for main character names
    main_chars = [
        'spongebob', 'patrick', 'squidward', 'krabs', 'plankton',
        'sandy', 'gary', 'puff', 'pearl', 'karen'
    ]
    if any(char in url_lower for char in main_chars):
        return 'character'

    # Default
    return 'other'


def clean_content(text: str) -> str:
    """
    Remove wiki artifacts, navigation elements, and junk from content.
    """
    # Patterns to remove (regex)
    patterns_to_remove = [
        r'\[edit\]',
        r'\[hide\]',
        r'\[show\]',
        r'\[\d+\]',  # Reference numbers [1], [2]
        r'https?://static\.wikia\.nocookie\.net[^\s]+',  # Image URLs
        r'data:image[^\s]+',  # Base64 images
        r'\d+,?\d*\s*pages\s*$',  # "18,353 pages"
        r'^in:.*$',  # Category lines "in: Characters, Males"
        r'^Categories.*$',
        r'Members Online.*',
        r'Recent Images.*',
    ]

    # Process line by line
    lines = text.split('\n')
    cleaned = []

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip junk lines
        if any(junk in line for junk in JUNK_LINES):
            continue

        # Skip very short lines (likely navigation)
        if len(line) < 3:
            continue

        # Skip lines that are just single letters (A B C D navigation)
        if len(line) == 1 and line.isalpha():
            continue

        # Skip lines that look like navigation (e.g., "1 2 3 4 5")
        if re.match(r'^[\d\s]+$', line):
            continue

        cleaned.append(line)

    text = '\n'.join(cleaned)

    # Apply regex patterns
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)

    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    return text.strip()


def detect_content_category(text: str, page_type: str) -> str:
    """
    Detect what type of content this chunk contains based on keywords.
    Uses the updated logic from requirements.
    """
    text_lower = text.lower()

    # Character content categories
    if page_type == "character":
        if any(word in text_lower for word in ["personality", "behavior", "traits", "known for being", "is often"]):
            return "personality"
        if any(word in text_lower for word in ["relationship", "friend", "enemy", "family", "married", "son", "daughter"]):
            return "relationships"
        if any(word in text_lower for word in ["born", "created", "origin", "history", "backstory", "early life"]):
            return "biography"
        if any(word in text_lower for word in ["appearance", "looks like", "wears", "color", "physical"]):
            return "appearance"
        if any(word in text_lower for word in ["ability", "can do", "skill", "talent", "power"]):
            return "abilities"
        if any(word in text_lower for word in ["quote", "says", "catchphrase", "famous line", '"']):
            return "quotes"

    # Episode content categories
    if page_type == "episode":
        if any(word in text_lower for word in ["plot", "synopsis", "summary", "story", "begins", "ends"]):
            return "plot"
        if any(word in text_lower for word in ["characters", "starring", "featuring", "appears"]):
            return "characters_in_episode"

    # Transcript content categories
    if page_type == "transcript":
        return "dialogue"

    # Location content categories
    if page_type == "location":
        if any(word in text_lower for word in ["description", "located", "is a", "building"]):
            return "description"
        if any(word in text_lower for word in ["feature", "inside", "interior", "room", "layout"]):
            return "features"
        if any(word in text_lower for word in ["resident", "lives", "employee", "works", "owner"]):
            return "residents"
        if any(word in text_lower for word in ["history", "built", "founded", "opened"]):
            return "history"

    return "general"


def is_main_character_page(page_title: str) -> bool:
    """
    Check if the page is about a main character.
    Returns True if page_title matches any main character name.
    """
    page_title_clean = page_title.lower()

    # Remove common suffixes from titles
    for suffix in [' | encyclopedia spongebobia', ' | fandom']:
        if suffix in page_title_clean:
            page_title_clean = page_title_clean.split(suffix)[0].strip()

    for char_name in MAIN_CHARACTERS:
        if char_name.lower() == page_title_clean or char_name.lower() in page_title_clean:
            return True

    return False


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap_chars: int = OVERLAP_CHARS) -> list:
    """
    Split text into chunks of approximately max_chars with overlap.
    ~400 tokens ≈ 1600 characters
    ~50 tokens overlap ≈ 200 characters
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []

    # Split by paragraphs first
    paragraphs = text.split('\n\n')

    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_length = len(para)

        # If single paragraph is too long, split by sentences
        if para_length > max_chars:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if current_length + len(sentence) > max_chars and current_chunk:
                    # Save current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(chunk_text)

                    # Start new chunk with overlap (last part of previous)
                    overlap_text = chunk_text[-overlap_chars:] if len(chunk_text) > overlap_chars else ''
                    current_chunk = [overlap_text] if overlap_text else []
                    current_length = len(overlap_text)

                current_chunk.append(sentence)
                current_length += len(sentence)
        else:
            # Normal paragraph
            if current_length + para_length > max_chars and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)

                # Overlap: keep last paragraph
                current_chunk = [current_chunk[-1]] if current_chunk else []
                current_length = len(current_chunk[0]) if current_chunk else 0

            current_chunk.append(para)
            current_length += para_length

    # Don't forget the last chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def extract_metadata(text: str, url: str, title: str, page_type: str, chunk_index: int, total_chunks: int) -> dict:
    """
    Extract rich metadata for a chunk.
    Returns both Pinecone and Sheets metadata.
    """
    # Find mentioned characters (use shorter names for detection)
    characters = []
    text_lower = text.lower()
    for char in CHARACTER_MENTION_NAMES:
        if char.lower() in text_lower:
            characters.append(char)

    # Find mentioned locations
    locations = []
    for loc in MAIN_LOCATIONS:
        if loc.lower() in text_lower:
            locations.append(loc)

    # Detect content category
    content_category = detect_content_category(text, page_type)

    # Check if this is a main character page
    is_main_char = is_main_character_page(title)

    # Generate unique ID
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    chunk_id = f"{url_hash}_{chunk_index}"

    # Determine namespace
    namespace = NAMESPACES.get(page_type, 'wiki-other')

    # Calculate word count
    word_count = len(text.split())

    # Text preview (first 200 characters)
    text_preview = text[:200] if len(text) > 200 else text

    return {
        'id': chunk_id,
        'namespace': namespace,
        'metadata': {
            'sheet_row_id': chunk_id,
            'source_url': url,
            'page_title': title,
            'page_type': page_type,
            'content_category': content_category,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'is_main_character': is_main_char,
            'characters_mentioned': characters,
            'locations_mentioned': locations,
            'full_text': text,
            'text_preview': text_preview,
            'word_count': word_count
        }
    }


def process_page(page: dict) -> list:
    """
    Process a single page and return list of chunks with metadata.
    Returns empty list if page should be skipped.
    """
    # Extract page data
    url = page.get('url', '')
    title = page.get('metadata', {}).get('title', '')
    text = page.get('text', '')

    # Check if page should be skipped
    should_skip, reason = should_skip_page(url, title, text)
    if should_skip:
        return []

    # Clean content
    cleaned_text = clean_content(text)

    # Check again after cleaning
    if len(cleaned_text) < MIN_CONTENT_LENGTH:
        return []

    # Classify page type
    page_type = classify_page(url, title, cleaned_text)

    # Chunk the text
    chunks = chunk_text(cleaned_text)

    # Extract metadata for each chunk
    results = []
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        metadata = extract_metadata(chunk, url, title, page_type, i, total_chunks)
        results.append(metadata)

    return results


def format_size(bytes: int) -> str:
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def load_data(input_file: str) -> list:
    """Load JSON data from file"""
    print(f"[1/5] Loading data...")
    print(f"      File: {input_file}")

    # Check if file exists
    if not os.path.exists(input_file):
        print(f"\n❌ Error: Cannot find '{input_file}'")
        print(f"   Please place your Apify export in this folder and name it '{input_file}'")
        print(f"   Or edit config.py to point to your file location")
        sys.exit(1)

    # Get file size
    file_size = os.path.getsize(input_file)
    print(f"      Size: {format_size(file_size)}")

    # Load JSON
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON file")
        print(f"   {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error reading file: {e}")
        sys.exit(1)

    # Check if data is empty
    if not data:
        print(f"\n❌ Error: JSON file is empty")
        sys.exit(1)

    print(f"      Loaded: {len(data):,} pages")
    print()

    return data


def process_all_pages(pages: list) -> tuple[list, dict]:
    """
    Process all pages and return chunks with statistics.
    """
    print(f"[2/5] Filtering pages...")
    print(f"      Checking which pages to keep...")
    print()

    print(f"[3/5] Processing & chunking...")
    print(f"      This may take a few minutes...")
    print()

    all_chunks = []
    stats = {
        'total_pages': len(pages),
        'pages_processed': 0,
        'pages_skipped': 0,
        'total_chunks': 0,
        'by_namespace': defaultdict(int),
        'by_page_type': defaultdict(int),
        'by_content_category': defaultdict(int),
        'processing_time': 0
    }

    start_time = datetime.now()

    # Process each page with progress bar
    for page in tqdm(pages, desc="      Processing", unit="page"):
        chunks = process_page(page)

        if chunks:
            all_chunks.extend(chunks)
            stats['pages_processed'] += 1

            # Update stats
            for chunk in chunks:
                stats['by_namespace'][chunk['namespace']] += 1
                stats['by_page_type'][chunk['metadata']['page_type']] += 1
                stats['by_content_category'][chunk['metadata']['content_category']] += 1
        else:
            stats['pages_skipped'] += 1

    stats['total_chunks'] = len(all_chunks)
    stats['processing_time'] = (datetime.now() - start_time).total_seconds()

    print()
    return all_chunks, stats


def write_pinecone_output(chunks: list, output_file: str):
    """Write chunks to Pinecone JSONL file (without full_text)"""
    print(f"[4/5] Writing Pinecone file...")
    print(f"      File: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            # Create Pinecone format (without full_text)
            pinecone_chunk = {
                'id': chunk['id'],
                'namespace': chunk['namespace'],
                'metadata': {
                    'sheet_row_id': chunk['metadata']['sheet_row_id'],
                    'source_url': chunk['metadata']['source_url'],
                    'page_title': chunk['metadata']['page_title'],
                    'page_type': chunk['metadata']['page_type'],
                    'content_category': chunk['metadata']['content_category'],
                    'chunk_index': chunk['metadata']['chunk_index'],
                    'total_chunks': chunk['metadata']['total_chunks'],
                    'is_main_character': chunk['metadata']['is_main_character'],
                    'characters_mentioned': chunk['metadata']['characters_mentioned'],
                    'locations_mentioned': chunk['metadata']['locations_mentioned'],
                    'text_preview': chunk['metadata']['text_preview']
                }
            }
            f.write(json.dumps(pinecone_chunk) + '\n')

    file_size = os.path.getsize(output_file)
    print(f"      Size: {format_size(file_size)}")
    print()


def write_sheets_output(chunks: list, output_file: str):
    """Write chunks to Google Sheets CSV file (with full_text)"""
    print(f"[5/5] Writing Google Sheets file...")
    print(f"      File: {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)

        # Write header
        writer.writerow(CSV_HEADERS)

        # Write data
        for chunk in chunks:
            m = chunk['metadata']
            writer.writerow([
                chunk['id'],
                chunk['namespace'],
                m['source_url'],
                m['page_title'],
                m['page_type'],
                m['content_category'],
                m['chunk_index'],
                m['total_chunks'],
                'TRUE' if m['is_main_character'] else 'FALSE',
                ', '.join(m['characters_mentioned']),
                ', '.join(m['locations_mentioned']),
                m['full_text'],
                m['text_preview'],
                m['word_count']
            ])

    file_size = os.path.getsize(output_file)
    print(f"      Size: {format_size(file_size)}")
    print()


def write_stats(stats: dict, stats_file: str):
    """Write processing statistics to JSON file"""
    # Convert defaultdict to regular dict for JSON serialization
    stats_clean = {
        'total_pages': stats['total_pages'],
        'pages_processed': stats['pages_processed'],
        'pages_skipped': stats['pages_skipped'],
        'total_chunks': stats['total_chunks'],
        'by_namespace': dict(stats['by_namespace']),
        'by_page_type': dict(stats['by_page_type']),
        'by_content_category': dict(stats['by_content_category']),
        'processing_time_seconds': stats['processing_time'],
        'timestamp': datetime.now().isoformat()
    }

    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_clean, f, indent=2)


def print_summary(stats: dict, pinecone_file: str, sheets_file: str):
    """Print processing summary"""
    print("=" * 60)
    print("✓ COMPLETE")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  Total pages:       {stats['total_pages']:,}")
    print(f"  Pages processed:   {stats['pages_processed']:,}")
    print(f"  Pages skipped:     {stats['pages_skipped']:,}")
    print(f"  Total chunks:      {stats['total_chunks']:,}")
    print(f"  Processing time:   {stats['processing_time']:.1f}s")
    print()

    # By namespace
    print("  By namespace:")
    for namespace, count in sorted(stats['by_namespace'].items()):
        pct = (count / stats['total_chunks'] * 100) if stats['total_chunks'] > 0 else 0
        print(f"    {namespace:20s} {count:5,} chunks ({pct:5.1f}%)")
    print()

    # By content category
    print("  By content category:")
    for category, count in sorted(stats['by_content_category'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / stats['total_chunks'] * 100) if stats['total_chunks'] > 0 else 0
        print(f"    {category:20s} {count:5,} chunks ({pct:5.1f}%)")
    print()

    print("Files created:")
    print(f"  {pinecone_file:30s} → Upload to Pinecone")
    print(f"  {sheets_file:30s} → Import to Google Sheets")
    print()
    print("=" * 60)
    print("Next steps:")
    print(f"  1. Import {sheets_file} into Google Sheets")
    print(f"  2. Run upload_to_pinecone.py to embed and upload")
    print("=" * 60)
    print()


def verify_output(pinecone_file: str):
    """Verify Pinecone output file and show sample"""
    print("Verifying output...")
    print()

    try:
        with open(pinecone_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            sample = json.loads(first_line)

        print("Sample Pinecone chunk:")
        print(f"  ID:               {sample['id']}")
        print(f"  Namespace:        {sample['namespace']}")
        print(f"  Page:             {sample['metadata']['page_title'][:50]}...")
        print(f"  Type:             {sample['metadata']['page_type']}")
        print(f"  Category:         {sample['metadata']['content_category']}")
        print(f"  Main Character:   {sample['metadata']['is_main_character']}")
        print(f"  Characters:       {', '.join(sample['metadata']['characters_mentioned'][:5])}")
        print(f"  Locations:        {', '.join(sample['metadata']['locations_mentioned'][:5])}")
        print(f"  Chunk:            {sample['metadata']['chunk_index']}/{sample['metadata']['total_chunks']-1}")
        print(f"  Preview:          {sample['metadata']['text_preview'][:80]}...")
        print()
        print("✓ Output files verified successfully")
        print()

    except Exception as e:
        print(f"⚠️  Warning: Could not verify output file: {e}")
        print()


def main():
    """Main processing pipeline"""
    print_header()

    # Load data
    pages = load_data(INPUT_FILE)

    # Process all pages
    chunks, stats = process_all_pages(pages)

    # Write Pinecone output (without full_text)
    write_pinecone_output(chunks, PINECONE_OUTPUT_FILE)

    # Write Google Sheets output (with full_text)
    write_sheets_output(chunks, SHEETS_OUTPUT_FILE)

    # Write stats
    write_stats(stats, STATS_FILE)

    # Print summary
    print_summary(stats, PINECONE_OUTPUT_FILE, SHEETS_OUTPUT_FILE)

    # Verify output
    verify_output(PINECONE_OUTPUT_FILE)


if __name__ == "__main__":
    main()
