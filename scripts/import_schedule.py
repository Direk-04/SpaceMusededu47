import sys
import os
from sqlalchemy.orm import Session
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import engine, RoomSchedule, Room

def import_schedule():
    session = Session(bind=engine)
    
    # Day mapping: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
    # format: (room_id, day, start, end, subject)
    schedules = [
        # Mini Hall (MiniHall)
        ("MiniHall", 0, "09:00", "12:00", "ENS341 Music Business"),
        ("MiniHall", 0, "13:00", "16:00", "ENS442 Music Entrepreneurship"),
        ("MiniHall", 1, "09:00", "12:00", "ENS231 Western Music History I"),
        ("MiniHall", 1, "13:00", "16:00", "ENS232 Western Music History II"),
        ("MiniHall", 2, "09:00", "12:00", "ENS111 Music Theory I"),
        ("MiniHall", 2, "13:00", "16:00", "ENS112 Music Theory II"),
        ("MiniHall", 3, "09:00", "12:00", "ENS311 Form and Analysis"),
        ("MiniHall", 3, "13:00", "16:00", "ENS312 Counterpoint"),
        ("MiniHall", 4, "09:00", "12:00", "ENS491 Senior Project I"),
        ("MiniHall", 4, "13:00", "16:00", "ENS492 Senior Project II"),

        # Room 504
        ("504", 0, "09:00", "12:00", "MS242 Music Theory IV (Sec 1)"),
        ("504", 0, "13:00", "16:00", "MS242 Music Theory IV (Sec 2)"),
        ("504", 1, "09:00", "12:00", "MS142 Music Theory II (Sec 1)"),
        ("504", 1, "13:00", "16:00", "MS142 Music Theory II (Sec 2)"),
        ("504", 2, "09:00", "12:00", "MS342 Form and Analysis (Sec 1)"),
        ("504", 2, "13:00", "16:00", "MS342 Form and Analysis (Sec 2)"),
        ("504", 3, "09:00", "12:00", "MS441 Counterpoint (Sec 1)"),
        ("504", 3, "13:00", "16:00", "MS441 Counterpoint (Sec 2)"),

        # Room 509
        ("509", 0, "09:00", "12:00", "MS112 Western Music History II (Sec 1)"),
        ("509", 0, "13:00", "16:00", "MS112 Western Music History II (Sec 2)"),
        ("509", 1, "09:00", "12:00", "MS212 Western Music History IV (Sec 1)"),
        ("509", 1, "13:00", "16:00", "MS212 Western Music History IV (Sec 2)"),
        ("509", 2, "09:00", "12:00", "MS311 Thai Music History (Sec 1)"),
        ("509", 2, "13:00", "16:00", "MS311 Thai Music History (Sec 2)"),
        ("509", 3, "09:00", "12:00", "MS411 Contemporary Music (Sec 1)"),
        ("509", 3, "13:00", "16:00", "MS411 Contemporary Music (Sec 2)"),

        # Room 511
        ("511", 0, "09:00", "12:00", "MS132 Solfège II (Sec 1)"),
        ("511", 0, "13:00", "16:00", "MS132 Solfège II (Sec 2)"),
        ("511", 1, "09:00", "12:00", "MS232 Solfège IV (Sec 1)"),
        ("511", 1, "13:00", "16:00", "MS232 Solfège IV (Sec 2)"),
        ("511", 2, "09:00", "12:00", "MS331 Conducting I (Sec 1)"),
        ("511", 2, "13:00", "16:00", "MS331 Conducting I (Sec 2)"),
        ("511", 3, "09:00", "12:00", "MS431 Orchestration (Sec 1)"),
        ("511", 3, "13:00", "16:00", "MS431 Orchestration (Sec 2)"),

        # Room 512
        ("512", 0, "09:00", "12:00", "MS122 Keyboard Skills II (Sec 1)"),
        ("512", 0, "13:00", "16:00", "MS122 Keyboard Skills II (Sec 2)"),
        ("512", 1, "09:00", "12:00", "MS222 Keyboard Skills IV (Sec 1)"),
        ("512", 1, "13:00", "16:00", "MS222 Keyboard Skills IV (Sec 2)"),
        ("512", 2, "09:00", "12:00", "MS321 Piano Pedagogy (Sec 1)"),
        ("512", 2, "13:00", "16:00", "MS321 Piano Pedagogy (Sec 2)"),
        ("512", 3, "09:00", "12:00", "MS421 Piano Literature (Sec 1)"),
        ("512", 3, "13:00", "16:00", "MS421 Piano Literature (Sec 2)"),

        # Room 513
        ("513", 0, "09:00", "12:00", "MS152 String Methods II (Sec 1)"),
        ("513", 0, "13:00", "16:00", "MS152 String Methods II (Sec 2)"),
        ("513", 1, "09:00", "12:00", "MS252 Woodwind Methods II (Sec 1)"),
        ("513", 1, "13:00", "16:00", "MS252 Woodwind Methods II (Sec 2)"),
        ("513", 2, "09:00", "12:00", "MS351 Brass Methods I (Sec 1)"),
        ("513", 2, "13:00", "16:00", "MS351 Brass Methods I (Sec 2)"),
        ("513", 3, "09:00", "12:00", "MS451 Percussion Methods (Sec 1)"),
        ("513", 3, "13:00", "16:00", "MS451 Percussion Methods (Sec 2)"),

        # Rooms 514-521 (From Previous Turns)
        ("514", 0, "09:00", "12:00", "Introduction to Music Theory"),
        ("514", 1, "13:00", "16:00", "Western Music History I"),
        ("514", 2, "09:00", "12:00", "Ear Training I"),
        ("514", 3, "13:00", "16:00", "Music Appreciation"),
        ("514", 4, "09:00", "12:00", "Keyboard Skills I"),
        ("515", 0, "13:00", "16:00", "Harmony I"),
        ("515", 1, "09:00", "12:00", "Form and Analysis"),
        ("515", 2, "13:00", "16:00", "Counterpoint I"),
        ("515", 3, "09:00", "12:00", "Orchestration I"),
        ("515", 4, "13:00", "16:00", "Composition I"),
        ("516", 0, "09:00", "12:00", "Conducting I"),
        ("516", 1, "13:00", "16:00", "Choral Conducting"),
        ("516", 2, "09:00", "12:00", "Instrumental Conducting"),
        ("516", 3, "13:00", "16:00", "Score Reading"),
        ("516", 4, "09:00", "12:00", "Rehearsal Techniques"),
        ("517", 0, "13:00", "16:00", "Music Technology I"),
        ("517", 1, "09:00", "12:00", "Digital Audio Workstation"),
        ("517", 2, "13:00", "16:00", "Sound Synthesis"),
        ("517", 3, "09:00", "12:00", "Music Production"),
        ("517", 4, "13:00", "16:00", "Audio Engineering"),
        ("518", 0, "09:00", "12:00", "Ethnomusicology"),
        ("518", 1, "13:00", "16:00", "World Music"),
        ("518", 2, "09:00", "12:00", "Thai Music History"),
        ("518", 3, "13:00", "16:00", "Folk Music Research"),
        ("518", 4, "09:00", "12:00", "Cultural Studies in Music"),
        ("520", 0, "13:00", "16:00", "Jazz Theory I"),
        ("520", 1, "09:00", "12:00", "Jazz Improvisation I"),
        ("520", 2, "13:00", "16:00", "Jazz History"),
        ("520", 3, "09:00", "12:00", "Jazz Arranging I"),
        ("520", 4, "13:00", "16:00", "Jazz Ensemble"),
        ("521", 0, "09:00", "12:00", "Music Education Philosophy"),
        ("521", 1, "13:00", "16:00", "Psychology of Music"),
        ("521", 2, "09:00", "12:00", "Teaching Methods I"),
        ("521", 3, "13:00", "16:00", "Curriculum Development"),
        ("521", 4, "09:00", "12:00", "Measurement and Evaluation"),

        # Room 531 (Voice)
        ("531", 0, "09:00", "10:00", "Voice 2"),
        ("531", 0, "10:00", "11:00", "Voice 4"),
        ("531", 0, "11:00", "12:00", "Voice 6"),
        ("531", 1, "09:00", "10:00", "Voice 2"),
        ("531", 1, "10:00", "11:00", "Voice 4"),
        ("531", 1, "13:00", "14:00", "Voice 8"),
        ("531", 2, "09:00", "10:00", "Voice 2"),
        ("531", 2, "10:00", "11:00", "Voice 4"),
        ("531", 3, "09:00", "10:00", "Voice 2"),
        ("531", 3, "10:00", "11:00", "Voice 4"),
        ("531", 4, "09:00", "10:00", "Voice 2"),

        # Keyboard Rooms
        ("534/7", 0, "09:00", "11:00", "Keyboard Skills 2"),
        ("534/7", 1, "13:00", "15:00", "Keyboard Skills 4"),
        ("534/7", 2, "09:00", "11:00", "Keyboard Skills 2"),
        ("534/7", 3, "10:00", "12:00", "Applied Piano 2"),
        ("534/8", 0, "13:00", "15:00", "Keyboard Skills 2"),
        ("534/8", 1, "09:00", "11:00", "Keyboard Skills 4"),
        ("534/8", 2, "13:00", "15:00", "Keyboard Skills 2"),
        ("534/9", 0, "10:00", "12:00", "Applied Piano 4"),
        ("534/9", 1, "10:00", "12:00", "Applied Piano 6"),
        ("534/9", 3, "13:00", "15:00", "Keyboard Skills 2"),
        ("534/10", 1, "09:00", "11:00", "Keyboard Skills 2"),
        ("534/10", 2, "10:00", "12:00", "Applied Piano 2"),
        ("534/10", 4, "09:00", "11:00", "Keyboard Skills 4"),
        ("534/11", 0, "09:00", "12:00", "Piano Performance 2"),
        ("534/11", 1, "13:00", "16:00", "Piano Performance 4"),
        ("534/11", 2, "09:00", "12:00", "Piano Performance 6"),
        ("534/11", 3, "09:00", "12:00", "Piano Performance 8"),
        ("534/12", 0, "13:00", "15:00", "Keyboard Literature 2"),
        ("534/12", 1, "09:00", "11:00", "Keyboard Pedagogy 2"),
        ("534/12", 2, "13:00", "15:00", "Collaborative Piano 2"),
        ("534/12", 4, "10:00", "12:00", "Keyboard Literature 4"),
        ("534/13", 1, "10:00", "12:00", "Applied Piano 8"),
        ("534/13", 2, "09:00", "11:00", "Keyboard Skills 4"),
        ("534/13", 3, "14:00", "16:00", "Applied Piano 4"),
        ("534/14", 0, "14:00", "16:00", "Applied Piano 2"),
        ("534/14", 2, "10:00", "12:00", "Applied Piano 6"),
        ("534/14", 4, "13:00", "15:00", "Keyboard Skills 2"),

        # Room 522 (Verified)
        ("522", 0, "09:00", "12:00", "ENS3102 (Sec 1)"),
        ("522", 0, "13:00", "16:00", "ENS3105 (Sec 1)"),
        ("522", 1, "09:00", "12:00", "ENS4101 (Sec 1)"),
        ("522", 1, "13:00", "16:00", "ENS4103 (Sec 1)"),
        ("522", 2, "09:00", "12:00", "ENS3102 (Sec 2)"),
        ("522", 2, "13:00", "16:00", "ENS3105 (Sec 2)"),
        ("522", 3, "09:00", "12:00", "ENS4101 (Sec 2)"),
        ("522", 3, "13:00", "16:00", "ENS4103 (Sec 2)"),

        # Room 527 (Verified)
        ("527", 0, "09:00", "12:00", "MTH1103 (Sec 1)"),
        ("527", 0, "13:00", "16:00", "MTH1103 (Sec 2)"),
        ("527", 1, "09:00", "12:00", "MTH2103 (Sec 1)"),
        ("527", 1, "13:00", "16:00", "MTH2103 (Sec 2)"),
        ("527", 2, "09:00", "12:00", "MTH1103 (Sec 3)"),
        ("527", 2, "13:00", "16:00", "MTH1103 (Sec 4)"),
        ("527", 3, "09:00", "12:00", "MTH2103 (Sec 3)"),
        ("527", 3, "13:00", "16:00", "MTH2103 (Sec 4)"),
    ]
    
    try:
        # Clear existing RECURRING schedules
        session.query(RoomSchedule).filter(RoomSchedule.specific_date == None).delete()
        
        for rid, day, start, end, subject in schedules:
            sch = RoomSchedule(
                room_id=rid,
                day_of_week=day,
                specific_date=None, # Weekly recurring
                start_time=start,
                end_time=end,
                subject_name=subject
            )
            session.add(sch)
        
        session.commit()
        print(f"Imported {len(schedules)} recurring schedule slots.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import_schedule()
