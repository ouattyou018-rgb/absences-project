# -*- coding: utf-8 -*-
import anthropic
import json

client = anthropic.Anthropic(api_key="TA_CLE_API_ICI")

def analyser_absences(donnees):
    prompt = f"""
Tu es un expert en gestion scolaire. Analyse ces donnees d absenteisme et reponds UNIQUEMENT en JSON valide.

DONNEES :
- Total eleves : {donnees.get('total_eleves', 0)}
- Total absences : {donnees.get('total_absences', 0)}
- Moyenne par eleve : {donnees.get('taux_global', 0)}
- Justifiees : {donnees.get('justifiees', 0)}
- Non justifiees : {donnees.get('non_justifiees', 0)}
- Eleves a risque : {json.dumps(donnees.get('a_risque', []), ensure_ascii=False)}
- Top absents : {json.dumps(donnees.get('top_absents', []), ensure_ascii=False)}
- Par classe : {json.dumps(donnees.get('par_classe', []), ensure_ascii=False)}
- Par mois : {json.dumps(donnees.get('par_mois', []), ensure_ascii=False)}

Reponds avec ce JSON exact sans aucun texte avant ou apres :
{{"resume":"texte","niveau_alerte":"normal","predictions":[{{"eleve":"nom","classe":"classe","risque":"eleve","raison":"raison"}}],"anomalies":[{{"type":"type","description":"desc","severite":"moyenne"}}],"recommandations":[{{"priorite":"haute","action":"action","cible":"cible"}}],"analyse_motifs":{{"tendance":"tendance","jour_critique":"jour","classe_critique":"classe"}}}}
"""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    texte = message.content[0].text.strip()
    if "```" in texte:
        texte = texte.split("```")[1]
        if texte.startswith("json"):
            texte = texte[4:]
    return json.loads(texte.strip())

def generer_rapport(donnees):
    prompt = f"""
Tu es un expert en gestion scolaire. Genere un rapport hebdomadaire professionnel en francais
sur l absenteisme scolaire base sur ces donnees :
{json.dumps(donnees, ensure_ascii=False)}

Structure du rapport :
1. Titre avec date
2. Resume executif
3. Analyse par classe
4. Eleves necessitant attention
5. Tendances observees
6. Recommandations
7. Conclusion

Utilise des emojis. Maximum 500 mots.
"""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def chatbot(question, donnees):
    prompt = f"""
Tu es un assistant specialise dans la gestion des absences scolaires.
Donnees disponibles : {json.dumps(donnees, ensure_ascii=False)}
Question : {question}
Reponds en francais, de facon claire et concise. Maximum 150 mots.
"""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
