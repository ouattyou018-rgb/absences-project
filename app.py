# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import db, bcrypt, ml

app = Flask(__name__)
app.secret_key = "absencetrack_secret_2024"
app.jinja_env.globals['enumerate'] = enumerate

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
        GROUP BY e.id_eleve, e.nom, e.prenom, c.nom_classe, TO_CHAR(a.date_absence, 'YYYY-MM')
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
        flash("Mot de passe modifie ! Connectez-vous.", "success")
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
    eleves = db.query("""
        SELECT e.*, c.nom_classe, COUNT(a.id_absence) AS total_absences
        FROM eleve e JOIN classe c ON e.id_classe = c.id_classe
        LEFT JOIN absence a ON e.id_eleve = a.id_eleve
        GROUP BY e.id_eleve, c.nom_classe ORDER BY e.nom, e.prenom
    """)
    return render_template("eleves/liste.html", eleves=eleves)

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
    eleves = db.query("""
        SELECT e.id_eleve, e.nom || ' ' || e.prenom || ' (' || c.nom_classe || ')' AS label
        FROM eleve e JOIN classe c ON e.id_classe = c.id_classe ORDER BY e.nom
    """)
    if request.method == "POST":
        db.execute("INSERT INTO absence (id_eleve, date_absence, motif, justifiee) VALUES (%s, %s, %s, %s)",
            (request.form["id_eleve"], request.form["date_absence"], request.form.get("motif") or None, "justifiee" in request.form))
        flash("Absence enregistree.", "success")
        return redirect(url_for("absences_liste"))
    return render_template("absences/form.html", absence=None, eleves=eleves)

@app.route("/absences/<int:id_absence>/modifier", methods=["GET", "POST"])
@login_required
def absence_modifier(id_absence):
    absence = db.query("SELECT * FROM absence WHERE id_absence = %s", (id_absence,), fetchall=False)
    eleves  = db.query("""
        SELECT e.id_eleve, e.nom || ' ' || e.prenom || ' (' || c.nom_classe || ')' AS label
        FROM eleve e JOIN classe c ON e.id_classe = c.id_classe ORDER BY e.nom
    """)
    if request.method == "POST":
        db.execute("UPDATE absence SET id_eleve=%s, date_absence=%s, motif=%s, justifiee=%s WHERE id_absence=%s",
            (request.form["id_eleve"], request.form["date_absence"], request.form.get("motif") or None, "justifiee" in request.form, id_absence))
        flash("Absence mise a jour.", "success")
        return redirect(url_for("absences_liste"))
    return render_template("absences/form.html", absence=absence, eleves=eleves)

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

# ── CHATBOT ──
@app.route("/predictions")
@login_required
def predictions_page():
    return render_template("predictions.html")

@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    question = request.json.get("question", "").strip().lower()
    donnees  = get_donnees_dashboard()
    reponse  = repondre_chatbot(question, donnees)
    return jsonify({"reponse": reponse})

@app.route("/api/predictions", methods=["GET"])
@login_required
def api_predictions():
    donnees      = get_donnees_dashboard()
    predictions  = ml.predire_absences(donnees["par_mois"], donnees["par_classe"])
    return jsonify({"predictions": predictions})

def repondre_chatbot(question, d):
    total_eleves   = d.get("total_eleves", 0)
    total_absences = d.get("total_absences", 0)
    taux           = d.get("taux_global", 0)
    justif         = d.get("justif", {})
    justifiees     = justif.get("justifiees", 0) or 0
    non_justifiees = justif.get("non_justifiees", 0) or 0
    par_classe     = d.get("par_classe", [])
    a_risque       = d.get("a_risque", [])
    top_absents    = d.get("top_absents", [])
    par_jour       = d.get("par_jour", [])

    # Total absences
    if any(m in question for m in ["total absence", "combien absence", "nombre absence"]):
        return f"Il y a au total {total_absences} absences enregistrees cette annee scolaire, dont {justifiees} justifiees et {non_justifiees} non justifiees."

    # Total eleves
    if any(m in question for m in ["total eleve", "combien eleve", "nombre eleve"]):
        return f"L etablissement compte {total_eleves} eleves au total."

    # Taux moyen
    if any(m in question for m in ["taux", "moyenne", "moy"]):
        return f"Le taux moyen d absenteisme est de {taux} absences par eleve. " + (
            "C est un taux eleve qui necessite une attention particuliere." if float(str(taux)) > 3
            else "C est un taux acceptable."
        )

    # Justifiees vs non justifiees
    if any(m in question for m in ["justif", "non justif"]):
        total = (justifiees or 0) + (non_justifiees or 0)
        pct_j  = round((justifiees / total * 100), 1) if total > 0 else 0
        pct_nj = round((non_justifiees / total * 100), 1) if total > 0 else 0
        return f"Sur {total} absences : {justifiees} sont justifiees ({pct_j}%) et {non_justifiees} sont non justifiees ({pct_nj}%)."

    # Eleves a risque
    if any(m in question for m in ["risque", "alerte", "danger"]):
        if not a_risque:
            return "Aucun eleve n est actuellement en situation de risque (plus de 3 absences par mois)."
        noms = ", ".join([r["eleve"] for r in a_risque[:5]])
        return f"{len(a_risque)} eleve(s) sont a risque (plus de 3 absences/mois) : {noms}."

    # Par classe
    if any(m in question for m in ["classe", "3eme", "terminale", "seconde"]):
        if not par_classe:
            return "Aucune donnee de classe disponible."
        rep = "Voici l absenteisme par classe :\n"
        for c in par_classe:
            rep += f"- {c['nom_classe']} : {c['total_absences']} absences, moyenne {c['moy']} par eleve\n"
        return rep.strip()

    # Classe la plus problematique
    if any(m in question for m in ["plus problematique", "pire", "plus d absence", "plus absent"]):
        if par_classe:
            pire = par_classe[0]
            return f"La classe la plus problematique est {pire['nom_classe']} avec {pire['total_absences']} absences et une moyenne de {pire['moy']} par eleve."
        return "Aucune donnee disponible."

    # Top absents
    if any(m in question for m in ["top", "plus absent", "classement", "eleve absent"]):
        if not top_absents:
            return "Aucune donnee sur les eleves absents."
        rep = "Top 5 des eleves les plus absents :\n"
        for i, e in enumerate(top_absents, 1):
            rep += f"{i}. {e['eleve']} ({e['nom_classe']}) : {e['total']} absences\n"
        return rep.strip()

    # Jour critique
    if any(m in question for m in ["jour", "lundi", "mardi", "mercredi", "jeudi", "vendredi"]):
        if par_jour:
            jour_max = max(par_jour, key=lambda x: x["nb"])
            return f"Le jour avec le plus d absences est le {jour_max['jour'].strip()} avec {jour_max['nb']} absences enregistrees."
        return "Aucune donnee par jour disponible."

    # Predictions
    if any(m in question for m in ["predict", "futur", "prochaine", "semaine prochaine", "prevision"]):
        predictions = ml.predire_absences(d.get("par_mois", []), par_classe)
        if not predictions:
            return "Impossible de faire des predictions avec les donnees actuelles."
        rep = "Predictions pour les prochaines semaines :\n"
        for p in predictions[:3]:
            rep += f"- {p['classe']} : tendance {p['tendance']}, {p['recommandation']}\n"
        return rep.strip()

    # Resume global
    if any(m in question for m in ["resume", "situation", "bilan", "general"]):
        classe_critique = par_classe[0]["nom_classe"] if par_classe else "N/A"
        return (
            f"Bilan general : {total_eleves} eleves, {total_absences} absences "
            f"(moy. {taux}/eleve). {len(a_risque)} eleve(s) a risque. "
            f"Classe la plus touchee : {classe_critique}. "
            f"Absences non justifiees : {non_justifiees} sur {(justifiees or 0)+(non_justifiees or 0)}."
        )

    # Aide
    return (
        "Je peux repondre a vos questions sur :\n"
        "- Le total des absences et des eleves\n"
        "- Le taux moyen d absenteisme\n"
        "- Les absences justifiees vs non justifiees\n"
        "- Les eleves a risque\n"
        "- L absenteisme par classe\n"
        "- Le jour le plus critique\n"
        "- Le classement des eleves les plus absents\n"
        "- Les predictions pour les semaines a venir\n"
        "Posez votre question !"
    )

if __name__ == "__main__":
    app.run(debug=True)

