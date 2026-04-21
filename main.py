from fastapi import FastAPI, Body, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from models import Session, Room, Booking, User, RoomSchedule
from pydantic import BaseModel
import shutil
import os
import datetime

class PhoneUpdate(BaseModel):
    student_id: str
    phone: str

app = FastAPI()

# --- เพิ่มโค้ดส่วนนี้เพื่อบังคับสร้างโฟลเดอร์หากยังไม่มี ---
os.makedirs("photo", exist_ok=True)
os.makedirs("uploads/student_cards", exist_ok=True)
os.makedirs("uploads/profiles", exist_ok=True)
os.makedirs("templates", exist_ok=True) # เผื่อโฟลเดอร์ templates หายไปด้วย
# ----------------------------------------------------

# เชื่อมต่อโฟลเดอร์รูปภาพ
app.mount("/photo", StaticFiles(directory="photo"), name="photo")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 1. หน้าแรก
@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# 2. ดึงข้อมูลห้อง (กรองตามหมวดหมู่ได้)
@app.get("/rooms")
def get_rooms(category: str = None):
    session = Session()
    try:
        query = session.query(Room)
        if category:
            if category == 'thai':
                query = query.filter(Room.category.in_(['thai', 'both']))
            elif category == 'inter':
                query = query.filter(Room.category.in_(['inter', 'both']))
            elif category == 'both':
                query = query.filter(Room.category == 'both')
            elif category == 'restricted':
                query = query.filter(Room.category == 'restricted')
        rooms = query.all()
        return rooms
    finally:
        session.close()

# 2.1 ดึงการจองของฉัน
@app.get("/my_bookings")
def get_my_bookings(student_id: str):
    session = Session()
    try:
        bookings = session.query(Booking, Room.room_name).join(Room, Booking.room_id == Room.room_id).filter(
            Booking.student_id == student_id
        ).all()
        
        result = []
        for b, room_name in bookings:
            result.append({
                "booking_id": b.booking_id,
                "room_name": room_name,
                "room_id": b.room_id,
                "date": b.booking_date,
                "start": b.start_time,
                "end": b.end_time
            })
        return result
    finally:
        session.close()

# 2.2 ยกเลิกการจอง
@app.post("/cancel_booking")
def cancel_booking(booking_id: int = Body(...)):
    session = Session()
    try:
        booking = session.query(Booking).filter(Booking.booking_id == booking_id).first()
        if booking:
            session.delete(booking)
            session.commit()
            return {"status": "success", "message": "ยกเลิกการจองเรียบร้อยแล้ว"}
        return {"status": "error", "message": "ไม่พบข้อมูลการจอง"}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()

# 3. เช็กความว่าง
@app.get("/check_availability")
def check_availability(room_id: str, date: str, start: int = 7, end: int = 22):
    session = Session()
    try:
        slots = [f"{str(h).zfill(2)}:00" for h in range(start, end)]
        availability = []
        
        existing_bookings = session.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.booking_date == date
        ).all()
        
        # ดึงตารางเรียน
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        schedules = session.query(RoomSchedule).filter(
            RoomSchedule.room_id == room_id,
            RoomSchedule.day_of_week == day_of_week
        ).all()

        def get_status(slot_time):
            slot_h = int(slot_time.split(":")[0])
            
            # เช็คตารางเรียนก่อน
            for sch in schedules:
                try:
                    sch_start_h = int(sch.start_time.split(":")[0])
                    sch_end_h = int(sch.end_time.split(":")[0])
                    if sch_start_h <= slot_h < sch_end_h:
                        return f"ติดเรียน: {sch.subject_name}"
                except: continue
                
            # เช็คการจอง
            for b in existing_bookings:
                try:
                    b_start_h = int(b.start_time.split(":")[0])
                    b_end_h = int(b.end_time.split(":")[0])
                    if b_start_h <= slot_h < b_end_h:
                        return "จองแล้ว"
                except: continue
                
            return "ว่าง"

        for slot in slots:
            status = get_status(slot)
            availability.append({"time": slot, "status": status})
        return availability
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()

# 4. จองห้อง
@app.post("/book")
def create_booking(
    student_id: str = Body(...),
    room_id: str = Body(...),
    date: str = Body(...),
    start: str = Body(...),
    end: str = Body(...),
    band: str = Body(...),
    purpose: str = Body(...),
    teacher_name: str = Body(None)
):
    session = Session()
    try:
        # ดึงข้อมูลผู้ใช้และห้อง
        user = session.query(User).filter(User.student_id == student_id).first()
        room = session.query(Room).filter(Room.room_id == room_id).first()
        
        if not user or not room:
            return {"status": "error", "message": "ไม่พบข้อมูลผู้ใช้หรือห้อง"}

        # 1. เช็กสิทธิ์ตามสาขา (คงเดิม)
        user_major = user.major.strip() if user.major else ""
        is_edu = "ดนตรีศึกษา" in user_major
        is_thai = "ดนตรีไทย" in user_major
        is_inter = "ดนตรีสากล" in user_major

        if room.category == 'restricted':
            return {"status": "error", "message": "ห้องนี้ไม่เปิดให้จองออนไลน์"}
        if room.category == 'thai' and not (is_thai or is_edu):
            return {"status": "error", "message": "เฉพาะนิสิตสาขาดนตรีไทย/ดนตรีศึกษาเท่านั้น"}
        if room.category == 'inter' and not (is_inter or is_edu):
            return {"status": "error", "message": "เฉพาะนิสิตสาขาดนตรีสากล/ดนตรีศึกษาเท่านั้น"}

        # 2. เช็กตารางเรียน (RoomSchedule)
        # แปลงวันที่เป็นวันในสัปดาห์ (0=Monday, 6=Sunday)
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        
        # เช็คว่ามีคาบเรียนที่ทับซ้อนหรือไม่
        new_start_h = int(start.split(":")[0])
        new_end_h = int(end.split(":")[0])
        
        schedules = session.query(RoomSchedule).filter(
            RoomSchedule.room_id == room_id,
            RoomSchedule.day_of_week == day_of_week
        ).all()
        
        for sch in schedules:
            sch_start_h = int(sch.start_time.split(":")[0])
            sch_end_h = int(sch.end_time.split(":")[0])
            if max(new_start_h, sch_start_h) < min(new_end_h, sch_end_h):
                return {"status": "error", "message": f"ช่วงเวลานี้ถูกล็อกไว้สำหรับวิชาเรียน: {sch.subject_name}"}

        # 3. ตรวจสอบเงื่อนไข Mini Hall (ต้องมีชื่ออาจารย์)
        if room_id == "530" or "Mini Hall" in room.room_name: # อิงตาม populate_rooms.py
            if not teacher_name or teacher_name.strip() == "":
                return {"status": "error", "message": "การจองห้อง Mini Hall ต้องระบุชื่ออาจารย์ผู้รับผิดชอบ"}

        # 4. ตรวจสอบโควตา 3 ชั่วโมงต่อวัน และจำกัดไม่เกิน 2 ห้องต่อวัน
        existing_bookings = session.query(Booking).filter(
            Booking.student_id == student_id,
            Booking.booking_date == date
        ).all()
        
        total_hours = 0
        booked_rooms = set()
        for b in existing_bookings:
            try:
                sh = int(b.start_time.split(":")[0])
                eh = int(b.end_time.split(":")[0])
                total_hours += (eh - sh)
                booked_rooms.add(b.room_id)
            except: continue
            
        new_duration = new_end_h - new_start_h
        
        if total_hours + new_duration > 3:
            return {"status": "error", "message": f"คุณจองเกินโควตา 3 ชั่วโมงต่อวัน (จองไปแล้ว {total_hours} ชม.)"}
            
        if room_id not in booked_rooms and len(booked_rooms) >= 2:
            return {"status": "error", "message": "คุณจองห้องเกินขีดจำกัด 2 ห้องต่อวัน"}

        new_booking = Booking(
            student_id=student_id,
            room_id=room_id,
            booking_date=date,
            start_time=start,
            end_time=end,
            band_type=band,
            purpose=purpose,
            teacher_name=teacher_name
        )
        session.add(new_booking)
        session.commit()
        return {"status": "success", "message": "จองห้องเรียบร้อยแล้ว!"}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()

# 5. สมัครสมาชิก
@app.post("/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    student_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    year: str = Form(...),
    status: str = Form(...),
    faculty: str = Form(...),
    major: str = Form(...),
    phone: str = Form(None),
    student_card: UploadFile = File(...)
):
    session = Session()
    try:
        if not email.endswith("@student.chula.ac.th"):
            return {"status": "error", "message": "กรุณาใช้อีเมลของมหาลัย"}

        # เช็กรหัสนิสิตดนตรีเท่านั้น (ต้องอยู่ในรายชื่อที่กำหนด)
        # สำหรับตอนนี้จะเช็คเบื้องต้นว่าต้องขึ้นต้นด้วยรหัสที่เกี่ยวข้อง หรือถ้ามีไฟล์รายชื่อจะเช็คจากไฟล์
        # สมมติว่าเรามีไฟล์ music_students.txt เก็บรายชื่อรหัสนิสิต
        valid_student = False
        if os.path.exists("music_students.txt"):
            with open("music_students.txt", "r") as f:
                valid_ids = f.read().splitlines()
                if student_id in valid_ids:
                    valid_student = True
        else:
            # ถ้าไม่มีไฟล์ ให้ผ่านไปก่อนแต่แจ้งเตือน Admin (หรือจะล็อกไว้เลยก็ได้)
            valid_student = True # เปลี่ยนเป็น False ถ้าต้องการล็อกเข้มงวดตั้งแต่แรก

        if not valid_student:
             return {"status": "error", "message": "รหัสนักศึกษานี้ไม่ได้อยู่ในสาขาดนตรีที่ได้รับอนุญาต"}

        if session.query(User).filter(User.email == email).first():
            return {"status": "error", "message": "อีเมลนี้ถูกใช้งานแล้ว!"}
            
        if session.query(User).filter(User.student_id == student_id).first():
            return {"status": "error", "message": "รหัสนักศึกษานี้ถูกใช้งานแล้ว!"}

        # บันทึกรูปบัตรนิสิต
        card_filename = f"card_{student_id}_{student_card.filename}"
        card_path = os.path.join("uploads/student_cards", card_filename)
        with open(card_path, "wb") as buffer:
            shutil.copyfileobj(student_card.file, buffer)

        new_user = User(
            email=email,
            password=password,
            student_id=student_id,
            name=f"{first_name} {last_name}",
            year=year,
            status=status,
            faculty=faculty,
            major=major,
            phone=phone,
            student_card_url=f"/uploads/student_cards/{card_filename}"
        )
        session.add(new_user)
        session.commit()
        return {"status": "success", "message": "สมัครสมาชิกสำเร็จ! กรุณารอการตรวจสอบข้อมูล"}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()

# 6. ล็อกอิน
@app.post("/login")
def login(email: str = Body(...), password: str = Body(...)):
    session = Session()
    try:
        user = session.query(User).filter(User.email == email, User.password == password).first()
        if user:
            return {
                "status": "success", 
                "student_id": user.student_id,
                "name": user.name,
                "year": user.year,
                "faculty": user.faculty,
                "major": user.major,
                "email": user.email,
                "phone": user.phone,
                "profile_pic": user.profile_pic_url
            }
        return {"status": "error", "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"}
    finally:
        session.close()

@app.post("/upload_profile_pic")
async def upload_profile_pic(student_id: str = Form(...), file: UploadFile = File(...)):
    session = Session()
    try:
        user = session.query(User).filter(User.student_id == student_id).first()
        if not user:
            return {"status": "error", "message": "ไม่พบผู้ใช้"}
            
        filename = f"profile_{student_id}_{file.filename}"
        path = os.path.join("uploads/profiles", filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        user.profile_pic_url = f"/uploads/profiles/{filename}"
        session.commit()
        return {"status": "success", "profile_pic": user.profile_pic_url}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        session.close()

# 7. อัปเดตเบอร์โทร
@app.post("/update_phone")
def update_phone(data: PhoneUpdate):
    session = Session()
    try:
        user = session.query(User).filter(User.student_id == data.student_id).first()
        if user:
            user.phone = data.phone
            session.commit()
            return {"status": "success"}
        return {"status": "error", "message": "ไม่พบผู้ใช้"}
    finally:
        session.close()

# 8. ลบผู้ใช้ (Admin)
@app.post("/admin/delete_user")
def delete_user(email: str = Body(...)):
    session = Session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user:
            session.query(Booking).filter(Booking.student_id == user.student_id).delete()
            session.delete(user)
            session.commit()
            return {"status": "success", "message": "ลบเรียบร้อย"}
        return {"status": "error", "message": "ไม่พบอีเมล"}
    finally:
        session.close()
