# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import db, bcrypt, ml

app = Flask(__name__)
app.secret_key = "absencetrack_secret_2024"
app.jinja_env.globals["enumerate"] = enumerate

COMPTES_AUTORISES = ["ouattyou018@gmail.com", "arzikamohamed@gmail.com"]

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_donnees_dashboard():
    par_classe = db.query("""
        SELECT c.nom_classe,
               COUNT(DISTINCT e.id_eleve) AS nb_eleves,
               COUNT(a.id_absence) AS total_absences,
               SUM(CASE WHEN a.justifiee THEN 1 ELSE 0 END) AS justifiees,
               SUM(CASE WHEN NOT a.justifiee THEN 1 ELSE 0 END) AS non_justifiees,
               ROUND(COUNT(a.id_absence)::NUMERIC / NULLIF(COUNT(DISTINCT e.id_eleve),0), 2) AS moy
        FROM classe c
        LEFT JOIN eleve e ON c.id_classe = e.id_classe
        LEFT JOIN absence a ON e.id_eleve = a.id_eleve
        GROUP BY c.id_classe, c.nom_classe ORDER BY moy DESC
    """)
    a_risque = db.query("""
        SELECT e.nom || ' ' || e.prenom AS eleve, c.nom_classe,
               TO_CHAR(a.date_absence, 'YYYY-MM') AS mois, COUNT(*) AS nb
        FROM absence a
        JOIN eleve e ON a.id_eleve = e.id_eleve
        JOIN classe c ON e.id_classe = c.id_classe
        GROUP BY e.id_eleve, e.nom, e.prenom, c.nom_classe,
                 TO_CHAR(a.date_absence, 'YYYY-MM')
        HAVING COUNT(*) > 3 ORDER BY nb DESC
    """)
    top_absents = db.query("""
        SELECT e.nom || ' ' || e.prenom AS eleve, c.nom_classe,
               COUNT(*) AS total,
               SUM(CASE WHEN a.justifiee THEN 1 ELSE 0 END) AS justifiees,
               SUM(CASE WHEN NOT a.justifiee THEN 1 ELSE 0 END) AS non_justifiees
        FROM absence a
        JOIN eleve e ON a.id_eleve = e.id_eleve
        JOIN classe c ON e.id_classe = c.id_classe
        GROUP BY e.id_eleve, e.nom, e.prenom, c.nom_classe
        ORDER BY total DESC LIMIT 5
    """)
    par_mois = db.query("""
        SELECT TO_CHAR(date_absence, 'YYYY-MM') AS mois, COUNT(*) AS nb,
               SUM(CASE WHEN justifiee THEN 1 ELSE 0 END) AS justifiees,
               SUM(CASE WHEN NOT justifiee THEN 1 ELSE 0 END) AS non_justifiees
        FROM absence GROUP BY TO_CHAR(date_absence, 'YYYY-MM') ORDER BY mois
    """)
    par_jour = db.query("""
        SELECT TRIM(TO_CHAR(date_absence, 'Day')) AS jour,
               EXTRACT(DOW FROM date_absence) AS num_jour, COUNT(*) AS nb
        FROM absence
        GROUP BY TRIM(TO_CHAR(date_absence, 'Day')), EXTRACT(DOW FROM date_absence)
        ORDER BY num_jour
    """)
    tendance = db.query("""
        SELECT TO_CHAR(DATE_TRUNC('week', date_absence), 'YYYY-MM-DD') AS semaine,
               COUNT(*) AS nb
        FROM absence GROUP BY DATE_TRUNC('week', date_absence) ORDER BY semaine
    """)
    justif = db.query("""
        SELECT SUM(CASE WHEN justifiee THEN 1 ELSE 0 END) AS justifiees,
               SUM(CASE WHEN NOT justifiee THEN 1 ELSE 0 END) AS non_justifiees
        FROM absence
    """, fetchall=False)
    total_stats = db.query("""
        SELECT COUNT(DISTINCT e.id_eleve) AS total_eleves,
               COUNT(a.id_absence) AS total_absences,
               ROUND(COUNT(a.id_absence)::NUMERIC / NULLIF(COUNT(DISTINCT e.id_eleve),0), 2) AS taux_global
        FROM eleve e LEFT JOIN absence a ON e.id_eleve = a.id_eleve
    """, fetchall=False)
    return {
        "par_classe":     [dict(r) for r in par_classe],
        "a_risque":       [dict(r) for r in a_risque],
        "top_absents":    [dict(r) for r in top_absents],
        "par_mois":       [dict(r) for r in par_mois],
        "par_jour":       [dict(r) for r in par_jour],
        "tendance":       [dict(r) for r in tendance],
        "justif":         dict(justif) if justif else {},
        "total_stats":    dict(total_stats) if total_stats else {},
        "total_eleves":   total_stats["total_eleves"] if total_stats else 0,
        "total_absences": total_stats["total_absences"] if total_stats else 0,
        "taux_global":    total_stats["taux_global"] if total_stats else 0,
        "justifiees":     justif["justifiees"] if justif else 0,
        "non_justifiees": justif["non_justifiees"] if justif else 0,
    }

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        mdp   = request.form.get("mot_de_passe", "")
        if email not in COMPTES_AUTORISES:
            flash("Acces refuse. Compte non autorise.", "danger")
            return render_template("login.html")
        admin = db.query("SELECT * FROM admin WHERE LOWER(email) = %s AND actif = TRUE", (email,), fetchall=False)
        if admin and bcrypt.checkpw(mdp.encode("utf-8"), admin["mot_de_passe"].encode("utf-8")):
            session["logged_in"]   = True
            session["admin_email"] = admin["email"]
            session["admin_nom"]   = admin["nom"]
            session["user_id"]     = admin["id_admin"]
            session["is_admin"]    = True
            flash("Bienvenue " + admin["nom"] + " !", "success")
            return redirect(url_for("index"))
        flash("Mot de passe incorrect.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/mot-de-passe-oublie", methods=["GET", "POST"])
def mdp_oublie():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if email not in COMPTES_AUTORISES:
            flash("Email non autorise.", "danger")
            return render_template("mdp_oublie.html")
        admin = db.query("SELECT * FROM admin WHERE LOWER(email) = %s", (email,), fetchall=False)
        if admin:
            return redirect(url_for("reinitialiser", email=email))
        flash("Aucun compte trouve.", "danger")
    return render_template("mdp_oublie.html")

@app.route("/reinitialiser/<email>", methods=["GET", "POST"])
def reinitialiser(email):
    admin = db.query("SELECT * FROM admin WHERE LOWER(email) = %s", (email.lower(),), fetchall=False)
    if not admin:
        return redirect(url_for("login"))
    if request.method == "POST":
        nouveau   = request.form.get("nouveau_mdp", "")
        confirmer = request.form.get("confirmer", "")
        if len(nouveau) < 6:
            flash("Minimum 6 caracteres.", "danger")
            return render_template("reinitialiser.html", email=email, nom=admin["nom"])
        if nouveau != confirmer:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template("reinitialiser.html", email=email, nom=admin["nom"])
        hashed = bcrypt.hashpw(nouveau.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        db.execute("UPDATE admin SET mot_de_passe = %s WHERE LOWER(email) = %s", (hashed, email.lower()))
        flash("Mot de passe modifie !", "success")
        return redirect(url_for("login"))
    return render_template("reinitialiser.html", email=email, nom=admin["nom"])

@app.route("/")
@login_required
def index():
    donnees   = get_donnees_dashboard()
    nb_risque = len(donnees["a_risque"])
    alertes   = []
    if nb_risque > 0:
        alertes.append({"type": "danger", "icon": "🚨", "message": str(nb_risque) + " eleve(s) ont depasse 3 absences ce mois."})
    justif = donnees.get("justif", {})
    if justif.get("non_justifiees") and justif.get("justifiees") and justif["non_justifiees"] > justif["justifiees"]:
        alertes.append({"type": "warning", "icon": "⚠️", "message": "Les absences non justifiees sont majoritaires."})
    return render_template("index.html", alertes=alertes, **donnees)

@app.route("/classes")
@login_required
def classes_liste():
    classes = db.query("SELECT * FROM classe ORDER BY niveau, nom_classe")
    return render_template("classes/liste.html", classes=classes)

@app.route("/classes/nouveau", methods=["GET", "POST"])
@login_required
def classe_nouveau():
    if request.method == "POST":
        db.execute("INSERT INTO classe (nom_classe, niveau, annee_scolaire) VALUES (%s, %s, %s)",
            (request.form["nom_classe"], request.form["niveau"], request.form.get("annee_scolaire", "2024-2025")))
        flash("Classe creee.", "success")
        return redirect(url_for("classes_liste"))
    return render_template("classes/form.html", classe=None)

@app.route("/classes/<int:id_classe>/modifier", methods=["GET", "POST"])
@login_required
def classe_modifier(id_classe):
    classe = db.query("SELECT * FROM classe WHERE id_classe = %s", (id_classe,), fetchall=False)
    if request.method == "POST":
        db.execute("UPDATE classe SET nom_classe=%s, niveau=%s, annee_scolaire=%s WHERE id_classe=%s",
            (request.form["nom_classe"], request.form["niveau"], request.form["annee_scolaire"], id_classe))
        flash("Classe mise a jour.", "success")
        return redirect(url_for("classes_liste"))
    return render_template("classes/form.html", classe=classe)

@app.route("/classes/<int:id_classe>/supprimer", methods=["POST"])
@login_required
def classe_supprimer(id_classe):
    db.execute("DELETE FROM classe WHERE id_classe = %s", (id_classe,))
    flash("Classe supprimee.", "warning")
    return redirect(url_for("classes_liste"))

@app.route("/eleves")
@login_required
def eleves_liste():
    filtre_classe = request.args.get("classe_id", "")
    filtre_date   = request.args.get("date_absence", "")
    if filtre_classe and filtre_date:
        eleves = db.query("""
            SELECT e.*, c.nom_classe, COUNT(a.id_absence) AS total_absences
            FROM eleve e JOIN classe c ON e.id_classe = c.id_classe
            LEFT JOIN absence a ON e.id_eleve = a.id_eleve
            WHERE e.id_classe = %s
            AND EXISTS (SELECT 1 FROM absence a2 WHERE a2.id_eleve = e.id_eleve AND a2.date_absence = %s)
            GROUP BY e.id_eleve, c.nom_classe ORDER BY e.nom, e.prenom
        """, (filtre_classe, filtre_date))
    elif filtre_classe:
        eleves = db.query("""
            SELECT e.*, c.nom_classe, COUNT(a.id_absence) AS total_absences
            FROM eleve e JOIN classe c ON e.id_classe = c.id_classe
            LEFT JOIN absence a ON e.id_eleve = a.id_eleve
            WHERE e.id_classe = %s
            GROUP BY e.id_eleve, c.nom_classe ORDER BY e.nom, e.prenom
        """, (filtre_classe,))
    elif filtre_date:
        eleves = db.query("""
            SELECT e.*, c.nom_classe, COUNT(a.id_absence) AS total_absences
            FROM eleve e JOIN classe c ON e.id_classe = c.id_classe
            LEFT JOIN absence a ON e.id_eleve = a.id_eleve
            WHERE EXISTS (SELECT 1 FROM absence a2 WHERE a2.id_eleve = e.id_eleve AND a2.date_absence = %s)
            GROUP BY e.id_eleve, c.nom_classe ORDER BY e.nom, e.prenom
        """, (filtre_date,))
    else:
        eleves = db.query("""
            SELECT e.*, c.nom_classe, COUNT(a.id_absence) AS total_absences
            FROM eleve e JOIN classe c ON e.id_classe = c.id_classe
            LEFT JOIN absence a ON e.id_eleve = a.id_eleve
            GROUP BY e.id_eleve, c.nom_classe ORDER BY e.nom, e.prenom
        """)
    classes = db.query("SELECT * FROM classe ORDER BY nom_classe")
    return render_template("eleves/liste.html", eleves=eleves, classes=classes,
                           filtre_classe=filtre_classe, filtre_date=filtre_date)

@app.route("/eleves/nouveau", methods=["GET", "POST"])
@login_required
def eleve_nouveau():
    classes = db.query("SELECT * FROM classe ORDER BY nom_classe")
    if request.method == "POST":
        db.execute("INSERT INTO eleve (nom, prenom, date_naissance, id_classe) VALUES (%s, %s, %s, %s)",
            (request.form["nom"], request.form["prenom"], request.form["date_naissance"] or None, request.form["id_classe"]))
        flash("Eleve ajoute.", "success")
        return redirect(url_for("eleves_liste"))
    return render_template("eleves/form.html", eleve=None, classes=classes)

@app.route("/eleves/<int:id_eleve>/modifier", methods=["GET", "POST"])
@login_required
def eleve_modifier(id_eleve):
    eleve   = db.query("SELECT * FROM eleve WHERE id_eleve = %s", (id_eleve,), fetchall=False)
    classes = db.query("SELECT * FROM classe ORDER BY nom_classe")
    if request.method == "POST":
        db.execute("UPDATE eleve SET nom=%s, prenom=%s, date_naissance=%s, id_classe=%s WHERE id_eleve=%s",
            (request.form["nom"], request.form["prenom"], request.form["date_naissance"] or None, request.form["id_classe"], id_eleve))
        flash("Eleve mis a jour.", "success")
        return redirect(url_for("eleves_liste"))
    return render_template("eleves/form.html", eleve=eleve, classes=classes)

@app.route("/eleves/<int:id_eleve>/supprimer", methods=["POST"])
@login_required
def eleve_supprimer(id_eleve):
    db.execute("DELETE FROM eleve WHERE id_eleve = %s", (id_eleve,))
    flash("Eleve supprime.", "warning")
    return redirect(url_for("eleves_liste"))

@app.route("/absences")
@login_required
def absences_liste():
    absences = db.query("""
        SELECT a.*, e.nom || ' ' || e.prenom AS eleve, c.nom_classe
        FROM absence a JOIN eleve e ON a.id_eleve = e.id_eleve
        JOIN classe c ON e.id_classe = c.id_classe
        ORDER BY a.date_absence DESC
    """)
    return render_template("absences/liste.html", absences=absences)

@app.route("/absences/nouveau", methods=["GET", "POST"])
@login_required
def absence_nouveau():
    classes = db.query("SELECT * FROM classe ORDER BY nom_classe")
    eleves  = db.query("SELECT e.id_eleve, e.nom, e.prenom, e.id_classe FROM eleve e ORDER BY e.nom, e.prenom")
    if request.method == "POST":
        db.execute("INSERT INTO absence (id_eleve, date_absence, motif, justifiee) VALUES (%s, %s, %s, %s)",
            (request.form["id_eleve"], request.form["date_absence"], request.form.get("motif") or None, "justifiee" in request.form))
        flash("Absence enregistree.", "success")
        return redirect(url_for("absences_liste"))
    return render_template("absences/form.html", absence=None, classes=classes, eleves=eleves)

@app.route("/absences/<int:id_absence>/modifier", methods=["GET", "POST"])
@login_required
def absence_modifier(id_absence):
    absence = db.query("SELECT * FROM absence WHERE id_absence = %s", (id_absence,), fetchall=False)
    classes = db.query("SELECT * FROM classe ORDER BY nom_classe")
    eleves  = db.query("SELECT e.id_eleve, e.nom, e.prenom, e.id_classe FROM eleve e ORDER BY e.nom, e.prenom")
    if absence:
        eleve_info = db.query("SELECT id_classe FROM eleve WHERE id_eleve = %s", (absence["id_eleve"],), fetchall=False)
        if eleve_info:
            absence = dict(absence)
            absence["classe_id"] = eleve_info["id_classe"]
    if request.method == "POST":
        db.execute("UPDATE absence SET id_eleve=%s, date_absence=%s, motif=%s, justifiee=%s WHERE id_absence=%s",
            (request.form["id_eleve"], request.form["date_absence"], request.form.get("motif") or None, "justifiee" in request.form, id_absence))
        flash("Absence mise a jour.", "success")
        return redirect(url_for("absences_liste"))
    return render_template("absences/form.html", absence=absence, classes=classes, eleves=eleves)

@app.route("/absences/<int:id_absence>/supprimer", methods=["POST"])
@login_required
def absence_supprimer(id_absence):
    db.execute("DELETE FROM absence WHERE id_absence = %s", (id_absence,))
    flash("Absence supprimee.", "warning")
    return redirect(url_for("absences_liste"))

@app.route("/admin")
@login_required
def admin_panel():
    admins = db.query("SELECT * FROM admin ORDER BY date_creation DESC")
    return render_template("admin.html", admins=admins)

if __name__ == "__main__":
    app.run(debug=True)