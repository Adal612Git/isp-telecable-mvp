from sqlalchemy.orm import Session
from ..models import IdempotencyKey


def get_or_store_idempotent(db: Session, key: str, resource: str, response: str | None = None) -> tuple[bool, str | None]:
    existing = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if existing:
        return True, existing.response
    if response is not None:
        idem = IdempotencyKey(key=key, resource=resource, response=response)
        db.add(idem)
        db.commit()
    return False, None

