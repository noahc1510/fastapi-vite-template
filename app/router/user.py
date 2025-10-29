from fastapi import APIRouter
from sqlalchemy.orm import Session

from fastapi import Depends
from app.db.session import get_db

router = APIRouter()



@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return {"users": []}