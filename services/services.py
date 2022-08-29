from http.client import HTTPException
from typing import Optional
import jwt as _jwt
from sqlalchemy.orm import Session
import passlib.hash as _hash
from fastapi import WebSocket, status, Depends, Cookie, Query, HTTPException
import fastapi.security as _security
import crud.database as database
from schema.schemas import User, UserCreate, PostCreate
from models.models import User, Post
import schema.schemas as schemas
import sqlalchemy.orm as orm
import datetime as datetime
_JWT_SECRET = "edvora"

oauth2schema = _security.OAuth2PasswordBearer("api/token")

def create_database():
    return database.Base.metadata.create_all(bind=database.engine)

async def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_user_by_email(email: str, db: Session):
    return db.query(User).filter(User.email == email).first()

async def create_user(user: UserCreate, db: Session):
    user_obj = User(email=user.email, hashed_password=_hash.bcrypt.hash(user.password))
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

async def authenticate_user(email: str, password: str, db: Session):
    user = await get_user_by_email(email=email, db=db)
    if not user:
        return False
    if not user.verify_password(password):
        return False
    return user

async def create_token(user: User):
    user_obj = schemas.User.from_orm(user)

    user_dict = user_obj.dict()
    del user_dict["date_created"]

    token = _jwt.encode(user_dict, _JWT_SECRET)

    return dict(access_token=token, token_type="bearer")


async def get_cookie_or_token(websocket: WebSocket, session: Optional[str] = Cookie(None), token: Optional[str] = Query(None)):
    if session is None and token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return session or token

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2schema)):
    try:
        payload = _jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        user = db.query(User).get(payload["id"])
    except:
        raise HTTPException(
            status_code=401, detail="Invalid Email or Password"
        )
    return schemas.User.from_orm(user)

async def create_post(user: schemas.User, db: orm.Session, post: schemas.PostCreate):
    post = Post(**post.dict(), owner_id=user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return schemas.Post.from_orm(post)

async def create_user_post(user: User, db: Session, post: PostCreate):
    post_obj = Post(post_text=post.post_text, owner_id=user.id, date_created=user.date_created)
    db.add(post_obj)
    db.commit()
    db.refresh(post_obj)
    return schemas.Post.from_orm(post_obj)

async def get_user_posts(user: User, db: Session):
    posts = db.query(Post).filter_by(owner_id=user.id)

    return list(map(schemas.Post.from_orm, posts))
