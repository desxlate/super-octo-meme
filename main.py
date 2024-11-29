from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = "sqlite:///./repair_requests.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    tablename = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)

class RepairRequest(Base):
    tablename = "repair_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_date = Column(DateTime, default=datetime.utcnow)
    equipment_type = Column(String)
    model = Column(String)
    problem_description = Column(String)
    client_name = Column(String)
    phone_number = Column(String)
    status = Column(Enum("новая", "в процессе", "завершена")) 
    master_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    master = relationship("User")

Base.metadata.create_all(bind=engine)

class RepairRequestCreate(BaseModel):
    equipment_type: str
    model: str
    problem_description: str
    client_name: str
    phone_number: str
    status: str
    master_id: Optional[int] = None

class RepairRequestResponse(RepairRequestCreate):
    id: int
    request_date: datetime
    
    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str):
    return pwd_context.hash(password)

@app.post("/users/", response_model=UserCreate)
def create_user(user: UserCreate, db: SessionLocal = Depends(get_db)):
    db_user = User(username=user.username, hashed_password=hash_password(user.password), role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/requests/", response_model=RepairRequestResponse)
def create_request(request: RepairRequestCreate, db: SessionLocal = Depends(get_db)):
    db_request = RepairRequest(**request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


@app.get("/requests/", response_model=List[RepairRequestResponse])
def read_requests(skip: int = 0, limit: int = 10, db: SessionLocal = Depends(get_db)):
    return db.query(RepairRequest).offset(skip).limit(limit).all()


@app.get("/requests/{request_id}", response_model=RepairRequestResponse)
def read_request(request_id: int, db: SessionLocal = Depends(get_db)):
    db_request = db.query(RepairRequest).filter(RepairRequest.id == request_id).first()
    if db_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return db_request


@app.put("/requests/{request_id}", response_model=RepairRequestResponse)
def update_request(request_id: int, request: RepairRequestCreate, db: SessionLocal = Depends(get_db)):
    db_request = db.query(RepairRequest).filter(RepairRequest.id == request_id).first()
    if db_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    for var, value in request.dict().items():
        setattr(db_request, var, value) if value else None
    db.commit()
    db.refresh(db_request)
    return db_request


@app.get("/statistics/")
def get_statistics(db: SessionLocal = Depends(get_db)):
    completed_requests = db.query(RepairRequest).filter(RepairRequest.status == "завершена").count()
    average_time = "Ожидание реализации"
    return {
        "completed_requests_count": completed_requests,
        "average_time": average_time
    }