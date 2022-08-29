import jwt as _jwt
import uuid
from typing import List, Optional
from fastapi import FastAPI, Request, WebSocket, Query, Depends, Response, WebSocketDisconnect
import fastapi.security as _security
import sqlalchemy.orm as orm
from models.models import User
import services.services as services
import schema.schemas as schemas
from utilities.socket_util import manager
from utilities.session import *

_JWT_SECRET = "edvora"

app = FastAPI()
oauth2schema = _security.OAuth2PasswordBearer("api/token")

@app.get('/')
async def get(request: Request):
    return {'Hello': 'World'}

@app.post("/api/users")
async def create_user(user: schemas.UserCreate, db: orm.Session = Depends(services.get_db)):
    db_user = await services.get_user_by_email(email=user.email, db=db)
    if db_user:
        return {"error": "Email already registered"}
    user = await services.create_user(user, db)
    return await services.create_token(user=user), "User created" 

@app.post("/api/create_session")
async def create_session(response: Response, token: Optional[str]=Query(None)):
    session = uuid.uuid4()
    name = _jwt.decode(token, _JWT_SECRET, algorithms=['HS256'])['id']
    data = SessionData(username=name)
    await backend.create(session, data)
    cookie.attach_to_response(response, session)
    return f"Session created"

@app.get("/api/current_session")
async def current_session(session: SessionData = Depends(cookie)):
    return session

    
@app.post("/api/token")
async def generate_token(form_data: _security.OAuth2PasswordRequestForm = Depends(), db: orm.Session = Depends(services.get_db)):
    user = await services.authenticate_user(email=form_data.username, password=form_data.password, db=db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    return await services.create_token(user=user)

@app.get("/api/users/me", response_model=schemas.User)
async def get_user(user: User = Depends(services.get_current_user)):
    return user

@app.post("/api/user-posts", response_model=schemas.Post)
async def create_post(post: schemas.PostCreate,user: schemas.User = Depends(services.get_current_user), db: orm.Session = Depends(services.get_db)):
    return await services.create_post(user=user, db=db, post=post)


@app.get("/api/my-posts", response_model=List[schemas.Post])
async def get_user_posts(user: schemas.User =  Depends(services.get_current_user), db: orm.Session =  Depends(services.get_db)):
    return await services.get_user_posts(user=user, db=db)

@app.websocket("/api/ws")
async def websocket_endpoint(websocket:  WebSocket, cookie_or_token= Depends(services.get_cookie_or_token)):
    print(cookie_or_token)
    user = _jwt.decode(cookie_or_token, _JWT_SECRET, algorithms=["HS256"])
    db = services.get_db()
    await manager.connect(websocket)
    username = user["email"].split('@')[0]
    await manager.broadcast(f'{username} has entered.')
    try:
        while True:
            post = await websocket.receive_text()
            await manager.broadcast(f'{username}:\t{post}')
    except  WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.broadcast(f'{username} left.')
