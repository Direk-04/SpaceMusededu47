from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    email = Column(String, primary_key=True)
    password = Column(String)
    student_id = Column(String, unique=True)
    name = Column(String)
    year = Column(String)
    status = Column(String)
    faculty = Column(String)
    major = Column(String)
    phone = Column(String)
    profile_pic_url = Column(String)
    student_card_url = Column(String)
    
class Room(Base):
    __tablename__ = 'rooms'
    room_id = Column(String, primary_key=True) 
    room_name = Column(String)
    image_url = Column(String)
    category = Column(String) # 'thai', 'inter', 'both', 'restricted'
    is_bookable = Column(Integer, default=1) # 1 = yes, 0 = no

class Booking(Base):
    __tablename__ = 'bookings'
    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey('users.student_id'))
    room_id = Column(String, ForeignKey('rooms.room_id'))
    booking_date = Column(String)
    start_time = Column(String)
    end_time = Column(String)
    band_type = Column(String)
    purpose = Column(String)
    teacher_name = Column(String) # For Mini Hall

class RoomSchedule(Base):
    __tablename__ = 'room_schedules'
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String, ForeignKey('rooms.room_id'))
    day_of_week = Column(Integer, nullable=True) # 0=Monday, 6=Sunday
    specific_date = Column(String, nullable=True) # YYYY-MM-DD
    start_time = Column(String)
    end_time = Column(String)
    subject_name = Column(String)

engine = create_engine('sqlite:///music_room.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
