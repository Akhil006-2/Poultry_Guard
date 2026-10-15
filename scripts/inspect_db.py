import sqlite3

conn = sqlite3.connect(r'C:\Dev\12hr\PoultryGuard_Full\data\poultryguard.sqlite3')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables in poultryguard.sqlite3:", tables)
for t in tables:
    if t != 'sqlite_sequence':
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur.fetchone()[0]} rows")

print("\nFarms:")
cur.execute("SELECT id, name, location FROM farms LIMIT 5")
for r in cur.fetchall():
    print(" ", r)

print("\nFlocks:")
cur.execute("SELECT id, farm_id, name, bird_count FROM flocks LIMIT 5")
for r in cur.fetchall():
    print(" ", r)

print("\nJobs:")
cur.execute("SELECT id, original_name, status FROM jobs LIMIT 5")
for r in cur.fetchall():
    print(" ", r)
