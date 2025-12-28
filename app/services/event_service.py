from io import BytesIO
import json
import os
from typing import List
from PIL import Image
from app.models.eventModel import Event
import pytesseract
import re
from datetime import datetime



def consolidateAllEventsFromDataStore() -> List[Event]:
    json_dir = "app/data/json"
    all_events: List[Event] = []

    if not os.path.isdir(json_dir):
        print(f"JSON directory not found: {json_dir}")
        return all_events

    for fname in os.listdir(json_dir):
        if not fname.lower().endswith(".json"):
            continue
        path = os.path.join(json_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                all_events.extend(data)
            elif isinstance(data, dict):
                # common structures: {"events": [...]}, or id->event mapping, or single event dict
                if "events" in data and isinstance(data["events"], list):
                    all_events.extend(data["events"])
                else:
                    # try to extract dict values that look like event objects
                    dict_values = [v for v in data.values() if isinstance(v, dict)]
                    if dict_values:
                        all_events.extend(dict_values)
                    else:
                        all_events.append(data)
            else:
                print(f"Skipping {fname}: unexpected JSON structure")
        except Exception as e:
            print(f"Failed to read {path}: {e}")
            continue

    return all_events
# ...existing code...

def process_image_file(file_bytes: bytes, filename: str) -> List[Event]:
    """
    Process an uploaded image (bytes) and save extracted events to JSON named like the source image.
    Overwrites existing JSON for same base filename.
    """
    try:
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        print(f"Extracted Text from uploaded file {filename}: "+text)
        events = extract_events_from_text(text)
        base, _ = os.path.splitext(filename)
        saveEventsToDatastore(text, base)
        return events
    except Exception as e:
        print(f"Failed to process uploaded image {filename}: {e}")
        raise


def saveEventsToDatastore(extractedText: str, base_name: str):
    save_dir = "app/data/json"   # adjust this path to your project structure
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, f"{base_name}.txt")
    # Write JSON file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(extractedText)
    print(f"Events saved to {file_path}")



def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%b %d").replace(year=2025).strftime("%Y-%m-%d")
    except:
        return date_str.strip()

def extract_events_from_text(raw_text):
    events = []
    event_id = 1

    # Split by day headers
    day_blocks = re.split(r"(?:Maha|he)\s+\w+\s*\|.*", raw_text)

    headers = re.findall(r"(?:Maha|he)\s+\w+\s*\|.*", raw_text)

    for header, block in zip(headers, day_blocks[1:]):
        if "|" in header:
            day_name, date_str = header.split("|", 1)
            event_date = parse_date(date_str)
        else:
            day_name, event_date = header, None
    # Extract events
        for line in block.split("\n"):
            if ":" in line:
                parts = line.rsplit(":", 1)
                if len(parts) < 2:
                    continue
                time_str = parts[0].strip()
                event_name = parts[1].strip().rstrip(".")
                event = {
                    "id": event_id,
                    "event_name": event_name.strip(),
                    "event_description": f"{event_name.strip()} at {time_str.strip()}",
                    "event_date": event_date,
                    "event_address": "Utsab Cultural Association, Gachibowli Stadium, Hyderabad",
                }
                events.append(event)
                event_id += 1
    return events
