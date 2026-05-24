-- ============================================================
-- Projet 1 : Tableau de bord des absences scolaires
-- Base de données PostgreSQL
-- ============================================================

DROP TABLE IF EXISTS absence CASCADE;
DROP TABLE IF EXISTS eleve CASCADE;
DROP TABLE IF EXISTS classe CASCADE;

-- TABLE : classe
CREATE TABLE classe (
    id_classe      SERIAL PRIMARY KEY,
    nom_classe     VARCHAR(50)  NOT NULL,
    niveau         VARCHAR(20)  NOT NULL,
    annee_scolaire VARCHAR(9)   NOT NULL DEFAULT '2024-2025'
);

-- TABLE : eleve
CREATE TABLE eleve (
    id_eleve       SERIAL PRIMARY KEY,
    nom            VARCHAR(100) NOT NULL,
    prenom         VARCHAR(100) NOT NULL,
    date_naissance DATE,
    id_classe      INT NOT NULL REFERENCES classe(id_classe) ON DELETE CASCADE
);

-- TABLE : absence
CREATE TABLE absence (
    id_absence    SERIAL PRIMARY KEY,
    id_eleve      INT  NOT NULL REFERENCES eleve(id_eleve) ON DELETE CASCADE,
    date_absence  DATE NOT NULL DEFAULT CURRENT_DATE,
    motif         VARCHAR(200),
    justifiee     BOOLEAN NOT NULL DEFAULT FALSE
);

-- INDEX
CREATE INDEX idx_absence_eleve ON absence(id_eleve);
CREATE INDEX idx_absence_date  ON absence(date_absence);
CREATE INDEX idx_eleve_classe  ON eleve(id_classe);

-- ============================================================
-- DONNÉES DE TEST
-- ============================================================
INSERT INTO classe (nom_classe, niveau) VALUES
    ('3ème A',      'Collège'),
    ('3ème B',      'Collège'),
    ('Terminale S', 'Lycée'),
    ('Seconde 2',   'Lycée');

INSERT INTO eleve (nom, prenom, date_naissance, id_classe) VALUES
    ('Koné',      'Aminata',  '2009-03-15', 1),
    ('Traoré',    'Ibrahim',  '2009-07-22', 1),
    ('Coulibaly', 'Fatou',    '2008-11-05', 1),
    ('Diallo',    'Moussa',   '2009-01-30', 2),
    ('Bamba',     'Awa',      '2008-09-12', 2),
    ('Ouattara',  'Youssouf', '2007-04-18', 3),
    ('Touré',     'Mariame',  '2007-06-25', 3),
    ('Konaté',    'Seydou',   '2008-02-14', 4);

INSERT INTO absence (id_eleve, date_absence, motif, justifiee) VALUES
    (1, '2024-10-01', 'Maladie',       TRUE),
    (1, '2024-10-08', NULL,            FALSE),
    (1, '2024-10-15', NULL,            FALSE),
    (1, '2024-10-22', 'Fièvre',        TRUE),
    (2, '2024-10-03', NULL,            FALSE),
    (2, '2024-10-10', NULL,            FALSE),
    (3, '2024-10-05', 'Décès famille', TRUE),
    (4, '2024-10-01', NULL,            FALSE),
    (4, '2024-10-08', NULL,            FALSE),
    (4, '2024-10-09', NULL,            FALSE),
    (4, '2024-10-16', NULL,            FALSE),
    (5, '2024-10-07', 'Maladie',       TRUE),
    (6, '2024-10-02', NULL,            FALSE),
    (7, '2024-10-11', NULL,            FALSE),
    (1, '2024-11-04', NULL,            FALSE),
    (2, '2024-11-05', 'Maladie',       TRUE),
    (4, '2024-11-06', NULL,            FALSE),
    (4, '2024-11-07', NULL,            FALSE),
    (4, '2024-11-12', NULL,            FALSE),
    (4, '2024-11-13', NULL,            FALSE);

-- ============================================================
-- REQUÊTES ANALYTIQUES
-- ============================================================

-- 1. Absences totales par élève
SELECT
    e.nom || ' ' || e.prenom                          AS eleve,
    c.nom_classe,
    COUNT(a.id_absence)                               AS total_absences,
    SUM(CASE WHEN a.justifiee     THEN 1 ELSE 0 END) AS justifiees,
    SUM(CASE WHEN NOT a.justifiee THEN 1 ELSE 0 END) AS non_justifiees
FROM eleve e
JOIN classe c ON e.id_classe = c.id_classe
LEFT JOIN absence a ON e.id_eleve = a.id_eleve
GROUP BY e.id_eleve, e.nom, e.prenom, c.nom_classe
ORDER BY total_absences DESC;

-- 2. Élèves à risque (> 3 absences dans un même mois)
SELECT
    e.nom || ' ' || e.prenom          AS eleve,
    c.nom_classe,
    TO_CHAR(a.date_absence, 'YYYY-MM') AS mois,
    COUNT(*)                           AS absences_ce_mois
FROM absence a
JOIN eleve e ON a.id_eleve = e.id_eleve
JOIN classe c ON e.id_classe = c.id_classe
GROUP BY e.id_eleve, e.nom, e.prenom, c.nom_classe,
         TO_CHAR(a.date_absence, 'YYYY-MM')
HAVING COUNT(*) > 3
ORDER BY absences_ce_mois DESC;

-- 3. Taux d'absentéisme par classe
SELECT
    c.nom_classe,
    c.niveau,
    COUNT(DISTINCT e.id_eleve)                             AS nb_eleves,
    COUNT(a.id_absence)                                    AS total_absences,
    ROUND(COUNT(a.id_absence)::NUMERIC /
          NULLIF(COUNT(DISTINCT e.id_eleve), 0), 2)       AS moy_par_eleve
FROM classe c
LEFT JOIN eleve e   ON c.id_classe = e.id_classe
LEFT JOIN absence a ON e.id_eleve  = a.id_eleve
GROUP BY c.id_classe, c.nom_classe, c.niveau
ORDER BY moy_par_eleve DESC;

-- 4. Tendance hebdomadaire
SELECT
    DATE_TRUNC('week', date_absence) AS semaine,
    COUNT(*)                          AS nb_absences
FROM absence
GROUP BY DATE_TRUNC('week', date_absence)
ORDER BY semaine;

-- 5. Récapitulatif mensuel par classe
SELECT
    c.nom_classe,
    TO_CHAR(a.date_absence, 'YYYY-MM') AS mois,
    COUNT(a.id_absence)                AS nb_absences
FROM absence a
JOIN eleve e ON a.id_eleve = e.id_eleve
JOIN classe c ON e.id_classe = c.id_classe
GROUP BY c.nom_classe, TO_CHAR(a.date_absence, 'YYYY-MM')
ORDER BY mois, nb_absences DESC;