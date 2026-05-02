from io import BytesIO
from typing import Any, List
from sqlalchemy.orm import Session
from app.models.eventModel import Event
import re
from datetime import datetime
from app.db.models import EventRecord
from app.db.session import SessionLocal
from app.schemas.eventSchema import EventCreate
from app.services.vector_service import store_event_embedding


def _normalize_date(date_value: Any) -> str:
    date_text = str(date_value).strip()
    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%b %d", "%B %d, %Y"):
        try:
            parsed_date = datetime.strptime(date_text, date_format)
            if date_format == "%b %d":
                parsed_date = parsed_date.replace(year=2025)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_text


def _event_record_to_schema(record: EventRecord) -> Event:
    return Event(
        id=record.id,
        event_name=record.event_name,
        event_description=record.event_description,
        event_date=record.event_date,
        event_address=record.event_address,
    )


def get_events_from_db(db: Session) -> List[Event]:
    records = db.query(EventRecord).order_by(EventRecord.event_date.asc(), EventRecord.id.asc()).all()
    return [_event_record_to_schema(record) for record in records]


def upsert_event(db: Session, event: EventCreate, update_embedding: bool = True) -> Event:
    event_date = _normalize_date(event.event_date)
    existing = (
        db.query(EventRecord)
        .filter(
            EventRecord.event_name == event.event_name,
            EventRecord.event_date == event_date,
            EventRecord.event_address == event.event_address,
        )
        .one_or_none()
    )

    if existing:
        existing.event_description = event.event_description
        existing.event_date = event_date
        existing.source_name = event.source_name
        existing.source_type = event.source_type
        record = existing
    else:
        record = EventRecord(
            event_name=event.event_name,
            event_description=event.event_description,
            event_date=event_date,
            event_address=event.event_address,
            source_name=event.source_name,
            source_type=event.source_type,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    if update_embedding:
        store_event_embedding(db, record.id)
    return _event_record_to_schema(record)


def upsert_events(db: Session, events: List[EventCreate], update_embeddings: bool = True) -> dict:
    for event in events:
        upsert_event(db, event, update_embedding=update_embeddings)
    return {"upserted": len(events)}


def consolidateAllEventsFromDataStore() -> List[Event]:
    db = SessionLocal()
    try:
        return get_events_from_db(db)
    finally:
        db.close()


def process_image_file(db: Session, file_bytes: bytes, filename: str, update_embeddings: bool = True) -> List[Event]:
    """
    Process an uploaded image and ingest extracted events directly into the database.
    """
    from PIL import Image
    import pytesseract

    try:
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        print(f"Extracted text from uploaded file {filename}: {text}")
        events = extract_events_from_text(text, source_name=filename)
        return [upsert_event(db, event, update_embedding=update_embeddings) for event in events]
    except Exception as e:
        print(f"Failed to process uploaded image {filename}: {e}")
        raise


def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%b %d").replace(year=2025).strftime("%Y-%m-%d")
    except:
        return date_str.strip()


def extract_events_from_text(raw_text: str, source_name: str = "ocr-upload") -> List[EventCreate]:
    events = []

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
                events.append(
                    EventCreate(
                        event_name=event_name.strip(),
                        event_description=f"{event_name.strip()} at {time_str.strip()}",
                        event_date=event_date,
                        event_address="Utsab Cultural Association, Gachibowli Stadium, Hyderabad",
                        source_name=source_name,
                        source_type="ocr",
                    )
                )
    return events
