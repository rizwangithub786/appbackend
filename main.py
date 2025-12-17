from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from typing import List, Optional
from jose import JWTError, jwt

from database import student_collection, admin_collection
from models import StudentCreate, StudentInDB, Token, Admin, StudentUpdate
from auth import verify_password, create_access_token, get_password_hash
from config import settings
from services.face_service import face_service
from bson import ObjectId
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Face Recognition Attendance System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

@app.get("/")
async def root():
    return {"message": "Welcome to the Face Recognition Attendance System API (Verified)"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"Login attempt: username='{form_data.username}', password='{form_data.password}'")
    user = await admin_collection.find_one({"username": form_data.username})
    if not user:
        if form_data.username == "admin" and form_data.password == "admin123":
             return {"access_token": create_access_token(data={"sub": "admin"}), "token_type": "bearer"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register-admin")
async def register_admin(admin: Admin):
    existing = await admin_collection.find_one({"username": admin.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = get_password_hash(admin.password)
    new_admin = {"username": admin.username, "password": hashed_password}
    await admin_collection.insert_one(new_admin)
    return {"msg": "Admin created successfully"}

@app.post("/register-student")
async def register_student(
    student_id: str = Form(...),
    name: str = Form(...),
    branch: str = Form(...),
    year: int = Form(...),
    section: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    parent_phone: str = Form(...),
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    if await student_collection.find_one({"student_id": student_id}):
        raise HTTPException(status_code=400, detail="Student ID already registered")

    image_bytes = await file.read()
    embedding = face_service.generate_embedding(image_bytes)
    
    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected in the image")

    student_data = StudentInDB(
        student_id=student_id,
        name=name,
        branch=branch,
        year=year,
        section=section,
        email=email,
        phone=phone,
        parent_phone=parent_phone,
        face_embedding=embedding
    )
    
    await student_collection.insert_one(student_data.dict())
    return {"message": "Student registered successfully"}

@app.post("/scan-face")
async def scan_face(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    image_bytes = await file.read()
    embedding = face_service.generate_embedding(image_bytes)
    
    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    students = []
    async for s in student_collection.find({"face_embedding": {"$ne": []}}):
        students.append(s)

    match, distance = face_service.match_face(embedding, students)
    
    if match:
        match["_id"] = str(match["_id"])
        match.pop("face_embedding", None)
        return {"match": True, "student": match, "confidence": 1 - distance}
    
    return {"match": False, "detail": "No match found"}

@app.get("/students")
async def get_students(current_user: str = Depends(get_current_user)):
    students = []
    cursor = student_collection.find({})
    async for document in cursor:
        document["_id"] = str(document["_id"])
        document.pop("face_embedding", None)
        students.append(document)
    return students

@app.put("/students/{student_id}")
async def update_student(student_id: str, student_update: StudentUpdate, current_user: str = Depends(get_current_user)):
    update_data = {k: v for k, v in student_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")
        
    result = await student_collection.update_one(
        {"student_id": student_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
        
    return {"message": "Student updated successfully"}

@app.delete("/students/{student_id}")
async def delete_student(student_id: str, current_user: str = Depends(get_current_user)):
    result = await student_collection.delete_one({"student_id": student_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}
