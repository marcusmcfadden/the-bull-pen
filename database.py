import sqlite3
import bcrypt

db_name = "bullpen.db"

def init_db():
    # Initializes the SQLite database and creates the cadets table.
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
     
    # Tiers: 1=Full Admin, 2=Limited Admin, 3=Standard User.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cadets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ms_level INTEGER,
            school TEXT,
            squad TEXT,
            tier INTEGER DEFAULT 3, 
            password_hash BLOB,
            status TEXT DEFAULT 'N'
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def register_cadet(name, ms_level, school, squad, tier, password):
    # Hashes the password and saves a new cadet to the database.
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO cadets (name, ms_level, school, squad, tier, password_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (name, ms_level, school, squad, tier, hashed)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error registering cadet: {e}")
        return False
    finally:
        conn.close()

def update_cadet(cadet_id, name, ms_level, school, squad, tier):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE cadets 
            SET name=?, ms_level=?, school=?, squad=?, tier=? 
            WHERE id=?
        ''', (name, ms_level, school, squad, tier, cadet_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating cadet: {e}")
        return False
    finally:
        conn.close()

def delete_cadet(cadet_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM cadets WHERE id=?", (cadet_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting cadet: {e}")
        return False
    finally:
        conn.close()

def get_filtered_cadets(search_query, schools, squads, ms_levels, direction="ASC"):
    import sqlite3
    conn = sqlite3.connect("bullpen.db")
    cursor = conn.cursor()
    
    # Base Query - Start with Name Search
    query = "SELECT id, name, ms_level, school, squad, tier FROM cadets WHERE name LIKE ?"
    params = [f'%{search_query}%']
    
    # Logic: Multi-Filter Checkboxes
    # If the list isn't empty, we add an "IN" clause to the SQL
    if schools:
        query += f" AND school IN ({','.join(['?'] * len(schools))})"
        params.extend(schools)
        
    if squads:
        query += f" AND squad IN ({','.join(['?'] * len(squads))})"
        params.extend(squads)
        
    if ms_levels:
        query += f" AND ms_level IN ({','.join(['?'] * len(ms_levels))})"
        params.extend(ms_levels)
        
    # Sorting
    query += f" ORDER BY name {direction}"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_attendance(cadet_id, day_col, status, is_late):
    conn = sqlite3.connect("cadets.db") # Use your actual db name
    cursor = conn.cursor()
    cursor.execute("""
         INSERT INTO attendance (cadet_id, day, status, is_late) 
         VALUES (?, ?, ?, ?)
         ON CONFLICT(cadet_id, day) DO UPDATE SET status=excluded.status, is_late=excluded.is_late
     """, (cadet_id, day_col, status, is_late))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()