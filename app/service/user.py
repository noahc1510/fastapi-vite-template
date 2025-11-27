from sqlalchemy.orm import Session

from app.db.model import User


def upsert_user_from_claims(db: Session, claims: dict) -> User:
    """
    Ensure the Logto user exists in our database.
    """
    uid = claims.get("sub") or claims.get("user_id") or claims.get("id")
    display_name = claims.get("username") or claims.get("name")
    if not uid:
        raise ValueError("Missing user id in token claims")

    user = db.query(User).filter(User.uid == uid, User.is_deleted.is_(False)).first()
    if user:
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(uid=uid, display_name=display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
