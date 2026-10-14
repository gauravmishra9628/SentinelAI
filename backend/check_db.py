import sqlite3
conn = sqlite3.connect('sentinelai.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    print(f'--- {t[0]} ---')
    cursor.execute(f'PRAGMA table_info({t[0]})')
    for col in cursor.fetchall():
        print(f'  {col}')
    cursor.execute(f'SELECT COUNT(*) FROM {t[0]}')
    print(f'  Count: {cursor.fetchone()[0]}')
conn.close()