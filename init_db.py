#!/usr/bin/env python3
"""
Création du schéma SQLite et migration depuis bibliotheque.json
Base : bibliotheque.db
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_FILE   = Path(__file__).parent / "bibliotheque.db"
JSON_FILE = Path(__file__).parent / "bibliotheque.json"

# ─── SCHÉMA ───────────────────────────────────────────────────────────────────
SCHEMA = """
-- Types de ressources
CREATE TABLE IF NOT EXISTS types (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle TEXT NOT NULL UNIQUE
);

-- Statuts
CREATE TABLE IF NOT EXISTS statuts (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle TEXT NOT NULL UNIQUE
);

-- Table principale
CREATE TABLE IF NOT EXISTS ressources (
    id               TEXT PRIMARY KEY,
    type_id          INTEGER REFERENCES types(id),
    titre            TEXT NOT NULL,
    serie            TEXT,
    isbn             TEXT,
    date_publication TEXT,
    editeur          TEXT,
    pages            TEXT,
    langue           TEXT,
    localisation     TEXT,
    statut_id        INTEGER REFERENCES statuts(id),
    fichier          TEXT,
    narrateur        TEXT,
    duree            TEXT,
    plateforme       TEXT,
    format           TEXT,
    lu               TEXT,
    commentaire      TEXT,
    couverture       TEXT,
    lien_amazon      TEXT,
    lien_fnac        TEXT,
    date_ajout       TEXT,
    source           TEXT
);

-- Auteurs
CREATE TABLE IF NOT EXISTS auteurs (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
);

-- Relation ressources <-> auteurs (N-N)
CREATE TABLE IF NOT EXISTS ressource_auteurs (
    ressource_id TEXT REFERENCES ressources(id) ON DELETE CASCADE,
    auteur_id    INTEGER REFERENCES auteurs(id) ON DELETE CASCADE,
    PRIMARY KEY (ressource_id, auteur_id)
);

-- Tags
CREATE TABLE IF NOT EXISTS tags (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle TEXT NOT NULL UNIQUE
);

-- Relation ressources <-> tags (N-N)
CREATE TABLE IF NOT EXISTS ressource_tags (
    ressource_id TEXT REFERENCES ressources(id) ON DELETE CASCADE,
    tag_id       INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (ressource_id, tag_id)
);

-- Index sur les colonnes de recherche fréquentes
CREATE INDEX IF NOT EXISTS idx_ressources_titre    ON ressources(titre);
CREATE INDEX IF NOT EXISTS idx_ressources_isbn     ON ressources(isbn);
CREATE INDEX IF NOT EXISTS idx_ressources_type     ON ressources(type_id);
CREATE INDEX IF NOT EXISTS idx_ressources_statut   ON ressources(statut_id);
CREATE INDEX IF NOT EXISTS idx_auteurs_nom         ON auteurs(nom);
CREATE INDEX IF NOT EXISTS idx_tags_libelle        ON tags(libelle);

-- Recherche fulltext FTS5
CREATE VIRTUAL TABLE IF NOT EXISTS ressources_fts USING fts5(
    id UNINDEXED,
    titre,
    auteurs,
    tags,
    commentaire
);
"""

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def get_or_create(cur, table, col, val):
    """Retourne l'id d'une ligne, la crée si elle n'existe pas."""
    cur.execute(f"SELECT id FROM {table} WHERE {col} = ?", (val,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table} ({col}) VALUES (?)", (val,))
    return cur.lastrowid

# ─── MIGRATION JSON → SQLite ──────────────────────────────────────────────────
def migrer(con):
    cur = con.cursor()

    print(f"📂 Lecture de {JSON_FILE}...")
    with open(JSON_FILE, encoding="utf-8") as f:
        ressources = json.load(f)

    ok = 0
    for r in ressources:
        # Résoudre type et statut
        type_id   = get_or_create(cur, "types",   "libelle", r.get("type",   "livre_papier"))
        statut_id = get_or_create(cur, "statuts",  "libelle", r.get("statut", "possédé"))

        # Insérer la ressource (INSERT OR IGNORE pour idempotence)
        cur.execute("""
            INSERT OR IGNORE INTO ressources
            (id, type_id, titre, serie, isbn, date_publication, editeur,
             pages, langue, localisation, statut_id, fichier, narrateur,
             duree, plateforme, format, lu, commentaire, couverture,
             lien_amazon, lien_fnac, date_ajout, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r["id"],
            type_id,
            r.get("titre"),
            r.get("serie"),
            r.get("isbn"),
            r.get("date_publication"),
            r.get("editeur"),
            r.get("pages"),
            r.get("langue"),
            r.get("localisation"),
            statut_id,
            r.get("fichier"),
            r.get("narrateur"),
            r.get("duree"),
            r.get("plateforme"),
            r.get("format"),
            r.get("lu"),
            r.get("commentaire"),
            r.get("couverture"),
            r.get("lien_amazon"),
            r.get("lien_fnac"),
            r.get("date_ajout", datetime.today().strftime("%Y-%m-%d")),
            r.get("source"),
        ))

        # Auteurs
        for nom in (r.get("auteurs") or []):
            if nom:
                auteur_id = get_or_create(cur, "auteurs", "nom", nom)
                cur.execute("INSERT OR IGNORE INTO ressource_auteurs VALUES (?,?)", (r["id"], auteur_id))

        # Tags
        for tag in (r.get("tags") or []):
            if tag:
                tag_id = get_or_create(cur, "tags", "libelle", tag)
                cur.execute("INSERT OR IGNORE INTO ressource_tags VALUES (?,?)", (r["id"], tag_id))

        ok += 1

    # Alimenter la table FTS5
    print("🔍 Construction de l'index fulltext FTS5...")
    cur.execute("DELETE FROM ressources_fts")
    cur.execute("""
        INSERT INTO ressources_fts (id, titre, auteurs, tags, commentaire)
        SELECT
            r.id,
            r.titre,
            COALESCE((
                SELECT GROUP_CONCAT(a.nom, ' ')
                FROM ressource_auteurs ra
                JOIN auteurs a ON a.id = ra.auteur_id
                WHERE ra.ressource_id = r.id
            ), ''),
            COALESCE((
                SELECT GROUP_CONCAT(t.libelle, ' ')
                FROM ressource_tags rt
                JOIN tags t ON t.id = rt.tag_id
                WHERE rt.ressource_id = r.id
            ), ''),
            COALESCE(r.commentaire, '')
        FROM ressources r
    """)

    con.commit()
    print(f"✅ {ok} ressource(s) migrées")
    return ok


# ─── STATS ────────────────────────────────────────────────────────────────────
def stats(con):
    cur = con.cursor()
    print("\n📊 Répartition par type :")
    for row in cur.execute("""
        SELECT t.libelle, COUNT(*) as n
        FROM ressources r JOIN types t ON t.id = r.type_id
        GROUP BY t.libelle ORDER BY n DESC
    """):
        print(f"   {row[0]:<20} {row[1]}")

    print("\n📊 Répartition par statut :")
    for row in cur.execute("""
        SELECT s.libelle, COUNT(*) as n
        FROM ressources r JOIN statuts s ON s.id = r.statut_id
        GROUP BY s.libelle ORDER BY n DESC
    """):
        print(f"   {row[0]:<20} {row[1]}")

    print("\n🏷  Top 10 tags :")
    for row in cur.execute("""
        SELECT t.libelle, COUNT(*) as n
        FROM ressource_tags rt JOIN tags t ON t.id = rt.tag_id
        GROUP BY t.libelle ORDER BY n DESC LIMIT 10
    """):
        print(f"   {row[0]:<20} {row[1]}")

    print("\n✍️  Top 10 auteurs :")
    for row in cur.execute("""
        SELECT a.nom, COUNT(*) as n
        FROM ressource_auteurs ra JOIN auteurs a ON a.id = ra.auteur_id
        GROUP BY a.nom ORDER BY n DESC LIMIT 10
    """):
        print(f"   {row[0]:<30} {row[1]}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🗄  Base de données : {DB_FILE}")

    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")  # Meilleures performances

    print("🔧 Création du schéma...")
    con.executescript(SCHEMA)

    migrer(con)
    stats(con)

    con.close()
    import os
    print(f"\n💾 Taille base : {os.path.getsize(DB_FILE)/1024:.1f} Ko")
    print(f"✅ Terminé → {DB_FILE}")
