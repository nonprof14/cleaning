# SpongeBob Wiki Data Processor

This script cleans and processes the Apify wiki scrape for Pinecone vector database. It transforms raw wiki pages into clean, chunked text ready for embedding and upload.

## What This Does

1. **Filters** out junk pages (galleries, categories, talk pages, etc.)
2. **Cleans** wiki artifacts and navigation elements from content
3. **Classifies** pages by type (character, episode, transcript, location)
4. **Chunks** content into ~400 token segments with overlap
5. **Extracts** rich metadata (mentioned characters, locations, content categories)
6. **Outputs** JSONL file ready for Pinecone upload

## Prerequisites

- **Python 3.8 or higher**
- Your Apify export JSON file (the 54MB wiki scrape)

## Setup Instructions

### Step 1: Check Python Installation

Open Terminal (Mac) or Command Prompt (Windows) and run:

```bash
python3 --version
```

You should see something like `Python 3.9.7` or higher.

**If Python is not installed:**

- **Mac:** Install with Homebrew: `brew install python`
- **Windows:** Download from https://www.python.org/downloads/
- **Linux:** `sudo apt-get install python3`

### Step 2: Navigate to This Directory

```bash
cd path/to/spongebob_processor
```

For example:
```bash
cd ~/cleaning/spongebob_processor
```

### Step 3: Install Dependencies

```bash
pip3 install -r requirements.txt
```

This installs `tqdm` for progress bars.

### Step 4: Place Your Input File

Put your Apify JSON export in this folder and name it:

```
apify_export.json
```

**Or:** Edit `config.py` to point to your file location:

```python
INPUT_FILE = "/path/to/your/dataset_spongebob_wiki.json"
```

### Step 5: Run the Processor

```bash
python3 process.py
```

## What to Expect

The processor will show progress in 4 stages:

```
============================================================
SpongeBob Wiki Data Processor
============================================================

[1/4] Loading data...
      File: apify_export.json
      Size: 54.2 MB
      Loaded: 2,147 pages

[2/4] Processing pages...
      This may take a few minutes...

      Processing: 100%|████████████| 2147/2147 [00:45<00:00, 47.23page/s]

[3/4] Writing output...
      File: spongebob_chunks.jsonl
      Size: 12.3 MB

[4/4] Complete!

============================================================
✓ PROCESSING COMPLETE
============================================================

Summary:
  Total pages:       2,147
  Pages processed:   1,892
  Pages skipped:     255
  Total chunks:      15,432
  Processing time:   45.2s

  By namespace:
    wiki-characters      4,521 chunks (29.3%)
    wiki-episodes        6,234 chunks (40.4%)
    wiki-transcripts     2,891 chunks (18.7%)
    wiki-locations       1,786 chunks (11.6%)

  By page type:
    character            4,521 chunks (29.3%)
    episode              6,234 chunks (40.4%)
    transcript           2,891 chunks (18.7%)
    location             1,786 chunks (11.6%)

Output file: spongebob_chunks.jsonl
File size:   12.3 MB

============================================================
Ready for: Embedding and uploading to Pinecone
============================================================

Verifying output...

Sample chunk:
  ID:               a3f2b1c9d4e5_0
  Namespace:        wiki-characters
  Page:             Patrick Star | Encyclopedia SpongeBobia | Fandom...
  Type:             character
  Category:         personality
  Characters:       Patrick, SpongeBob, Squidward, Mr. Krabs, Sandy
  Locations:        Bikini Bottom, Krusty Krab, Easter Island Head
  Chunk:            0/12
  Preview:          Patrick Star is a fictional character in the American animated...

✓ Output file verified successfully
```

## Output Files

After running, you'll have:

1. **`spongebob_chunks.jsonl`** - Clean chunks ready for Pinecone (main output)
2. **`processing_stats.json`** - Detailed statistics about the processing

## Output Format

Each line in `spongebob_chunks.jsonl` is a JSON object:

```json
{
  "id": "a3f2b1c9d4e5_0",
  "namespace": "wiki-characters",
  "metadata": {
    "source_url": "https://spongebob.fandom.com/wiki/Patrick_Star",
    "page_title": "Patrick Star",
    "page_type": "character",
    "content_category": "personality",
    "chunk_index": 0,
    "total_chunks": 12,
    "characters_mentioned": ["Patrick", "SpongeBob", "Squidward"],
    "locations_mentioned": ["Bikini Bottom", "Krusty Krab"],
    "text": "Full chunk text content here...",
    "text_preview": "First 200 characters..."
  }
}
```

## Namespaces

Chunks are organized into 4 Pinecone namespaces:

- **`wiki-characters`** - Character bios, personality, relationships
- **`wiki-episodes`** - Episode plots, summaries, info
- **`wiki-transcripts`** - Raw dialogue from episodes
- **`wiki-locations`** - Location descriptions, features

## Configuration

Edit `config.py` to customize:

- **File paths** - Input/output locations
- **Chunking settings** - Chunk size, overlap amount
- **Characters/locations** - What to detect in content
- **Skip patterns** - What URL patterns to filter out

## Troubleshooting

### Error: Cannot find 'apify_export.json'

**Solution:** Place your Apify export in this folder and rename it, or edit `INPUT_FILE` in `config.py`

### Error: Invalid JSON file

**Solution:** Make sure your export is valid JSON. Try opening it in a text editor to check.

### Error: 'tqdm' module not found

**Solution:** Run `pip3 install -r requirements.txt` again

### Processing takes too long

**Solution:** The 54MB file should process in 1-2 minutes. If it takes longer, try:
- Closing other applications
- Using a faster computer
- Check if antivirus is scanning the file

### Output file is empty or too small

**Solution:** Check if your input file actually contains page data. The script needs pages with `text` fields.

## Next Steps

After processing, you can:

1. **Upload to Pinecone** - Use the output JSONL with embedding script
2. **Inspect the data** - Open `spongebob_chunks.jsonl` in a text editor
3. **Check statistics** - Review `processing_stats.json` for insights

## Technical Details

### Page Filtering

The processor skips:
- Category, Special, User, Talk, and Forum pages
- Gallery and credits pages
- Pages with query parameters (`?action=`, `?diff=`, etc.)
- Pages shorter than 200 characters

### Content Cleaning

Removes:
- Wiki navigation elements
- Edit/Show/Hide buttons
- Reference numbers [1], [2]
- Image URLs and base64 data
- Advertisement text
- Fandom boilerplate

### Chunking Strategy

- **Target:** ~400 tokens (1600 characters) per chunk
- **Overlap:** ~50 tokens (200 characters) between chunks
- **Method:** Splits by paragraphs first, then sentences if needed
- **Preserves:** Paragraph boundaries where possible

### Classification Logic

**Characters:**
- URL contains character name (spongebob, patrick, etc.)
- Content mentions "voiced by", "first appearance", "species:", etc.

**Episodes:**
- URL contains `_(episode)`, `_(short)`, or `_(special)`

**Transcripts:**
- URL contains `/transcript` or ends with `_transcript`

**Locations:**
- URL contains location keywords (krusty_krab, bikini_bottom, etc.)

### Metadata Extraction

For each chunk:
- **Characters mentioned** - Detected from MAIN_CHARACTERS list
- **Locations mentioned** - Detected from MAIN_LOCATIONS list
- **Content category** - Detected from section keywords (personality, plot, etc.)
- **Unique ID** - MD5 hash of URL + chunk index

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your Python version is 3.8+
3. Make sure the input JSON is valid
4. Check that you have write permissions in this directory

## Architecture

```
Input: apify_export.json (54MB, 2000+ pages)
  ↓
Filter: Remove junk pages (galleries, categories, etc.)
  ↓
Clean: Remove wiki artifacts and navigation
  ↓
Classify: Determine page type (character/episode/transcript/location)
  ↓
Chunk: Split into ~400 token segments with overlap
  ↓
Extract: Generate metadata (characters, locations, categories)
  ↓
Output: spongebob_chunks.jsonl (JSONL format)
  ↓
Ready for: OpenAI embedding → Pinecone upload
```

## Example Workflow

```bash
# 1. Navigate to directory
cd ~/cleaning/spongebob_processor

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Place your input file
cp ~/Downloads/dataset_spongebob_wiki.json ./apify_export.json

# 4. Run processor
python3 process.py

# 5. Check output
head -n 1 spongebob_chunks.jsonl | python3 -m json.tool

# 6. View stats
cat processing_stats.json
```

## License

This is a data processing script for personal use.
