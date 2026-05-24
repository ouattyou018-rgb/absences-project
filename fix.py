import bcrypt
import pg8000

conn = pg8000.connect(host="localhost", port=5432, database="absences_db", user="postgres", password="MonMdp2024")
cur = conn.cursor()
cur.execute("DELETE FROM admin")
conn.commit()

comptes = [("Ouattara", "ouattyou018@gmail.com", "Aida2015"), ("Arzika Mohamed", "arzikamohamed@gmail.com", "Arzika123")]

for nom, email, mdp in comptes:
    hashed = bcrypt.hashpw(mdp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.execute("INSERT INTO admin (nom, email, mot_de_passe, actif) VALUES (%s, %s, %s, TRUE)", (nom, email, hashed))
    print("Cree : " + email)

conn.commit()
cur.close()
conn.close()
print("Termine!")
