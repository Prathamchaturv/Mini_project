import sqlite3
conn = sqlite3.connect('security.db')
cur = conn.cursor()
cur.execute('SELECT id, time, message, image, detections, model_type, confidence FROM alerts ORDER BY id DESC LIMIT 5')
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
