import sqlite3
from database import register_cadet

def seed_data():
    # 1. Clear existing data
    conn = sqlite3.connect("bullpen.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cadets")
    conn.commit()
    conn.close()

    test_cadets = []
    
    # SQUAD GENERATOR: 1st, 2nd, 3rd, 4th Squads
    squad_names = ["1st Squad", "2nd Squad", "3rd Squad", "4th Squad"]
    
    for squad in squad_names:
        for i in range(6):
            # Requirements: 1 per squad is Tier 2, 3 Duke (D), 3 NCCU (N)
            tier = 2 if i == 0 else 3
            school = "D" if i < 3 else "N"
            ms_level = (i % 3) + 1 # Cycles MS1, MS2, MS3
            
            name = f"Cadet {squad[:1]}{i+1}, {school}-{ms_level}"
            test_cadets.append((name, ms_level, school, squad, tier, "password123"))

    # MS4 GENERATOR: 6 Students, No Squad (Squad = "MS4")
    for i in range(6):
        school = "D" if i < 3 else "N"
        name = f"Staff_Cadet {i+1}, {school}-4"
        # 1 Admin (Tier 1), the rest Tier 3 or 2
        tier = 1 if i == 0 else 3
        test_cadets.append((name, 4, school, "MS4", tier, "admin123"))

    # 3. Execution
    print(f"Seeding {len(test_cadets)} cadets...")
    for c in test_cadets:
        register_cadet(*c)
    print("Seeding complete. Total: 30 Cadets.")

if __name__ == "__main__":
    seed_data()