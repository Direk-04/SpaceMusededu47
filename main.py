from fastapi import FastAPI, Body, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, text
from models import Session, Room, Booking, User, RoomSchedule
from pydantic import BaseModel
import shutil
import os
import datetime

class PhoneUpdate(BaseModel):
    student_id: str
    phone: str

class CancelRequest(BaseModel):
    booking_id: int

class LoginRequest(BaseModel):
    email: str
    password: str

class BookingRequest(BaseModel):
    student_id: str
    room_id: str
    date: str
    start: str
    end: str
    band: str
    purpose: str
    teacher_name: str = None

class DeleteUserRequest(BaseModel):
    student_id: str

app = FastAPI()

os.makedirs("photo", exist_ok=True)
os.makedirs("uploads/student_cards", exist_ok=True)
os.makedirs("uploads/profiles", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# --- โค้ดบรรทัดเดิมของคุณ (ไม่ต้องเปลี่ยนแปลง) ---
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
        sid = student_id.strip()
        print(f"DEBUG: Fetching for SID: '{sid}'")
        bookings = session.query(Booking).filter(Booking.student_id == sid).all()
        print(f"DEBUG: Found {len(bookings)} bookings")
        
        result = []
        for b in bookings:
            room = session.query(Room).filter(Room.room_id == b.room_id).first()
            result.append({
                "booking_id": b.booking_id,
                "room_name": room.room_name if room else f"Room {b.room_id}",
                "room_id": b.room_id,
                "date": b.booking_date,
                "start": b.start_time,
                "end": b.end_time,
                "purpose": b.purpose,
                "teacher": b.teacher_name
            })
        return result
    finally:
        session.close()

# 2.2 ยกเลิกการจอง
@app.post("/cancel_booking")
def cancel_booking(data: CancelRequest):
    session = Session()
    try:
        booking = session.query(Booking).filter(Booking.booking_id == data.booking_id).first()
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

# 2.3 ดึงสถิติการใช้งานของนิสิต
@app.get("/student_stats")
def get_student_stats(student_id: str):
    session = Session()
    try:
        sid = student_id.strip()
        bookings = session.query(Booking).filter(Booking.student_id == sid).all()
        total_bookings = len(bookings)
        total_hours = 0
        room_usage = {}
        
        for b in bookings:
            try:
                sh = int(b.start_time.split(":")[0])
                eh = int(b.end_time.split(":")[0])
                total_hours += (eh - sh)
                room_usage[b.room_id] = room_usage.get(b.room_id, 0) + 1
            except: continue
            
        fav_room = "ยังไม่มี"
        if room_usage:
            fav_room_id = max(room_usage, key=room_usage.get)
            room = session.query(Room).filter(Room.room_id == fav_room_id).first()
            fav_room = room.room_name if room else fav_room_id

        # ดึงการจองครั้งถัดไป (Upcoming)
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        upcoming = session.query(Booking, Room.room_name).join(Room, Booking.room_id == Room.room_id).filter(
            Booking.student_id == sid,
            Booking.booking_date >= today_str
        ).order_by(Booking.booking_date.asc(), Booking.start_time.asc()).first()

        upcoming_data = None
        if upcoming:
            b, r_name = upcoming
            upcoming_data = {
                "room": r_name,
                "date": b.booking_date,
                "time": f"{b.start_time} - {b.end_time}"
            }

        return {
            "total_bookings": total_bookings,
            "total_hours": total_hours,
            "fav_room": fav_room,
            "upcoming": upcoming_data
        }
    finally:
        session.close()

# 3. เช็กความว่าง
# 1.2 ดึงข้อมูลห้องว่างแบบ Batch (Optimized)
@app.get("/batch_availability")
def batch_availability(category: str, date: str, start: int = 7, end: int = 22):
    session = Session()
    try:
        now = datetime.datetime.now()
        current_date_str = now.strftime("%Y-%m-%d")
        current_h = now.hour

        # 1. ดึงข้อมูลห้องทั้งหมดในหมวดหมู่
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
        
        # 2. ดึงการจองและตารางเรียนทั้งหมดของวันนั้น (ทีเดียว)
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        
        all_bookings = session.query(Booking).filter(Booking.booking_date == date).all()
        all_schedules = session.query(RoomSchedule).filter(
            or_(RoomSchedule.day_of_week == day_of_week, RoomSchedule.specific_date == date)
        ).all()

        # ดึงสถานะปัจจุบัน (Right Now) เพื่อใช้ทำ Badge
        current_bookings = []
        current_schedules = []
        if date == current_date_str:
            current_bookings = all_bookings
            current_schedules = all_schedules
        else:
            # ถ้าดูวันอื่น ต้องดึงของวันนี้มาเช็คสถานะ Live
            current_bookings = session.query(Booking).filter(Booking.booking_date == current_date_str).all()
            today_dow = now.weekday()
            current_schedules = session.query(RoomSchedule).filter(
                or_(RoomSchedule.day_of_week == today_dow, RoomSchedule.specific_date == current_date_str)
            ).all()

        results = {}
        time_slots = range(start, end)

        for r in rooms:
            room_slots = []
            # ใช้ strip() เพื่อความแม่นยำในการเทียบ ID
            rid_clean = r.room_id.strip()
            r_bookings = [b for b in all_bookings if b.room_id.strip() == rid_clean]
            r_schedules = [s for s in all_schedules if s.room_id.strip() == rid_clean]

            # คำนวณ Live Status
            is_busy_now = False
            # Check current schedule
            curr_room_sch = [s for s in current_schedules if s.room_id.strip() == rid_clean]
            for sch in curr_room_sch:
                try:
                    sh = int(sch.start_time.split(":")[0])
                    eh = int(sch.end_time.split(":")[0])
                    if sh <= current_h < eh:
                        is_busy_now = True; break
                except: continue
            
            if not is_busy_now:
                # Check current booking
                curr_room_book = [b for b in current_bookings if b.room_id.strip() == rid_clean]
                for b in curr_room_book:
                    try:
                        sh = int(b.start_time.split(":")[0])
                        eh = int(b.end_time.split(":")[0])
                        if sh <= current_h < eh:
                            is_busy_now = True; break
                    except: continue

            for slot_h in time_slots:
                status = "ว่าง"
                for sch in r_schedules:
                    try:
                        sh = int(sch.start_time.split(":")[0])
                        eh = int(sch.end_time.split(":")[0])
                        if sh <= slot_h < eh:
                            status = f"ติดเรียน: {sch.subject_name}"; break
                    except: continue
                if status == "ว่าง":
                    for b in r_bookings:
                        try:
                            sh = int(b.start_time.split(":")[0])
                            eh = int(b.end_time.split(":")[0])
                            if sh <= slot_h < eh:
                                status = f"จองแล้ว: {b.band_type}"; break
                        except: continue
                room_slots.append({"time": f"{slot_h:02d}:00", "status": status})
            
            results[r.room_id] = {
                "slots": room_slots,
                "is_busy_now": is_busy_now
            }
            
        return results
    finally:
        session.close()

# 1.3 สรุปสถานะภาพรวม (Live Status)
@app.get("/facility_status")
def get_facility_status():
    session = Session()
    try:
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_h = now.hour
        
        # ดึงห้องทั้งหมดที่จองได้
        all_rooms = session.query(Room).filter(Room.category != 'restricted').all()
        total_rooms = len(all_rooms)
        
        # ดึงการจองชั่วโมงนี้
        bookings = session.query(Booking).filter(
            Booking.booking_date == today_str
        ).all()
        
        day_of_week = now.weekday()
        schedules = session.query(RoomSchedule).filter(
            or_(RoomSchedule.day_of_week == day_of_week, RoomSchedule.specific_date == today_str)
        ).all()
        
        busy_rooms = set()
        # เช็ค Booking
        for b in bookings:
            try:
                bh = int(b.start_time.split(":")[0])
                eh = int(b.end_time.split(":")[0])
                if bh <= current_h < eh:
                    busy_rooms.add(b.room_id)
            except: continue

        # เช็ค Schedule
        for sch in schedules:
            try:
                sh = int(sch.start_time.split(":")[0])
                eh = int(sch.end_time.split(":")[0])
                if sh <= current_h < eh:
                    busy_rooms.add(sch.room_id)
            except: continue
            
        busy_count = len(busy_rooms & {r.room_id for r in all_rooms})
        available_count = total_rooms - busy_count
        
        return {
            "total": total_rooms,
            "available": max(0, available_count),
            "busy": busy_count,
            "current_hour": f"{current_h:02d}:00"
        }
    finally:
        session.close()

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
            or_(RoomSchedule.day_of_week == day_of_week, RoomSchedule.specific_date == date)
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
                        return f"จองแล้ว: {b.band_type}"
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
def create_booking(data: BookingRequest):
    session = Session()
    try:
        # ดึงข้อมูลผู้ใช้และห้อง
        sid = data.student_id.strip()
        rid = data.room_id.strip()
        user = session.query(User).filter(User.student_id == sid).first()
        room = session.query(Room).filter(Room.room_id == rid).first()
        
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
        dt = datetime.datetime.strptime(data.date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        
        # เช็คว่ามีคาบเรียนที่ทับซ้อนหรือไม่
        new_start_h = int(data.start.split(":")[0])
        new_end_h = int(data.end.split(":")[0])
        
        schedules = session.query(RoomSchedule).filter(
            RoomSchedule.room_id == data.room_id,
            or_(RoomSchedule.day_of_week == day_of_week, RoomSchedule.specific_date == data.date)
        ).all()
        
        for sch in schedules:
            sch_start_h = int(sch.start_time.split(":")[0])
            sch_end_h = int(sch.end_time.split(":")[0])
            if max(new_start_h, sch_start_h) < min(new_end_h, sch_end_h):
                return {"status": "error", "message": f"ช่วงเวลานี้ถูกล็อกไว้สำหรับวิชาเรียน: {sch.subject_name}"}

        # 2.1 เช็คการจองที่ทับซ้อน (Overlap Booking)
        all_room_bookings = session.query(Booking).filter(
            Booking.room_id == data.room_id,
            Booking.booking_date == data.date
        ).all()
        for rb in all_room_bookings:
            try:
                rb_start_h = int(rb.start_time.split(":")[0])
                rb_end_h = int(rb.end_time.split(":")[0])
                if max(new_start_h, rb_start_h) < min(new_end_h, rb_end_h):
                    return {"status": "error", "message": "ห้องนี้ถูกจองไปแล้วในช่วงเวลานี้"}
            except: continue

        # 3. ตรวจสอบเงื่อนไข Mini Hall (ต้องมีชื่ออาจารย์)
        if data.room_id == "MiniHall" or "Mini Hall" in room.room_name: # อิงตาม populate_rooms.py
            if not data.teacher_name or data.teacher_name.strip() == "":
                return {"status": "error", "message": "การจองห้อง Mini Hall ต้องระบุชื่ออาจารย์ผู้รับผิดชอบ"}

        # 4. ตรวจสอบโควตา 3 ชั่วโมงต่อวัน และจำกัดไม่เกิน 2 ห้องต่อวัน
        existing_bookings = session.query(Booking).filter(
            Booking.student_id == data.student_id,
            Booking.booking_date == data.date
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
            
        if data.room_id not in booked_rooms and len(booked_rooms) >= 2:
            return {"status": "error", "message": "คุณจองห้องเกินขีดจำกัด 2 ห้องต่อวัน"}

        new_booking = Booking(
            student_id=data.student_id,
            room_id=data.room_id,
            booking_date=data.date,
            start_time=data.start,
            end_time=data.end,
            band_type=data.band,
            purpose=data.purpose,
            teacher_name=data.teacher_name
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
                valid_ids = [line.strip() for line in f.read().splitlines() if line.strip()]
                if student_id in valid_ids:
                    valid_student = True
        else:
            # ถ้าไม่มีไฟล์ ให้ล็อกไว้ก่อนเพื่อความปลอดภัย
            valid_student = False 

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
def login(data: LoginRequest):
    session = Session()
    try:
        user = session.query(User).filter(User.email == data.email, User.password == data.password).first()
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
                "profile_pic": user.profile_pic_url,
                "student_card": user.student_card_url
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

# 8. Admin Functions
@app.get("/admin/summary")
def get_admin_summary():
    session = Session()
    try:
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        total_bookings_today = session.query(Booking).filter(Booking.booking_date == today_str).count()
        total_users = session.query(User).count()
        total_rooms = session.query(Room).filter(Room.category != 'restricted').count()
        
        # ค้นหาห้องที่ถูกใช้บ่อยที่สุด
        most_popular = session.execute(text("SELECT room_id, COUNT(*) as count FROM bookings GROUP BY room_id ORDER BY count DESC LIMIT 1")).fetchone()
        pop_room_name = "N/A"
        if most_popular:
            r = session.query(Room).filter(Room.room_id == most_popular[0]).first()
            pop_room_name = r.room_name if r else most_popular[0]

        return {
            "today_bookings": total_bookings_today,
            "total_users": total_users,
            "total_rooms": total_rooms,
            "popular_room": pop_room_name
        }
    finally:
        session.close()

@app.get("/admin/all_bookings")
def get_all_bookings():
    session = Session()
    try:
        bookings = session.query(Booking, Room.room_name, User.name).join(Room, Booking.room_id == Room.room_id).join(User, Booking.student_id == User.student_id).order_by(Booking.booking_date.desc(), Booking.start_time.desc()).all()
        result = []
        for b, r_name, u_name in bookings:
            result.append({
                "booking_id": b.booking_id,
                "room_name": r_name,
                "student_name": u_name,
                "student_id": b.student_id,
                "date": b.booking_date,
                "start": b.start_time,
                "end": b.end_time,
                "purpose": b.purpose
            })
        return result
    finally:
        session.close()

@app.post("/admin/cancel_booking")
def admin_cancel_booking(data: CancelRequest):
    session = Session()
    try:
        booking = session.query(Booking).filter(Booking.booking_id == data.booking_id).first()
        if booking:
            session.delete(booking)
            session.commit()
            return {"status": "success", "message": "ยกเลิกการจองโดย Admin เรียบร้อยแล้ว"}
        return {"status": "error", "message": "ไม่พบข้อมูลการจอง"}
    finally:
        session.close()

@app.get("/admin/search_users")
def search_users(q: str):
    session = Session()
    try:
        users = session.query(User).filter(
            or_(User.name.like(f"%{q}%"), User.student_id.like(f"%{q}%"))
        ).all()
        return [{"student_id": u.student_id, "name": u.name, "email": u.email, "major": u.major} for u in users]
    finally:
        session.close()

@app.post("/admin/delete_user")
def delete_user(data: DeleteUserRequest):
    session = Session()
    try:
        user = session.query(User).filter(User.student_id == data.student_id).first()
        if user:
            session.query(Booking).filter(Booking.student_id == user.student_id).delete()
            session.delete(user)
            session.commit()
            return {"status": "success", "message": "ลบเรียบร้อย"}
        return {"status": "error", "message": "ไม่พบผู้ใช้"}
    finally:
        session.close()
