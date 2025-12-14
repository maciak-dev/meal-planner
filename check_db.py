import sqlite3

# <-- tu podaj nazwę pliku bazy z database.py -->
DB_FILE = "meal_etl.db"

def main():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("### STRUKTURA TABELI recipes ###")
    cursor.execute("PRAGMA table_info(recipes);")
    columns = cursor.fetchall()
    for col in columns:
        print(col)

    print("\n### WSZYSTKIE REKORDY ###")
    cursor.execute("SELECT * FROM recipes;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    conn.close()

if __name__ == "__main__":
    main()
