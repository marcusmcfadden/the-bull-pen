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

        test_cadets.append((
            f"Leader {squad}",
            3,
            "D",
            squad,
            2,
            "password123"
        ))

        for i in range(1, 6):
            school = "D" if i <= 3 else "N"
            ms_level = (i % 3) + 1

            test_cadets.append((
                f"Cadet {squad} {i}",
                ms_level,
                school,
                squad,
                3,
                "password123"
            ))

    test_cadets.append((
        "Superadmin MS4",
        4,
        "D",
        "MS4",
        0,
        "admin123"
    ))

    test_cadets.append((
        "Admin MS4",
        4,
        "D",
        "MS4",
        1,
        "admin123"
    ))

    for i in range(1, 5):
        school = "D" if i <= 2 else "N"

        test_cadets.append((
            f"Cadet MS4 {i}",
            4,
            school,
            "MS4",
            3,
            "password123"
        ))

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
        if "Admin" in name or "Superadmin" in name:
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

    with open("seed.txt", "w") as f:
        f.write(content)

    print("Login credentials written to seed.txt")

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