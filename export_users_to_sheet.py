import sqlite3
import gspread
from google.oauth2.service_account import Credentials

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = '1KXLAOn0aJnlkKnLBRkBKCx-t_MrbLuX3tGvSQ_c9tro'

def export_users():
    try:
        # 1. ดึงข้อมูลผู้ใช้ทั้งหมดจากฐานข้อมูล
        conn = sqlite3.connect('music_room.db')
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name FROM users")
        users = cursor.fetchall()
        conn.close()

        if not users:
            print("ไม่พบข้อมูลสมาชิกในฐานข้อมูล")
            return

        print(f"พบสมาชิกในระบบทั้งหมด {len(users)} คน กำลังเชื่อมต่อ Google Sheets...")

        # 2. เชื่อมต่อ Google Sheets
        creds = Credentials.from_service_account_file("credentials.json", scopes=SHEETS_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("สมาชิก")

        # 3. ล้างข้อมูลเก่าทั้งหมดใน Sheet
        sheet.clear()

        # 4. เตรียมข้อมูลพร้อมหัวตาราง และลำดับที่
        headers = ['ลำดับ', 'รหัสนักศึกษา', 'รายชื่อ']
        rows_to_insert = [headers]
        
        for i, user in enumerate(users, 1):
            student_id, name = user
            rows_to_insert.append([str(i), str(student_id), str(name)])

        # 5. ส่งข้อมูลขึ้น Google Sheets รวดเดียว
        sheet.update(range_name='A1', values=rows_to_insert)
        
        print("ซิงค์ข้อมูลสมาชิกลง Google Sheets พร้อมลำดับเรียบร้อยแล้ว!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"เกิดข้อผิดพลาด: {e}")

if __name__ == '__main__':
    export_users()
