from app.db import get_db
c = get_db()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Todas las tablas:")
for t in tables:
    print(" ", t[0])
mant = [t[0] for t in tables if 'mantenimiento' in t[0].lower()]
print("\nTablas de mantenimiento:", mant)
