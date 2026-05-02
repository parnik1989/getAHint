from io import BytesIO
import json
import os
from typing import Any, Dict, Iterable, List, Optional
from app.models.eventModel import Event
import re
from datetime import datetime
from app.core.paths import DATA_DIR



def _extract_event_records(data: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if not isinstance(data, dict):
        return []

    if isinstance(data.get("events"), list):
        return [item for item in data["events"] if isinstance(item, dict)]

    dict_values = [value for value in data.values() if isinstance(value, dict)]
    if dict_values:
        return dict_values

    return [data]


def _normalize_date(date_value: Any) -> str:
    date_text = str(date_value).strip()
    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%b %d"):
        try:
            parsed_date = datetime.strptime(date_text, date_format)
            if date_format == "%b %d":
                parsed_date = parsed_date.replace(year=2025)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_text


def _normalize_event_record(record: Dict[str, Any]) -> Optional[Event]:
    event_id = record.get("id", record.get("event_id"))
    required_fields = ("event_name", "event_description", "event_date", "event_address")

    if event_id is None or any(record.get(field) in (None, "") for field in required_fields):
        return None

    try:
        return Event(
            id=int(event_id),
            event_name=str(record["event_name"]).strip(),
            event_description=str(record["event_description"]).strip(),
            event_date=_normalize_date(record["event_date"]),
            event_address=str(record["event_address"]).strip(),
        )
    except (TypeError, ValueError):
        return None


def consolidateAllEventsFromDataStore() -> List[Event]:
    json_dir = DATA_DIR
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

            records = _extract_event_records(data)
            if not records:
                print(f"Skipping {fname}: unexpected JSON structure")
                continue

            for record in records:
                event = _normalize_event_record(record)
                if event is None:
                    print(f"Skipping invalid event in {fname}: {record}")
                    continue
                all_events.append(event)
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
    from PIL import Image
    import pytesseract

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
    save_dir = DATA_DIR
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
