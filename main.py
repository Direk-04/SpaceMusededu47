from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from models import Session, Room, Booking, User
from pydantic import BaseModel

class PhoneUpdate(BaseModel):
    student_id: str
    phone: str

app = FastAPI()

# เชื่อมต่อโฟลเดอร์รูปภาพ
app.mount("/photo", StaticFiles(directory="photo"), name="photo")

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
        # กำหนดช่วงเวลาที่ต้องการแสดง (default 07:00 - 22:00)
        slots = [f"{str(h).zfill(2)}:00" for h in range(start, end)]
        availability = []
        
        # ดึงการจองทั้งหมดของห้องในวันที่เลือก
        existing_bookings = session.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.booking_date == date
        ).all()

        # ฟังก์ชันตรวจสอบว่าช่วงเวลา slot ถูกจองหรือไม่
        def is_booked(slot_time):
            slot_h = int(slot_time.split(":")[0])
            for b in existing_bookings:
                try:
                    b_start_h = int(b.start_time.split(":")[0])
                    b_end_h = int(b.end_time.split(":")[0])
                    # ถ้า slot อยู่ในช่วง start ถึง end ของการจอง
                    if b_start_h <= slot_h < b_end_h:
                        return True
                except:
                    continue
            return False

        for slot in slots:
            status = "จองแล้ว" if is_booked(slot) else "ว่าง"
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
    band: str = Body(...)
):
    session = Session()
    try:
        # ดึงข้อมูลผู้ใช้และห้องเพื่อเช็กสาขา
        user = session.query(User).filter(User.student_id == student_id).first()
        room = session.query(Room).filter(Room.room_id == room_id).first()
        
        if not user or not room:
            return {"status": "error", "message": "ไม่พบข้อมูลผู้ใช้หรือห้อง"}

        # เช็กสิทธิ์การจองตามสาขา
        # ถ้าเป็นห้อง 'both' ทุกคนจองได้
        # ถ้าเป็นห้อง 'thai' เฉพาะสาขาดนตรีไทยจองได้
        # ถ้าเป็นห้อง 'inter' เฉพาะสาขาดนตรีสากลจองได้
        # ถ้าเป็นห้อง 'restricted' จองไม่ได้เลย
        
        user_major = user.major.strip() if user.major else ""
        
        # กฎการจอง:
        # 1. ถ้าห้องเป็น 'both' -> ทุกคนจองได้
        # 2. ถ้าผู้ใช้เป็น 'ดนตรีศึกษา' (สาขาหลัก) -> จองได้ทุกห้อง
        # 3. ถ้าห้องเป็น 'thai' -> เฉพาะ 'ดนตรีไทย' หรือ 'ดนตรีศึกษา' จองได้
        # 4. ถ้าห้องเป็น 'inter' -> เฉพาะ 'ดนตรีสากล' หรือ 'ดนตรีศึกษา' จองได้
        
        is_edu = "ดนตรีศึกษา" in user_major
        is_thai = "ดนตรีไทย" in user_major
        is_inter = "ดนตรีสากล" in user_major

        if room.category == 'restricted':
            return {"status": "error", "message": "ห้องนี้ไม่เปิดให้จองออนไลน์"}
            
        if room.category == 'thai' and not (is_thai or is_edu):
            return {"status": "error", "message": f"ห้องดนตรีไทยเฉพาะนิสิตสาขาดนตรีไทย/ดนตรีศึกษาเท่านั้น (สาขาของคุณคือ {user_major})"}
            
        if room.category == 'inter' and not (is_inter or is_edu):
            return {"status": "error", "message": f"ห้องดนตรีสากลเฉพาะนิสิตสาขาดนตรีสากล/ดนตรีศึกษาเท่านั้น (สาขาของคุณคือ {user_major})"}

        # ตรวจสอบโควตา 3 ชั่วโมงต่อวัน
        existing_bookings = session.query(Booking).filter(
            Booking.student_id == student_id,
            Booking.booking_date == date
        ).all()
        
        total_hours = 0
        for b in existing_bookings:
            try:
                sh = int(b.start_time.split(":")[0])
                eh = int(b.end_time.split(":")[0])
                total_hours += (eh - sh)
            except: continue
            
        new_h = int(start.split(":")[0])
        new_e = int(end.split(":")[0])
        new_duration = new_e - new_h
        
        if total_hours + new_duration > 3:
            return {"status": "error", "message": f"คุณจองเกินโควตา 3 ชั่วโมงต่อวัน (จองไปแล้ว {total_hours} ชม.)"}

        new_booking = Booking(
            student_id=student_id,
            room_id=room_id,
            booking_date=date,
            start_time=start,
            end_time=end,
            band_type=band
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
def register(
    email: str = Body(...),
    password: str = Body(...),
    student_id: str = Body(...),
    first_name: str = Body(...),
    last_name: str = Body(...),
    year: str = Body(...),
    status: str = Body(...),
    faculty: str = Body(...),
    major: str = Body(...),
    phone: str = Body(None)
):
    session = Session()
    try:
        if not email.endswith("@student.chula.ac.th"):
            return {"status": "error", "message": "กรุณาใช้อีเมลของมหาลัย"}

        if session.query(User).filter(User.email == email).first():
            return {"status": "error", "message": "อีเมลนี้ถูกใช้งานแล้ว!"}
            
        if session.query(User).filter(User.student_id == student_id).first():
            return {"status": "error", "message": "รหัสนักศึกษานี้ถูกใช้งานแล้ว!"}

        new_user = User(
            email=email,
            password=password,
            student_id=student_id,
            name=f"{first_name} {last_name}",
            year=year,
            status=status,
            faculty=faculty,
            major=major,
            phone=phone
        )
        session.add(new_user)
        session.commit()
        return {"status": "success", "message": "สมัครสมาชิกสำเร็จ!"}
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
                "phone": user.phone
            }
        return {"status": "error", "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"}
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
