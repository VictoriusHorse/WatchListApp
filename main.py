from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import FastAPI, HTTPException, Depends, status
from typing import Annotated
import pymysql

engine = create_engine("mysql+pymysql://tccapp:yE2KGUn7!Nqchvd@watchlist.mysql.database.azure.com/app_db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(50))
    is_active = Column(Boolean, default=True)

    items = relationship("Item", back_populates="owner")


class Item(Base):
    __tablename__ = "items"

    owner_id = Column(Integer, ForeignKey("users.id"))
    movieId = Column(Integer, index=True)
    rating = Column(String(50), index=True)
    id = Column(Integer, primary_key=True, index=True)

    owner = relationship("User", back_populates="items")

class Movie(Base):
    __tablename__ = "Movies"
    movieId = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), index=True)
    genres = Column(String(50), index=True)
    poster = Column(String(255))

class Recommend(Base):
    __tablename__ = "recommend"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), index=True)
    movieId = Column(Integer, index=True)
    userId = Column(Integer, index=True)

class ItemBase(BaseModel):
    movieId: int
    rating: float


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    items: list[Item] = []

    class Config:
        orm_mode = True

class Movie(BaseModel):
    movieId: int
    title: str
    genres: str

class Poster(BaseModel):
    poster: bytes


class Recommend (BaseModel):
    id: int
    title: str
    movieId: int
    userId: int

def create_user(db: Session, user: UserCreate):
    fake_hashed_password = user.password
    db_user = User(email=user.email, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def create_user_item(db: Session, item: ItemCreate, user_id: int):
    db_item = Item(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Item).offset(skip).limit(limit).all()

def get_movie(db: Session, movie_id: int):
    return db.query(Movie).filter(Movie.movieId == movie_id).first()

def get_poster(db: Session, movie_id: int):
    return db.query(Movie).filter(Movie.movieId == movie_id).first()

def get_recommend(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Recommend).offset(skip).limit(limit).all()

app = FastAPI(
    title="My App",
    description="Description of my app.",
    version="1.0",
    docs_url='/docs',
    openapi_url='/openapi.json',
    redoc_url=None)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]


@app.post("/users/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db=db, user=user)

@app.get("/users/{user_id}", response_model=User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/items/", response_model=Item)
def create_item_for_user(
    user_id: int, item: ItemCreate, db: Session = Depends(get_db)
):
    return create_user_item(db=db, item=item, user_id=user_id)


@app.get("/items/", response_model=list[Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = get_items(db, skip=skip, limit=limit)
    return items

@app.get("/movies/", response_model=Movie)
def read_Movie(movie_id: int, db: Session = Depends(get_db)):
    db_user = get_movie(db, movie_id=movie_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return db_user

@app.get("/poster/", response_model=Poster)
def read_poster(movie_id: int, db: Session = Depends(get_db)):
    db_user = get_poster(db, movie_id=movie_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Poster not found")
    return db_user

@app.get("/recommend/", response_model=list[Recommend])
def read_recommend(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = get_recommend(db, skip=skip, limit=limit)
    return items