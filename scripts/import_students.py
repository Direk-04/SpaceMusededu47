import sys
import os

# Add parent directory to path so we can import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def import_ids(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return
        
    with open(filename, 'r') as f:
        ids = [line.strip() for line in f.readlines() if line.strip()]
        
    with open('music_students.txt', 'w') as f:
        f.write('\n'.join(ids))
        
    print(f"Imported {len(ids)} student IDs to music_students.txt")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_students.py <ids_file.txt>")
    else:
        import_ids(sys.argv[1])
