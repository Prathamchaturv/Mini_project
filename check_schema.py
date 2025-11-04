import sqlite3
conn = sqlite3.connect('security.db')
cur = conn.cursor()
print('Columns:')
for col in cur.execute("PRAGMA table_info(alerts)"):
    print(col)

print('\nLast 5 rows (raw):')
try:
    for r in cur.execute('SELECT * FROM alerts ORDER BY id DESC LIMIT 5'):
        print(r)
except Exception as e:
    print('Error selecting rows:', e)
conn.close()
