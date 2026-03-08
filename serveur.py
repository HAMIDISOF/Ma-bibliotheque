#!/usr/bin/env python3
"""
Serveur Flask — API locale pour la bibliothèque
Lance avec : python serveur.py
Accès       : http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import sys

# Ajouter le répertoire courant au path pour importer bibliotheque
sys.path.insert(0, str(Path(__file__).parent))
from bibliotheque import Bibliotheque

BASE_DIR = Path(__file__).parent
app = Flask(__name__, static_folder=str(BASE_DIR))

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def bib():
    return Bibliotheque(BASE_DIR / "bibliotheque.db")

def ok(data):
    return jsonify({"ok": True, "data": data})

def err(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code

# ─── ROUTES STATIQUES ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

# ─── API STATS ────────────────────────────────────────────────────────────────
@app.route("/api/stats")
def stats():
    with bib() as b:
        return ok(b.stats())

# ─── API RECHERCHE ────────────────────────────────────────────────────────────
@app.route("/api/rechercher")
def rechercher():
    with bib() as b:
        resultats = b.rechercher(
            query        = request.args.get("q") or None,
            type_res     = request.args.get("type") or None,
            statut       = request.args.get("statut") or None,
            tag          = request.args.get("tag") or None,
            auteur       = request.args.get("auteur") or None,
            langue       = request.args.get("langue") or None,
            localisation = request.args.get("localisation") or None,
            annee_min    = request.args.get("annee_min") or None,
            annee_max    = request.args.get("annee_max") or None,
            tri          = request.args.get("tri") or "titre",
            limit        = int(request.args.get("limit", 200))
        )
        return ok(resultats)

# ─── API LISTES (pour filtres) ────────────────────────────────────────────────
@app.route("/api/tags")
def tags():
    with bib() as b:
        cur = b.con.cursor()
        rows = cur.execute("""
            SELECT t.libelle, COUNT(*) as n
            FROM tags t JOIN ressource_tags rt ON rt.tag_id = t.id
            GROUP BY t.libelle ORDER BY n DESC
        """).fetchall()
        return ok([{"libelle": r[0], "count": r[1]} for r in rows])

@app.route("/api/auteurs")
def auteurs():
    with bib() as b:
        cur = b.con.cursor()
        q = request.args.get("q", "")
        rows = cur.execute("""
            SELECT a.nom, COUNT(*) as n
            FROM auteurs a JOIN ressource_auteurs ra ON ra.auteur_id = a.id
            WHERE a.nom LIKE ?
            GROUP BY a.nom ORDER BY a.nom LIMIT 20
        """, (f"%{q}%",)).fetchall()
        return ok([{"nom": r[0], "count": r[1]} for r in rows])

@app.route("/api/types")
def types():
    with bib() as b:
        cur = b.con.cursor()
        rows = cur.execute("""
            SELECT t.libelle, COUNT(*) as n FROM types t
            JOIN ressources r ON r.type_id = t.id
            GROUP BY t.libelle ORDER BY n DESC
        """).fetchall()
        return ok([{"libelle": r[0], "count": r[1]} for r in rows])

# ─── API CRUD ─────────────────────────────────────────────────────────────────
@app.route("/api/ressource/<rid>")
def get_ressource(rid):
    with bib() as b:
        r = b.get(rid)
        if not r:
            return err("Ressource introuvable", 404)
        return ok(r)

@app.route("/api/ressource", methods=["POST"])
def ajouter():
    data = request.json or {}
    try:
        with bib() as b:
            rid = b.ajouter(**data)
            return ok({"id": rid})
    except ValueError as e:
        return err(str(e))

@app.route("/api/ressource/<rid>", methods=["PUT"])
def modifier(rid):
    data = request.json or {}
    try:
        with bib() as b:
            b.modifier(rid, **data)
            return ok({"id": rid})
    except ValueError as e:
        return err(str(e))

@app.route("/api/ressource/<rid>", methods=["DELETE"])
def supprimer(rid):
    try:
        with bib() as b:
            b.supprimer(rid)
            return ok({"id": rid})
    except ValueError as e:
        return err(str(e))

# ─── API ISBN ─────────────────────────────────────────────────────────────────
@app.route("/api/isbn/<isbn>")
def isbn(isbn):
    with bib() as b:
        meta = b.isbn_lookup(isbn)
        if not meta:
            return err("ISBN non trouvé", 404)
        return ok(meta)

# ─── API EXPORT ───────────────────────────────────────────────────────────────
@app.route("/api/exporter")
def exporter():
    with bib() as b:
        f = b.exporter_json()
        return ok({"fichier": str(f)})

# ─── LANCEMENT ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from waitress import serve
    print("""
╔══════════════════════════════════════════════════════╗
║         Bibliothèque personnelle — Serveur           ║
╠══════════════════════════════════════════════════════╣
║  Accès : http://localhost:5000                       ║
║  Arrêt : Ctrl+C  (arrêt propre garanti)              ║
╚══════════════════════════════════════════════════════╝
    """)
    serve(app, host="127.0.0.1", port=5000)
