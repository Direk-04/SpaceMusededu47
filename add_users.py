from models import Session, User, Base, engine


User.__table__.drop(engine, checkfirst=True)
Base.metadata.create_all(engine)
session = Session()


user1 = User(
    email="6642117127@student.chula.ac.th", 
    password="534jhPxu", 
    student_id="6642117127",
    name="นายพงษ์พิพัฒน์ โพธิบุตร",
    status="นิสิต",
    faculty="ครุศาสตร์",
    major="ดนตรีศึกษา"
)

try:
    session.add(user1)
    session.commit()
    print("เพิ่มข้อมูลผู้ใช้แบบจัดเต็มสำเร็จแล้ว!")
except Exception as e:
    session.rollback()
    print("เกิดข้อผิดพลาด:", e)
finally:
    session.close()