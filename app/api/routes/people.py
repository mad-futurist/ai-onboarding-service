from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.person_contact import PersonContact
from app.schemas.person_contact import (
    NewcomerRecommendedContactRead,
    PersonContactCreate,
    PersonContactRead,
)
from app.services.person_contact_service import get_recommended_contacts

router = APIRouter(prefix="/people", tags=["People Map"])


@router.post("/", response_model=PersonContactRead, status_code=201)
def create_person_contact(payload: PersonContactCreate, db: Session = Depends(get_db)):
    contact = PersonContact(
        full_name=payload.full_name,
        role=payload.role,
        team=payload.team,
        email=payload.email,
        topics=payload.topics,
        is_active=payload.is_active,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/", response_model=list[PersonContactRead])
def list_person_contacts(db: Session = Depends(get_db)):
    return db.query(PersonContact).filter(PersonContact.is_active == True).order_by(PersonContact.id).all()


@router.get("/topics/{topic}", response_model=list[PersonContactRead])
def get_people_by_topic(topic: str, db: Session = Depends(get_db)):
    contacts = db.query(PersonContact).filter(PersonContact.is_active == True).all()
    matched = [c for c in contacts if c.topics and any(topic.lower() in t.lower() for t in c.topics)]
    return matched


@router.get("/recommendations/newcomers/{newcomer_id}", response_model=list[NewcomerRecommendedContactRead])
def get_recommended_people(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    results = get_recommended_contacts(db=db, newcomer_id=newcomer_id)
    return [
        NewcomerRecommendedContactRead(person=r["person"], reason=r["reason"], topic=r["topic"])
        for r in results
    ]
