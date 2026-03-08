#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Ma Bibliothèque
=========================
Lance une fenêtre desktop (pywebview) avec Flask en arrière-plan.
Fermer la fenêtre arrête tout proprement — pas de Ctrl+C nécessaire.

Lancement :
    python app.py

Dépendances :
    pip install flask pywebview
"""

import threading
import socket
import sys
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request

from bibliotheque import Bibliotheque, TYPES_VALIDES, STATUTS_VALIDES

# ── CHEMINS ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DB_FILE    = BASE_DIR / "bibliotheque.db"
INDEX_FILE = BASE_DIR / "index.html"

# ── FLASK ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.config["JSON_AS_ASCII"] = False


def ok(data):
    return jsonify({"ok": True, "data": data})


def err(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code


# ── PAGE PRINCIPALE ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


# ── STATS ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    with Bibliotheque(DB_FILE) as bib:
        return ok(bib.stats())


# ── TYPES & TAGS ──────────────────────────────────────────────────────────────

@app.route("/api/types")
def api_types():
    with Bibliotheque(DB_FILE) as bib:
        cur = bib.con.cursor()
        rows = cur.execute("""
            SELECT t.libelle, COUNT(r.id) as count
            FROM types t
            LEFT JOIN ressources r ON r.type_id = t.id
            GROUP BY t.id
            ORDER BY count DESC
        """).fetchall()
        return ok([{"libelle": r[0], "count": r[1]} for r in rows])


@app.route("/api/tags")
def api_tags():
    with Bibliotheque(DB_FILE) as bib:
        cur = bib.con.cursor()
        rows = cur.execute("""
            SELECT t.libelle, COUNT(rt.ressource_id) as count
            FROM tags t
            LEFT JOIN ressource_tags rt ON rt.tag_id = t.id
            GROUP BY t.id
            ORDER BY count DESC, t.libelle
        """).fetchall()
        return ok([{"libelle": r[0], "count": r[1]} for r in rows])


# ── RECHERCHE ─────────────────────────────────────────────────────────────────

@app.route("/api/rechercher")
def api_rechercher():
    p = request.args
    with Bibliotheque(DB_FILE) as bib:
        resultats = bib.rechercher(
            query       = p.get("q")           or None,
            type_res    = p.get("type")         or None,
            statut      = p.get("statut")       or None,
            tag         = p.get("tag")          or None,
            auteur      = p.get("auteur")       or None,
            langue      = p.get("langue")       or None,
            localisation= p.get("localisation") or None,
            annee_min   = p.get("annee_min")    or None,
            annee_max   = p.get("annee_max")    or None,
            tri         = p.get("tri", "titre"),
        )
        return ok(resultats)


# ── RESSOURCE INDIVIDUELLE ────────────────────────────────────────────────────

@app.route("/api/ressource/<rid>")
def api_get_ressource(rid):
    with Bibliotheque(DB_FILE) as bib:
        r = bib.get(rid)
        if not r:
            return err("Ressource introuvable", 404)
        return ok(r)


@app.route("/api/ressource", methods=["POST"])
def api_ajouter():
    data = request.get_json(force=True)
    if not data or not data.get("titre"):
        return err("Le titre est obligatoire")
    try:
        with Bibliotheque(DB_FILE) as bib:
            rid = bib.ajouter(
                titre           = data["titre"],
                type_res        = data.get("type_res", "livre_papier"),
                statut          = data.get("statut", "possédé"),
                auteurs         = data.get("auteurs", []),
                tags            = data.get("tags", []),
                isbn            = data.get("isbn"),
                serie           = data.get("serie"),
                date_publication= data.get("date_publication"),
                editeur         = data.get("editeur"),
                pages           = data.get("pages"),
                langue          = data.get("langue"),
                localisation    = data.get("localisation"),
                fichier         = data.get("fichier"),
                narrateur       = data.get("narrateur"),
                duree           = data.get("duree"),
                commentaire     = data.get("commentaire"),
                couverture      = data.get("couverture"),
                source          = "interface",
            )
            return ok({"id": rid})
    except ValueError as e:
        return err(str(e))


@app.route("/api/ressource/<rid>", methods=["PUT"])
def api_modifier(rid):
    data = request.get_json(force=True)
    try:
        with Bibliotheque(DB_FILE) as bib:
            champs = {}
            for k in ["titre", "serie", "isbn", "date_publication", "editeur",
                      "pages", "langue", "localisation", "fichier", "narrateur",
                      "duree", "commentaire", "couverture"]:
                if k in data:
                    champs[k] = data[k]
            if "type_res" in data:  champs["type_res"] = data["type_res"]
            if "statut"   in data:  champs["statut"]   = data["statut"]
            if "auteurs"  in data:  champs["auteurs"]  = data["auteurs"]
            if "tags"     in data:  champs["tags"]     = data["tags"]
            bib.modifier(rid, **champs)
            return ok({"id": rid})
    except ValueError as e:
        return err(str(e))


@app.route("/api/ressource/<rid>", methods=["DELETE"])
def api_supprimer(rid):
    try:
        with Bibliotheque(DB_FILE) as bib:
            bib.supprimer(rid)
            return ok({"supprimé": rid})
    except ValueError as e:
        return err(str(e))


# ── ISBN ──────────────────────────────────────────────────────────────────────

@app.route("/api/isbn/<isbn>")
def api_isbn(isbn):
    with Bibliotheque(DB_FILE) as bib:
        meta = bib.isbn_lookup(isbn)
        if not meta:
            return err("ISBN non trouvé", 404)
        return ok(meta)


# ── LANCEMENT ─────────────────────────────────────────────────────────────────

def _trouver_port():
    """Trouve un port libre."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _lancer_flask(port):
    """Lance Flask dans un thread daemon."""
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def main():
    port = _trouver_port()

    # Flask dans un thread daemon (s'arrête quand la fenêtre se ferme)
    t = threading.Thread(target=_lancer_flask, args=(port,), daemon=True)
    t.start()

    try:
        import webview
    except ImportError:
        print("❌ pywebview non installé. Lance : pip install pywebview")
        print(f"   En attendant, ouvre http://127.0.0.1:{port} dans ton navigateur.")
        # Fallback : ouvre dans le navigateur par défaut
        import webbrowser, time
        time.sleep(0.8)
        webbrowser.open(f"http://127.0.0.1:{port}")
        input("Appuie sur Entrée pour quitter…")
        sys.exit(0)

    # Fenêtre pywebview — fermer la fenêtre = arrêt propre
    window = webview.create_window(
        title     = "📚 Ma Bibliothèque",
        url       = f"http://127.0.0.1:{port}",
        width     = 1280,
        height    = 820,
        min_size  = (800, 600),
        resizable = True,
    )
    import sys as _sys
    gui = "edgechromium" if _sys.platform == "win32" else None
    webview.start(gui=gui)
    # Quand start() retourne → la fenêtre a été fermée → le thread daemon s'arrête
    print("👋 Au revoir !")
    sys.exit(0)


if __name__ == "__main__":
    main()
