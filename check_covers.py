import sqlite3
c = sqlite3.connect('bibliotheque.db')
print("=== Nombre de livres ===")
print(c.execute('SELECT COUNT(*) FROM ressources').fetchone())
print("\n=== Exemples couvertures ===")
rows = c.execute('SELECT titre, couverture FROM ressources WHERE couverture IS NOT NULL LIMIT 10').fetchall()
for r in rows:
    print(r)
print("\n=== Couvertures NULL ===")
print(c.execute('SELECT COUNT(*) FROM ressources WHERE couverture IS NULL').fetchone())
