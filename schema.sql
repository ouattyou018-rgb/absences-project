DROP TABLE IF EXISTS absence;
DROP TABLE IF EXISTS eleve;
DROP TABLE IF EXISTS classe;

CREATE TABLE classe (
    id_classe      SERIAL PRIMARY KEY,
    nom_classe     VARCHAR(50)  NOT NULL,
    niveau         VARCHAR(20)  NOT NULL,
    annee_scolaire VARCHAR(9)   NOT NULL DEFAULT '2024-2025'
);

CREATE TABLE eleve (
    id_eleve       SERIAL PRIMARY KEY,
    nom            VARCHAR(100) NOT NULL,
    prenom         VARCHAR(100) NOT NULL,
    date_naissance DATE,
    id_classe      INT NOT NULL REFERENCES classe(id_classe) ON DELETE CASCADE
);

CREATE TABLE absence (
    id_absence    SERIAL PRIMARY KEY,
    id_eleve      INT  NOT NULL REFERENCES eleve(id_eleve) ON DELETE CASCADE,
    date_absence  DATE NOT NULL DEFAULT CURRENT_DATE,
    motif         VARCHAR(200),
    justifiee     BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO classe (nom_classe, niveau) VALUES
    ('3eme A',      'College'),
    ('3eme B',      'College'),
    ('Terminale S', 'Lycee'),
    ('Seconde 2',   'Lycee');

INSERT INTO eleve (nom, prenom, date_naissance, id_classe) VALUES
    ('Kone',      'Aminata',  '2009-03-15', 1),
    ('Traore',    'Ibrahim',  '2009-07-22', 1),
    ('Coulibaly', 'Fatou',    '2008-11-05', 1),
    ('Diallo',    'Moussa',   '2009-01-30', 2),
    ('Bamba',     'Awa',      '2008-09-12', 2),
    ('Ouattara',  'Youssouf', '2007-04-18', 3),
    ('Toure',     'Mariame',  '2007-06-25', 3),
    ('Konate',    'Seydou',   '2008-02-14', 4);

INSERT INTO absence (id_eleve, date_absence, motif, justifiee) VALUES
    (1, '2024-10-01', 'Maladie', TRUE),
    (1, '2024-10-08', NULL,      FALSE),
    (1, '2024-10-15', NULL,      FALSE),
    (1, '2024-10-22', 'Fievre',  TRUE),
    (2, '2024-10-03', NULL,      FALSE),
    (2, '2024-10-10', NULL,      FALSE),
    (3, '2024-10-05', 'Deces',   TRUE),
    (4, '2024-10-01', NULL,      FALSE),
    (4, '2024-10-08', NULL,      FALSE),
    (4, '2024-10-09', NULL,      FALSE),
    (4, '2024-10-16', NULL,      FALSE),
    (5, '2024-10-07', 'Maladie', TRUE),
    (6, '2024-10-02', NULL,      FALSE),
    (7, '2024-10-11', NULL,      FALSE),
    (1, '2024-11-04', NULL,      FALSE),
    (2, '2024-11-05', 'Maladie', TRUE),
    (4, '2024-11-06', NULL,      FALSE),
    (4, '2024-11-07', NULL,      FALSE),
    (4, '2024-11-12', NULL,      FALSE),
    (4, '2024-11-13', NULL,      FALSE);