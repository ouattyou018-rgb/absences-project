import numpy as np
from datetime import datetime, timedelta

def predire_absences(par_mois, par_classe):
    predictions = []
    aujourd_hui = datetime.today()
    n_mois = len(par_mois)

    for classe in par_classe:
        nom_classe  = classe["nom_classe"]
        nb_eleves   = classe["nb_eleves"] or 1
        moy         = float(classe["moy"] or 0)
        total       = float(classe["total_absences"] or 0)

        # Base de prediction : moyenne mensuelle de cette classe
        if n_mois > 0:
            moy_mensuelle = total / n_mois
        else:
            moy_mensuelle = moy

        # Calcul de la tendance avec regression lineaire si assez de donnees
        if n_mois >= 3:
            y = np.array([float(m["nb"] or 0) for m in par_mois])
            x = np.arange(n_mois)
            coeffs   = np.polyfit(x, y, 1)
            pente    = coeffs[0]
            # Ratio de la classe par rapport au total
            total_global = sum(float(c["total_absences"] or 0) for c in par_classe)
            ratio = total / total_global if total_global > 0 else 1 / len(par_classe)
            pente_classe = pente * ratio
        else:
            pente_classe = 0
            ratio = total / max(sum(float(c["total_absences"] or 0) for c in par_classe), 1)

        # Tendance globale
        if pente_classe > 0.3:
            tendance = "hausse"
        elif pente_classe < -0.3:
            tendance = "baisse"
        else:
            tendance = "stable"

        # Predictions pour 4 semaines
        # On convertit la moyenne mensuelle en hebdomadaire (divise par 4)
        base_hebdo = max(1, round(moy_mensuelle / 4)) if moy_mensuelle > 0 else max(1, round(moy * nb_eleves / 4))

        semaines_pred = []
        for i in range(1, 5):
            date_sem = aujourd_hui + timedelta(weeks=i)
            # Valeur predite avec tendance
            valeur = max(1, round(base_hebdo + pente_classe * i * ratio))

            if valeur > 6:
                niveau = "critique"
            elif valeur > 3:
                niveau = "attention"
            else:
                niveau = "normal"

            semaines_pred.append({
                "semaine": "Semaine " + str(i),
                "date":    date_sem.strftime("%d/%m/%Y"),
                "valeur":  valeur,
                "niveau":  niveau
            })

        # Recommandation
        max_val = max(s["valeur"] for s in semaines_pred)
        if max_val > 6 or moy > 5:
            reco = "Intervention urgente requise — contacter les familles"
        elif max_val > 3 or moy > 3:
            reco = "Surveillance renforcee recommandee"
        else:
            reco = "Situation normale — continuer le suivi regulier"

        predictions.append({
            "classe":       nom_classe,
            "nb_eleves":    nb_eleves,
            "moy_actuelle": moy,
            "tendance":     tendance,
            "predictions":  semaines_pred,
            "recommandation": reco
        })

    return sorted(predictions, key=lambda x: x["moy_actuelle"], reverse=True)
