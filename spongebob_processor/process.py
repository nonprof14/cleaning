#!/usr/bin/env python3
"""
SpongeBob Wiki Data Processor
Cleans and processes Apify wiki scrape for Pinecone vector database
"""

import json
import re
import os
import sys
import hashlib
from collections import defaultdict
from datetime import datetime
from tqdm import tqdm

# Import configuration
from config import (
    INPUT_FILE, OUTPUT_FILE, STATS_FILE,
    MAX_CHUNK_CHARS, OVERLAP_CHARS, MIN_CONTENT_LENGTH,
    MAIN_CHARACTERS, MAIN_LOCATIONS, SKIP_URL_PATTERNS,
    SECTION_CATEGORIES, JUNK_LINES, NAMESPACES
)


def print_header():
    """Print script header"""
    print("\n" + "=" * 60)
    print("SpongeBob Wiki Data Processor")
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
    Detect what type of content this chunk contains based on section keywords.
    """
    text_lower = text[:500].lower()

    for category, keywords in SECTION_CATEGORIES.items():
        if any(keyword in text_lower for keyword in keywords):
            return category

    # Defaults by page type
    if page_type == 'character':
        return 'biography'
    elif page_type == 'episode':
        return 'plot'
    elif page_type == 'location':
        return 'description'
    elif page_type == 'transcript':
        return 'dialogue'

    return 'general'


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
    """
    # Find mentioned characters
    characters = []
    text_lower = text.lower()
    for char in MAIN_CHARACTERS:
        if char.lower() in text_lower:
            characters.append(char)

    # Find mentioned locations
    locations = []
    for loc in MAIN_LOCATIONS:
        if loc.lower() in text_lower:
            locations.append(loc)

    # Detect content category
    content_category = detect_content_category(text, page_type)

    # Generate unique ID
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    chunk_id = f"{url_hash}_{chunk_index}"

    # Determine namespace
    namespace = NAMESPACES.get(page_type, 'wiki-other')

    return {
        'id': chunk_id,
        'namespace': namespace,
        'metadata': {
            'source_url': url,
            'page_title': title,
            'page_type': page_type,
            'content_category': content_category,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'characters_mentioned': characters,
            'locations_mentioned': locations,
            'text': text,
            'text_preview': text[:200]
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
    print(f"[1/4] Loading data...")
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
    print(f"[2/4] Processing pages...")
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


def write_output(chunks: list, output_file: str):
    """Write chunks to JSONL file"""
    print(f"[3/4] Writing output...")
    print(f"      File: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + '\n')

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


def print_summary(stats: dict, output_file: str):
    """Print processing summary"""
    print(f"[4/4] Complete!")
    print()
    print("=" * 60)
    print("✓ PROCESSING COMPLETE")
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

    # By page type
    print("  By page type:")
    for page_type, count in sorted(stats['by_page_type'].items()):
        pct = (count / stats['total_chunks'] * 100) if stats['total_chunks'] > 0 else 0
        print(f"    {page_type:20s} {count:5,} chunks ({pct:5.1f}%)")
    print()

    print(f"Output file: {output_file}")
    file_size = os.path.getsize(output_file)
    print(f"File size:   {format_size(file_size)}")
    print()
    print("=" * 60)
    print("Ready for: Embedding and uploading to Pinecone")
    print("=" * 60)
    print()


def verify_output(output_file: str):
    """Verify output file and show sample"""
    print("Verifying output...")
    print()

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            sample = json.loads(first_line)

        print("Sample chunk:")
        print(f"  ID:               {sample['id']}")
        print(f"  Namespace:        {sample['namespace']}")
        print(f"  Page:             {sample['metadata']['page_title'][:50]}...")
        print(f"  Type:             {sample['metadata']['page_type']}")
        print(f"  Category:         {sample['metadata']['content_category']}")
        print(f"  Characters:       {', '.join(sample['metadata']['characters_mentioned'][:5])}")
        print(f"  Locations:        {', '.join(sample['metadata']['locations_mentioned'][:5])}")
        print(f"  Chunk:            {sample['metadata']['chunk_index']}/{sample['metadata']['total_chunks']-1}")
        print(f"  Preview:          {sample['metadata']['text_preview'][:80]}...")
        print()
        print("✓ Output file verified successfully")
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

    # Write output
    write_output(chunks, OUTPUT_FILE)

    # Write stats
    write_stats(stats, STATS_FILE)

    # Print summary
    print_summary(stats, OUTPUT_FILE)

    # Verify output
    verify_output(OUTPUT_FILE)


if __name__ == "__main__":
    main()
