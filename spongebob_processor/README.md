# SpongeBob Wiki Data Processor v2.0

This script cleans and processes the Apify wiki scrape for **two outputs**:
1. **Pinecone JSONL** - Metadata only (no full text) for vector database
2. **Google Sheets CSV** - Complete data with full text for reference

## What This Does

1. **Filters** out junk pages (galleries, categories, talk pages, etc.)
2. **Cleans** wiki artifacts and navigation elements from content
3. **Classifies** pages by type (character, episode, transcript, location)
4. **Chunks** content into ~400 token segments with overlap
5. **Extracts** rich metadata (mentioned characters, locations, content categories)
6. **Outputs TWO files**:
   - `pinecone_chunks.jsonl` - For Pinecone (text_preview only, no full_text)
   - `sheets_chunks.csv` - For Google Sheets (includes full_text)

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

### Step 3: Create a Virtual Environment

Python best practice is to use a virtual environment to avoid conflicts:

```bash
python3 -m venv venv
```

This creates a `venv` folder in your project directory.

### Step 4: Activate the Virtual Environment

**Mac/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your terminal prompt.

### Step 5: Install Dependencies

Now install the required packages:

```bash
pip install -r requirements.txt
```

This installs `tqdm` for progress bars.

**Note:** If you get an "externally-managed-environment" error, make sure you activated the virtual environment in Step 4.

### Step 6: Place Your Input File

Put your Apify JSON export in this folder and name it:

```
apify_export.json
```

**Or:** Edit `config.py` to point to your file location:

```python
INPUT_FILE = "/path/to/your/dataset_spongebob_wiki.json"
```

### Step 7: Run the Processor

```bash
python3 process.py
```

**Important:** Always activate the virtual environment (Step 4) before running the script!

## What to Expect

The processor will show progress in 5 stages:

```
============================================================
SpongeBob Wiki Data Processor v2.0
============================================================

[1/5] Loading data...
      File: apify_export.json
      Size: 54.2 MB
      Loaded: 2,147 pages

[2/5] Filtering pages...
      Checking which pages to keep...

[3/5] Processing & chunking...
      This may take a few minutes...

      Processing: 100%|████████████| 2147/2147 [00:45<00:00, 47.23page/s]

[4/5] Writing Pinecone file...
      File: pinecone_chunks.jsonl
      Size: 8.2 MB

[5/5] Writing Google Sheets file...
      File: sheets_chunks.csv
      Size: 14.5 MB

============================================================
✓ COMPLETE
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

  By content category:
    plot                 4,521 chunks (29.3%)
    dialogue             2,891 chunks (18.7%)
    personality          1,203 chunks ( 7.8%)
    general              4,823 chunks (31.3%)
    relationships          892 chunks ( 5.8%)
    description          1,102 chunks ( 7.1%)

Files created:
  pinecone_chunks.jsonl         → Upload to Pinecone
  sheets_chunks.csv             → Import to Google Sheets

============================================================
Next steps:
  1. Import sheets_chunks.csv into Google Sheets
  2. Run upload_to_pinecone.py to embed and upload
============================================================

Verifying output...

Sample Pinecone chunk:
  ID:               a3f2b1c9d4e5_0
  Namespace:        wiki-characters
  Page:             Patrick Star | Encyclopedia SpongeBobia | Fandom...
  Type:             character
  Category:         personality
  Main Character:   True
  Characters:       Patrick, SpongeBob, Squidward, Mr. Krabs, Sandy
  Locations:        Bikini Bottom, Krusty Krab, Easter Island Head
  Chunk:            0/12
  Preview:          Patrick Star is a fictional character in the American animated...

✓ Output files verified successfully
```

## Output Files

After running, you'll have:

1. **`pinecone_chunks.jsonl`** - For Pinecone vector database (8-10 MB)
2. **`sheets_chunks.csv`** - For Google Sheets reference (14-16 MB)
3. **`processing_stats.json`** - Detailed statistics about the processing

## Output Format Details

### 1. Pinecone JSONL (`pinecone_chunks.jsonl`)

Each line is a JSON object **without full text** (only text_preview):

```json
{
  "id": "a3f2b1c9d4e5_0",
  "namespace": "wiki-characters",
  "metadata": {
    "sheet_row_id": "a3f2b1c9d4e5_0",
    "source_url": "https://spongebob.fandom.com/wiki/Patrick_Star",
    "page_title": "Patrick Star | Encyclopedia SpongeBobia | Fandom",
    "page_type": "character",
    "content_category": "personality",
    "chunk_index": 0,
    "total_chunks": 12,
    "is_main_character": true,
    "characters_mentioned": ["Patrick", "SpongeBob", "Squidward"],
    "locations_mentioned": ["Bikini Bottom", "Krusty Krab"],
    "text_preview": "Patrick Star is one of the main characters in SpongeBob SquarePants. He is a dim-witted but well-meaning pink sea star who lives under a rock..."
  }
}
```

**Note:** The `text_preview` is **first 200 characters only**. There is **NO full_text** field in this file.

### 2. Google Sheets CSV (`sheets_chunks.csv`)

CSV with 14 columns including the **full text**:

| Column | Description |
|--------|-------------|
| chunk_id | Unique ID (matches Pinecone id) |
| namespace | wiki-characters, wiki-episodes, etc. |
| source_url | Full wiki URL |
| page_title | Character/episode/location name |
| page_type | character, episode, transcript, location |
| content_category | personality, relationships, plot, etc. |
| chunk_index | Position in page (0, 1, 2...) |
| total_chunks | Total chunks from this page |
| is_main_character | TRUE/FALSE (for characters only) |
| characters_mentioned | Comma-separated list |
| locations_mentioned | Comma-separated list |
| **full_text** | **Complete chunk text** |
| text_preview | First 200 characters |
| word_count | Number of words in chunk |

**Important:** The CSV uses `utf-8-sig` encoding and `QUOTE_ALL` for Excel compatibility. Full text includes newlines, which are properly escaped.

## Namespaces

Chunks are organized into 4 Pinecone namespaces:

- **`wiki-characters`** - Character bios, personality, relationships
- **`wiki-episodes`** - Episode plots, summaries, info
- **`wiki-transcripts`** - Raw dialogue from episodes
- **`wiki-locations`** - Location descriptions, features

## Content Categories

The processor detects content categories based on keywords:

### Character Content
- **personality** - Behavior, traits, "known for being", "is often"
- **relationships** - Friends, enemies, family, "son", "daughter"
- **biography** - Born, created, origin, history, backstory
- **appearance** - Looks, wears, color, physical features
- **abilities** - Skills, talents, powers, "can do"
- **quotes** - Catchphrases, famous lines, dialogue

### Episode Content
- **plot** - Synopsis, summary, story, "begins", "ends"
- **characters_in_episode** - Starring, featuring, appears

### Transcript Content
- **dialogue** - All transcript content

### Location Content
- **description** - Located, "is a", building overview
- **features** - Interior, rooms, layout, design
- **residents** - Lives, employees, owner, works
- **history** - Built, founded, opened

## Main Characters

The processor identifies these as main characters (for `is_main_character` field):

- SpongeBob SquarePants / SpongeBob
- Patrick Star / Patrick
- Squidward Tentacles / Squidward
- Mr. Krabs / Eugene H. Krabs
- Plankton / Sheldon J. Plankton
- Sandy Cheeks / Sandy
- Gary the Snail / Gary
- Mrs. Puff
- Pearl Krabs / Pearl
- Karen Plankton / Karen

## Configuration

Edit `config.py` to customize:

- **File paths** - Input/output locations
- **Chunking settings** - Chunk size, overlap amount
- **Characters/locations** - What to detect in content
- **Skip patterns** - What URL patterns to filter out
- **CSV headers** - Column names for Google Sheets

## Troubleshooting

### Error: Cannot find 'apify_export.json'

**Solution:** Place your Apify export in this folder and rename it, or edit `INPUT_FILE` in `config.py`

### Error: Invalid JSON file

**Solution:** Make sure your export is valid JSON. Try opening it in a text editor to check.

### Error: 'tqdm' module not found

**Solution:** Make sure you activated the virtual environment first:
```bash
source venv/bin/activate  # Mac/Linux
# OR: venv\Scripts\activate  # Windows
```
Then run: `pip install -r requirements.txt`

### Error: externally-managed-environment

**Solution:** This happens when trying to install packages system-wide. Use a virtual environment instead:
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# OR: venv\Scripts\activate  # Windows

# Now install packages
pip install -r requirements.txt
```

**Alternative:** If you really want to install system-wide (not recommended), use:
```bash
pip3 install --user -r requirements.txt
```

### Processing takes too long

**Solution:** The 54MB file should process in 1-2 minutes. If it takes longer, try:
- Closing other applications
- Using a faster computer
- Check if antivirus is scanning the file

### Output file is empty or too small

**Solution:** Check if your input file actually contains page data. The script needs pages with `text` fields.

### CSV doesn't open properly in Excel

**Solution:** The CSV uses `utf-8-sig` encoding. Try:
1. Open Excel
2. Go to Data → From Text/CSV
3. Select `sheets_chunks.csv`
4. Choose UTF-8 encoding
5. Import

## Next Steps

### 1. Import to Google Sheets

```bash
# Option A: Upload directly
# Go to Google Sheets → File → Import → Upload → sheets_chunks.csv

# Option B: Use Google Drive
# Upload sheets_chunks.csv to Google Drive
# Right-click → Open with → Google Sheets
```

### 2. Upload to Pinecone

Use the `pinecone_chunks.jsonl` file with your embedding script:

```python
# Example workflow (you'll need to create this script)
# 1. Read pinecone_chunks.jsonl
# 2. Generate embeddings using OpenAI text-embedding-3-small
# 3. Upload to Pinecone with full_text from Google Sheets lookup
```

**Important:** The Pinecone file doesn't contain full_text. You'll need to:
1. Store full_text in Google Sheets (already done by this processor)
2. Use `sheet_row_id` to look up full text when generating embeddings
3. Include the full text in the embedding process

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
- **Characters mentioned** - Detected from CHARACTER_MENTION_NAMES list
- **Locations mentioned** - Detected from MAIN_LOCATIONS list
- **Content category** - Detected from keywords (personality, plot, etc.)
- **Is main character** - TRUE if page_title matches MAIN_CHARACTERS list
- **Unique ID** - MD5 hash of URL + chunk index
- **Word count** - Number of words in full_text

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
Output 1: pinecone_chunks.jsonl (JSONL, no full_text)
Output 2: sheets_chunks.csv (CSV with full_text)
  ↓
Ready for:
  - Pinecone: Embed + Upload (use Google Sheets for full_text)
  - Google Sheets: Import for reference and lookups
```

## Example Workflow

```bash
# 1. Navigate to directory
cd ~/cleaning/spongebob_processor

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# OR: venv\Scripts\activate  # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place your input file
cp ~/Downloads/dataset_spongebob_wiki.json ./apify_export.json

# 5. Run processor
python3 process.py

# 6. Check Pinecone output (no full_text)
head -n 1 pinecone_chunks.jsonl | python3 -m json.tool

# 7. Check CSV output (has full_text)
head -n 2 sheets_chunks.csv

# 8. View stats
cat processing_stats.json

# 9. Deactivate virtual environment when done
deactivate
```

## License

This is a data processing script for personal use.
