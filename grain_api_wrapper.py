#!/usr/bin/env python3
"""
Grain Workspace API Wrapper
Fetches transcripts from Grain recordings and saves them as JSON files.
"""

import json
import os
import requests
from typing import Dict, List, Optional
from datetime import datetime
import time


class GrainAPIClient:
    """Client for interacting with the Grain Workspace API."""

    BASE_URL = "https://api.grain.com/_/workspace-api"

    def __init__(self, api_token: str):
        """
        Initialize the Grain API client.

        Args:
            api_token: Workspace access token for authentication
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def get_recording(self, recording_id: str, include_transcript: bool = True) -> Dict:
        """
        Fetch a single recording by ID.

        Args:
            recording_id: The ID of the recording to fetch
            include_transcript: Whether to include transcript data

        Returns:
            Recording data including transcript if requested
        """
        url = f"{self.BASE_URL}/recordings/{recording_id}"
        params = {"include_participants": "true", "include_owners": "true"}

        # Add transcript_format parameter to get transcript in the response
        if include_transcript:
            params["transcript_format"] = "json"

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        recording_data = response.json()

        return recording_data

    def list_recordings(self, cursor: Optional[str] = None) -> Dict:
        """
        List all fully processed recordings in the workspace.

        Args:
            cursor: Pagination cursor for fetching next page

        Returns:
            Response containing list of recordings and pagination info
        """
        url = f"{self.BASE_URL}/recordings"
        params = {"include_participants": "true", "include_owners": "true"}

        if cursor:
            params["cursor"] = cursor

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        return response.json()

    def process_all_recordings(self, callback, resume_cursor=None):
        """
        Process all recordings page by page, calling callback for each recording.

        Args:
            callback: Function to call for each recording
            resume_cursor: Optional cursor to resume from

        Returns:
            Total number of recordings processed
        """
        cursor = resume_cursor
        total_processed = 0
        page_num = 1

        while True:
            print(f"\nFetching page {page_num}...")
            response = self.list_recordings(cursor)
            recordings = response.get("recordings", [])

            if not recordings:
                break

            print(f"Processing {len(recordings)} recordings from this page...")

            for recording in recordings:
                callback(recording, total_processed + 1)
                total_processed += 1

            # Check for next page
            cursor = response.get("cursor")
            if not cursor:
                break

            # Save cursor state
            save_cursor_state(cursor, total_processed)
            page_num += 1

            # Be nice to the API
            time.sleep(0.5)

            break

        return total_processed


def save_cursor_state(cursor: str, count: int, filename: str = ".cursor_state.json"):
    """Save the current cursor state to a file."""
    state = {
        "cursor": cursor,
        "processed_count": count,
        "timestamp": datetime.now().isoformat(),
    }
    with open(filename, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved cursor state (processed: {count})")


def load_cursor_state(filename: str = ".cursor_state.json") -> Optional[Dict]:
    """Load cursor state from file if it exists."""
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cursor state: {e}")
    return None


def save_recording_to_json(recording_data: Dict, output_dir: str = "recordings"):
    """
    Save recording data to a JSON file in a year/month/day directory structure.

    Args:
        recording_data: Recording data including transcript
        output_dir: Directory to save JSON files
    """
    # Parse the start_datetime to create directory structure
    start_datetime_str = recording_data.get("start_datetime")
    if start_datetime_str:
        try:
            dt = datetime.fromisoformat(start_datetime_str.replace("Z", "+00:00"))
            # Create year/month/day directory structure
            date_path = os.path.join(
                output_dir, str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}"
            )
        except Exception as e:
            print(f"  Warning: Could not parse date {start_datetime_str}: {e}")
            date_path = output_dir
    else:
        date_path = output_dir

    os.makedirs(date_path, exist_ok=True)

    # Create filename from recording ID and title
    recording_id = recording_data["id"]
    title = recording_data.get("title", "Untitled")
    # Clean title for filename
    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    safe_title = safe_title[:50]  # Limit length

    filename = f"{recording_id}_{safe_title}.json"
    filepath = os.path.join(date_path, filename)

    # Extract relevant data
    output_data = {
        "id": recording_data["id"],
        "title": recording_data.get("title"),
        "url": recording_data.get("url"),
        "source": recording_data.get("source"),
        "start_datetime": recording_data.get("start_datetime"),
        "participants": recording_data.get("participants", []),
        "transcript": recording_data.get(
            "transcript_json", {}
        ),  # API returns transcript_json when transcript_format=json
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    relative_path = os.path.relpath(filepath, output_dir)
    print(f"  Saved: {relative_path}")
    return filepath


def main():
    """Main function to fetch and save Grain recordings."""

    # Configuration
    API_TOKEN = os.environ.get("GRAIN_API_TOKEN")
    if not API_TOKEN:
        raise ValueError("Please set GRAIN_API_TOKEN environment variable")

    # Initialize client
    client = GrainAPIClient(API_TOKEN)

    # Test mode: fetch a single recording
    test_mode = False

    if test_mode:
        print("Running in test mode - fetching recordings list first...")
        try:
            # Get list of recordings
            response = client.list_recordings()
            recordings = response.get("recordings", [])

            if not recordings:
                print("No recordings found in workspace")
                return

            # Fetch first recording with transcript
            first_recording = recordings[0]
            print(f"\nFetching recording: {first_recording.get('title', 'Untitled')}")
            print(f"ID: {first_recording['id']}")

            # Fetch full recording data with transcript
            recording_data = client.get_recording(first_recording["id"])

            # Save to JSON
            filepath = save_recording_to_json(recording_data)
            print(f"\nTest complete! Check the output at: {filepath}")
            print("\nTo fetch all recordings, set test_mode = False in the script")

        except Exception as e:
            print(f"Error in test mode: {e}")
            raise
    else:
        print("Fetching all recordings...")

        # Check for existing cursor state
        cursor_state = load_cursor_state()
        resume_cursor = None
        starting_count = 0

        if cursor_state:
            print(f"\nFound saved state from {cursor_state['timestamp']}")
            print(f"Already processed: {cursor_state['processed_count']} recordings")
            resume = input("Resume from saved state? (y/n): ").lower().strip() == "y"
            if resume:
                resume_cursor = cursor_state["cursor"]
                starting_count = cursor_state["processed_count"]
            else:
                # Delete old state if not resuming
                if os.path.exists(".cursor_state.json"):
                    os.remove(".cursor_state.json")

        def process_recording(recording: Dict, index: int):
            """Process a single recording."""
            actual_index = starting_count + index
            print(
                f"\n[{actual_index}] Processing: {recording.get('title', 'Untitled')}"
            )

            try:
                # Check if already downloaded in the specific date directory
                recording_id = recording["id"]
                start_datetime_str = recording.get("start_datetime")

                if start_datetime_str and os.path.exists("recordings"):
                    try:
                        dt = datetime.fromisoformat(
                            start_datetime_str.replace("Z", "+00:00")
                        )
                        date_path = os.path.join(
                            "recordings",
                            str(dt.year),
                            f"{dt.month:02d}",
                            f"{dt.day:02d}",
                        )

                        if os.path.exists(date_path):
                            existing_files = [
                                f
                                for f in os.listdir(date_path)
                                if f.startswith(recording_id)
                            ]
                            if existing_files:
                                relative_path = os.path.join(
                                    str(dt.year),
                                    f"{dt.month:02d}",
                                    f"{dt.day:02d}",
                                    existing_files[0],
                                )
                                print(f"  Already downloaded: {relative_path}")
                                return
                    except Exception:
                        pass  # If date parsing fails, we'll just download it

                # Fetch full recording data with transcript
                recording_data = client.get_recording(recording_id)
                save_recording_to_json(recording_data)

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                print(f"  Error: {e}")

        try:
            # Process all recordings with streaming
            total = client.process_all_recordings(process_recording, resume_cursor)

            print(f"\nCompleted! Processed {total} recordings")

            # Clean up cursor state on successful completion
            if os.path.exists(".cursor_state.json"):
                os.remove(".cursor_state.json")
                print("Removed cursor state file")

        except Exception as e:
            print(f"\nError during processing: {e}")
            print("Cursor state saved - you can resume from where it stopped")
            raise


if __name__ == "__main__":
    main()
