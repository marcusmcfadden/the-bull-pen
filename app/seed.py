import sqlite3
from database import register_cadet, create_auth_user, _conn

def reset_tables():
    conn = _conn(write=True)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM cadets")
    cursor.execute("DELETE FROM attendance_current")
    cursor.execute("DELETE FROM auth_users")

    cursor.execute("DELETE FROM sqlite_sequence WHERE name='cadets'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='auth_users'")

    conn.commit()
    conn.close()

def generate_unique_username(base_username, cursor):
    username = base_username
    counter = 1

    while True:
        cursor.execute(
            "SELECT 1 FROM auth_users WHERE username = ?",
            (username,)
        )
        if not cursor.fetchone():
            return username

        username = f"{base_username}{counter}"
        counter += 1

def gen_cadets():

    test_cadets = []
    
    squad_names = ["1st Squad", "2nd Squad", "3rd Squad", "4th Squad"]
    
    for squad in squad_names:
        for i in range(6):
            # Requirements: 1 per squad is Tier 2, 3 Duke (D), 3 NCCU (N)
            tier = 2 if i == 0 else 3
            school = "D" if i < 3 else "N"
            ms_level = (i % 4 ) + 1
            
            last = f"Cadet{squad[0]}{i+1}"
            first = f"{school}-MS{ms_level}"
            name = f"{last}, {first}"
            password = "password123"

            test_cadets.append((name, ms_level, school, squad, tier, password))

    # MS4: 6 Students, No Squad (Squad = "MS4")
    for i in range(6):
        school = "D" if i < 3 else "N"
        # 1 Admin (Tier 1), the rest Tier 3 or 2
        tier = 1 if i == 0 else 3

        last = f"StaffCadet{i+1}"
        first = f"{school}-MS4"
        name = f"{last}, {first}"
        password = "admin123"

        test_cadets.append((name, 4, school, "MS4", tier, "admin123"))

    return test_cadets

def login_credentials():
    conn = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.name, a.username
        FROM auth_users a
        JOIN cadets c ON a.id = c.id
        ORDER BY c.squad, c.name
    """)

    rows = cursor.fetchall()
    conn.close()

    lines = []
    lines.append("===== LOGINS =====\n")

    for name, username in rows:
        if "StaffCadet" in name:
            password = "admin123"
        else:
            password = "password123"

        print(f"{name}")
        print(f"  username: {username}")
        print(f"  password: {password}\n")

        lines.append(name)
        lines.append(f"  username: {username}")
        lines.append(f"  password: {password}")
        lines.append("")

    content = "\n".join(lines)

    with open("login.txt", "w") as f:
        f.write(content)

    print("Login credentials written to login.txt")

def seed_data():
    reset_tables()

    conn = _conn(write=True)
    cursor = conn.cursor()

    test_cadets = gen_cadets()

    print(f"Seeding {len(test_cadets)} cadets...")

    for name, ms, school, squad, tier, password in test_cadets:
        try:
            cadet_id = register_cadet(name, ms, school, squad, tier)

            base_username = (
                name.lower()
                .replace(" ", "")
                .replace(",", "")
                .replace("-", "")
            )

            username = generate_unique_username(base_username, cursor)

            create_auth_user(cadet_id, username, password)

        except Exception as e:
            print(f"Error seeding {name}: {e}")

    conn.commit()
    conn.close()

    print(f"Seeding complete. Total: {len(test_cadets)} cadets.")

    login_credentials()

if __name__ == "__main__":
    seed_data()