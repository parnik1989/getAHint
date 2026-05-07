from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import EventRecord
from app.db.session import get_db

router = APIRouter(prefix="/eventManagement", tags=["Event Management"])


@router.get("/eventCount")
def get_event_count(db: Session = Depends(get_db)):
    """Get total number of events in database"""
    count = db.query(func.count(EventRecord.id)).scalar()
    return {"total_events": count}


@router.delete("/deleteAll")
def delete_all_events(db: Session = Depends(get_db)):
    """Delete ALL events from the database - USE WITH CAUTION"""
    try:
        count = db.query(EventRecord).delete()
        db.commit()
        return {
            "message": "All events deleted successfully",
            "deleted_count": count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/deleteByDate/{event_date}")
def delete_events_by_date(event_date: str, db: Session = Depends(get_db)):
    """Delete events on a specific date (format: YYYY-MM-DD)"""
    try:
        count = db.query(EventRecord).filter(
            EventRecord.event_date == event_date
        ).delete()
        db.commit()
        return {
            "message": f"Deleted events on {event_date}",
            "deleted_count": count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/deleteByCategory/{category}")
def delete_events_by_category(category: str, db: Session = Depends(get_db)):
    """Delete events by source_type category"""
    try:
        count = db.query(EventRecord).filter(
            EventRecord.source_type == category
        ).delete()
        db.commit()
        return {
            "message": f"Deleted events in category '{category}'",
            "deleted_count": count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/listEvents")
def list_all_events(limit: int = 100, db: Session = Depends(get_db)):
    """List all events (for debugging)"""
    events = db.query(EventRecord).limit(limit).all()
    return {
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "event_name": e.event_name,
                "event_date": e.event_date,
                "source_type": e.source_type,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }
