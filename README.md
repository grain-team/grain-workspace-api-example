# Grain API Wrapper

A Python wrapper for the Grain Workspace API to fetch transcripts and save them as JSON files.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Grain API token as an environment variable:
```bash
export GRAIN_API_TOKEN="your-token-here"
```

## Usage

The script starts in test mode by default, which fetches only the first recording:

```bash
python grain_api_wrapper.py
```

To fetch all recordings, edit the script and set `test_mode = False` in the `main()` function.

## Features

- **Streaming pagination**: Processes recordings page by page without loading all into memory
- **Resume capability**: Automatically saves progress after each page; can resume from crashes
- **Duplicate detection**: Skips recordings that have already been downloaded
- **Date-based organization**: Creates a directory tree organized by year/month/day

## Output Structure

The script creates a `recordings/` directory with subdirectories organized by date:

```
recordings/
├── 2024/
│   ├── 01/
│   │   ├── 15/
│   │   │   └── {recording_id}_{title}.json
│   │   └── 20/
│   │       └── {recording_id}_{title}.json
│   └── 02/
│       └── 03/
│           └── {recording_id}_{title}.json
└── 2025/
    └── 06/
        └── 16/
            └── {recording_id}_{title}.json
```

Each JSON file contains:
- ID, title, URL, source, datetime
- List of participants with names and emails
- Full transcript in JSON format

## Resume from Interruption

If the script is interrupted, it saves progress to `.cursor_state.json`. On the next run, it will ask if you want to resume from where it left off.

## API Notes

- The script includes rate limiting (1 second between recordings) to be respectful of the API
- Transcripts are fetched using the `transcript_format=json` parameter
