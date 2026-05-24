import bcrypt
import psycopg2

conn = psycopg2.connect(
    dbname="absences_db",
    user="postgres",
    password="Prepaesatic23",
    host="localhost",
    port="5432"
)

hashed = bcrypt.hashpw("Admin@2024".encode(), bcrypt.gensalt()).decode()

cur = conn.cursor()
cur.execute(
    "INSERT INTO admin (nom, email, mot_de_passe) VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING",
    ("Super Admin", "admin@absencetrack.com", hashed)
)
conn.commit()
conn.close()
print("Admin cree avec succes !")
