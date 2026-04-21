import sys
import os
from sqlalchemy.orm import Session
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import engine, RoomSchedule, Room

def import_schedule():
    session = Session(bind=engine)
    
    # Example data (Day: 0=Mon, 1=Tue, ..., 4=Fri)
    # format: (room_id, day, start, end, subject)
    schedules = [
        ("522", 0, "08:00", "12:00", "วิชาทฤษฎีดนตรี 1"),
        ("523", 1, "13:00", "16:00", "วิชาประวัติดนตรี"),
        ("530", 2, "09:00", "12:00", "สัมมนากิจกรรมดนตรี"),
        # Add more based on the Google Sheet
    ]
    
    try:
        # Clear existing schedules if you want to refresh
        session.query(RoomSchedule).delete()
        
        for rid, day, start, end, subject in schedules:
            sch = RoomSchedule(
                room_id=rid,
                day_of_week=day,
                start_time=start,
                end_time=end,
                subject_name=subject
            )
            session.add(sch)
        
        session.commit()
        print(f"Imported {len(schedules)} schedule slots.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import_schedule()
