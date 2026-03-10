#!/usr/bin/env python3
"""
Gestionnaire de bibliothèque personnelle
Couches 1 & 2 : stockage SQLite + gestion des ressources + API ISBN
"""

import sqlite3
import json
import uuid
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

DB_FILE = Path(__file__).parent / "bibliotheque.db"

# ─── TYPES ET STATUTS VALIDES ─────────────────────────────────────────────────
TYPES_VALIDES = [
    "livre_papier", "audio", "ebook", "pdf", "article", "bd", "film", "jeu_video"
]
STATUTS_VALIDES = ["possédé", "souhaité", "prêté", "lu", "abandonné"]


# ══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
class Bibliotheque:

    PROPRIETAIRES_DEFAUT = ["Kim", "Lana", "Jac", "Sof", "Invité"]

    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.con = sqlite3.connect(db_file)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.execute("PRAGMA journal_mode = WAL")
        self._migrer_proprietaires()

    def _migrer_proprietaires(self):
        """Crée la table propriétaires et ajoute la colonne si nécessaire."""
        cur = self.con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS proprietaires (
                id  INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE
            )
        """)
        count = cur.execute("SELECT COUNT(*) FROM proprietaires").fetchone()[0]
        if count == 0:
            for nom in self.PROPRIETAIRES_DEFAUT:
                cur.execute("INSERT OR IGNORE INTO proprietaires (nom) VALUES (?)", (nom,))
        cols = [r[1] for r in cur.execute("PRAGMA table_info(ressources)").fetchall()]
        if "proprietaire_id" not in cols:
            cur.execute("ALTER TABLE ressources ADD COLUMN proprietaire_id INTEGER REFERENCES proprietaires(id)")
        self.con.commit()

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── HELPERS INTERNES ──────────────────────────────────────────────────────

    def _uid(self):
        return str(uuid.uuid4())[:8]

    def _get_or_create(self, table, col, val):
        cur = self.con.cursor()
        cur.execute(f"SELECT id FROM {table} WHERE {col} = ?", (val,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(f"INSERT INTO {table} ({col}) VALUES (?)", (val,))
        return cur.lastrowid

    def _update_fts(self, ressource_id):
        """Met à jour l'index FTS5 pour une ressource."""
        cur = self.con.cursor()
        cur.execute("DELETE FROM ressources_fts WHERE id = ?", (ressource_id,))
        cur.execute("""
            INSERT INTO ressources_fts (id, titre, auteurs, tags, commentaire)
            SELECT
                r.id,
                r.titre,
                COALESCE((
                    SELECT GROUP_CONCAT(a.nom, ' ')
                    FROM ressource_auteurs ra JOIN auteurs a ON a.id = ra.auteur_id
                    WHERE ra.ressource_id = r.id
                ), ''),
                COALESCE((
                    SELECT GROUP_CONCAT(t.libelle, ' ')
                    FROM ressource_tags rt JOIN tags t ON t.id = rt.tag_id
                    WHERE rt.ressource_id = r.id
                ), ''),
                COALESCE(r.commentaire, '')
            FROM ressources r WHERE r.id = ?
        """, (ressource_id,))

    def _row_to_dict(self, row):
        """Convertit une Row SQLite en dict enrichi avec auteurs et tags."""
        if not row:
            return None
        d = dict(row)
        cur = self.con.cursor()
        d["auteurs"] = [r[0] for r in cur.execute("""
            SELECT a.nom FROM ressource_auteurs ra
            JOIN auteurs a ON a.id = ra.auteur_id
            WHERE ra.ressource_id = ?
        """, (d["id"],))]
        d["tags"] = [r[0] for r in cur.execute("""
            SELECT t.libelle FROM ressource_tags rt
            JOIN tags t ON t.id = rt.tag_id
            WHERE rt.ressource_id = ?
        """, (d["id"],))]
        pid = d.get("proprietaire_id")
        if pid:
            row = cur.execute("SELECT nom FROM proprietaires WHERE id=?", (pid,)).fetchone()
            d["proprietaire"] = row[0] if row else None
        else:
            d["proprietaire"] = None
        return d

    # ── AJOUTER ───────────────────────────────────────────────────────────────

    def ajouter(self, titre, type_res="livre_papier", statut="possédé",
                auteurs=None, tags=None, isbn=None, serie=None,
                date_publication=None, editeur=None, pages=None,
                langue=None, localisation=None, fichier=None,
                narrateur=None, duree=None, plateforme=None,
                format_res=None, commentaire=None, couverture=None,
                lien_amazon=None, lien_fnac=None, source="manuel",
                proprietaire=None):
        """Ajoute une nouvelle ressource. Retourne l'ID créé."""

        if type_res not in TYPES_VALIDES:
            raise ValueError(f"Type invalide : {type_res}. Valides : {TYPES_VALIDES}")
        if statut not in STATUTS_VALIDES:
            raise ValueError(f"Statut invalide : {statut}. Valides : {STATUTS_VALIDES}")

        rid = self._uid()
        type_id   = self._get_or_create("types",   "libelle", type_res)
        statut_id = self._get_or_create("statuts",  "libelle", statut)

        cur = self.con.cursor()
        cur.execute("""
            INSERT INTO ressources
            (id, type_id, titre, serie, isbn, date_publication, editeur,
             pages, langue, localisation, statut_id, fichier, narrateur,
             duree, plateforme, format, lu, commentaire, couverture,
             lien_amazon, lien_fnac, date_ajout, source, proprietaire_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            rid, type_id, titre, serie, isbn, date_publication, editeur,
            pages, langue, localisation, statut_id, fichier, narrateur,
            duree, plateforme, format_res, None, commentaire, couverture,
            lien_amazon, lien_fnac,
            datetime.today().strftime("%Y-%m-%d"), source,
            self._get_proprietaire_id(proprietaire)
        ))

        for nom in (auteurs or []):
            if nom:
                aid = self._get_or_create("auteurs", "nom", nom)
                cur.execute("INSERT OR IGNORE INTO ressource_auteurs VALUES (?,?)", (rid, aid))

        for tag in (tags or []):
            if tag:
                tid = self._get_or_create("tags", "libelle", tag)
                cur.execute("INSERT OR IGNORE INTO ressource_tags VALUES (?,?)", (rid, tid))

        self._update_fts(rid)
        self.con.commit()
        return rid

    # ── MODIFIER ──────────────────────────────────────────────────────────────

    def modifier(self, ressource_id, **kwargs):
        """
        Modifie les champs d'une ressource.
        Champs spéciaux : auteurs=[], tags=[] remplacent les listes.
        """
        cur = self.con.cursor()

        # Vérifier existence
        cur.execute("SELECT id FROM ressources WHERE id = ?", (ressource_id,))
        if not cur.fetchone():
            raise ValueError(f"Ressource '{ressource_id}' introuvable")

        # Champs scalaires modifiables
        champs_scalaires = {
            "titre", "serie", "isbn", "date_publication", "editeur",
            "pages", "langue", "localisation", "fichier", "narrateur",
            "duree", "plateforme", "commentaire", "couverture",
            "lien_amazon", "lien_fnac", "lu"
        }

        scalaires = {k: v for k, v in kwargs.items() if k in champs_scalaires}
        if scalaires:
            set_clause = ", ".join(f"{k} = ?" for k in scalaires)
            cur.execute(
                f"UPDATE ressources SET {set_clause} WHERE id = ?",
                list(scalaires.values()) + [ressource_id]
            )

        # Type
        if "type_res" in kwargs:
            type_id = self._get_or_create("types", "libelle", kwargs["type_res"])
            cur.execute("UPDATE ressources SET type_id = ? WHERE id = ?", (type_id, ressource_id))

        # Statut
        if "statut" in kwargs:
            statut_id = self._get_or_create("statuts", "libelle", kwargs["statut"])
            cur.execute("UPDATE ressources SET statut_id = ? WHERE id = ?", (statut_id, ressource_id))

        # Propriétaire
        if "proprietaire" in kwargs:
            pid = self._get_proprietaire_id(kwargs["proprietaire"])
            cur.execute("UPDATE ressources SET proprietaire_id = ? WHERE id = ?", (pid, ressource_id))

        # Auteurs (remplacement complet)
        if "auteurs" in kwargs:
            cur.execute("DELETE FROM ressource_auteurs WHERE ressource_id = ?", (ressource_id,))
            for nom in kwargs["auteurs"]:
                if nom:
                    aid = self._get_or_create("auteurs", "nom", nom)
                    cur.execute("INSERT OR IGNORE INTO ressource_auteurs VALUES (?,?)", (ressource_id, aid))

        # Tags (remplacement complet)
        if "tags" in kwargs:
            cur.execute("DELETE FROM ressource_tags WHERE ressource_id = ?", (ressource_id,))
            for tag in kwargs["tags"]:
                if tag:
                    tid = self._get_or_create("tags", "libelle", tag)
                    cur.execute("INSERT OR IGNORE INTO ressource_tags VALUES (?,?)", (ressource_id, tid))

        self._update_fts(ressource_id)
        self.con.commit()

    # ── SUPPRIMER ─────────────────────────────────────────────────────────────

    def supprimer(self, ressource_id):
        """Supprime une ressource et ses relations (CASCADE)."""
        cur = self.con.cursor()
        cur.execute("DELETE FROM ressources_fts WHERE id = ?", (ressource_id,))
        cur.execute("DELETE FROM ressources WHERE id = ?", (ressource_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Ressource '{ressource_id}' introuvable")
        self.con.commit()

    # ── RÉCUPÉRER ─────────────────────────────────────────────────────────────

    def get(self, ressource_id):
        """Retourne une ressource complète par son ID."""
        cur = self.con.cursor()
        cur.execute("""
            SELECT r.*, t.libelle as type, s.libelle as statut
            FROM ressources r
            JOIN types t ON t.id = r.type_id
            JOIN statuts s ON s.id = r.statut_id
            WHERE r.id = ?
        """, (ressource_id,))
        return self._row_to_dict(cur.fetchone())

    # ── RECHERCHE ─────────────────────────────────────────────────────────────

    def rechercher(self, query=None, type_res=None, statut=None,
                   tag=None, auteur=None, langue=None, localisation=None,
                   annee_min=None, annee_max=None, tri="titre", limit=200,
                   proprietaire=None):
        """
        Recherche multicritères.
        query        : fulltext (titre, auteurs, tags, commentaire)
        type_res     : filtrer par type
        statut       : filtrer par statut
        tag          : filtrer par tag exact
        auteur       : filtrer par nom auteur (LIKE)
        langue       : filtrer par langue
        localisation : filtrer par localisation (LIKE)
        annee_min    : année de publication >= annee_min
        annee_max    : année de publication <= annee_max
        tri          : titre | auteur | date | date_ajout
        """
        cur = self.con.cursor()

        if query:
            sql = """
                SELECT r.*, t.libelle as type, s.libelle as statut
                FROM ressources_fts f
                JOIN ressources r ON r.id = f.id
                JOIN types t ON t.id = r.type_id
                JOIN statuts s ON s.id = r.statut_id
                WHERE ressources_fts MATCH ?
            """
            # Ajout du wildcard * pour recherche partielle (ex: "Cah" trouve "Cahier")
            params = [query.strip() + "*"]
        else:
            sql = """
                SELECT r.*, t.libelle as type, s.libelle as statut
                FROM ressources r
                JOIN types t ON t.id = r.type_id
                JOIN statuts s ON s.id = r.statut_id
                WHERE 1=1
            """
            params = []

        if type_res:
            sql += " AND t.libelle = ?"
            params.append(type_res)
        if statut:
            sql += " AND s.libelle = ?"
            params.append(statut)
        if langue:
            sql += " AND r.langue = ?"
            params.append(langue)
        if localisation:
            sql += " AND r.localisation LIKE ?"
            params.append(f"%{localisation}%")
        if annee_min:
            sql += " AND SUBSTR(r.date_publication, 1, 4) >= ?"
            params.append(str(annee_min))
        if annee_max:
            sql += " AND SUBSTR(r.date_publication, 1, 4) <= ?"
            params.append(str(annee_max))
        if tag:
            sql += """
                AND r.id IN (
                    SELECT rt.ressource_id FROM ressource_tags rt
                    JOIN tags tg ON tg.id = rt.tag_id
                    WHERE tg.libelle = ?
                )
            """
            params.append(tag)
        if auteur:
            sql += """
                AND r.id IN (
                    SELECT ra.ressource_id FROM ressource_auteurs ra
                    JOIN auteurs a ON a.id = ra.auteur_id
                    WHERE a.nom LIKE ?
                )
            """
            params.append(f"%{auteur}%")
        if proprietaire:
            sql += """ AND r.proprietaire_id IN (
                SELECT id FROM proprietaires WHERE nom = ?
            )
            """
            params.append(proprietaire)

        # Tri
        ordre = {
            "titre":      "r.titre COLLATE NOCASE",
            "auteur":     "(SELECT MIN(a.nom) FROM ressource_auteurs ra JOIN auteurs a ON a.id=ra.auteur_id WHERE ra.ressource_id=r.id) COLLATE NOCASE",
            "date":       "r.date_publication DESC",
            "date_ajout": "r.date_ajout DESC",
        }.get(tri, "r.titre COLLATE NOCASE")
        sql += f" ORDER BY {ordre} LIMIT ?"
        params.append(limit)

        rows = cur.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ── API ISBN ──────────────────────────────────────────────────────────────

    def isbn_lookup(self, isbn):
        """
        Cherche les métadonnées d'un ISBN via Open Library.
        Fallback sur Google Books si Open Library ne trouve rien.
        Retourne un dict avec les champs prêts à passer à ajouter().
        """
        isbn_clean = isbn.replace("-", "").replace(" ", "")
        meta = self._isbn_openlibrary(isbn_clean)
        if not meta:
            meta = self._isbn_googlebooks(isbn_clean)
        return meta

    def _isbn_openlibrary(self, isbn):
        """Open Library API."""
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
            key = f"ISBN:{isbn}"
            if key not in data:
                return None
            book = data[key]
            return {
                "titre":            book.get("title"),
                "auteurs":          [a["name"] for a in book.get("authors", [])],
                "isbn":             isbn,
                "date_publication": book.get("publish_date"),
                "editeur":          ", ".join(p["name"] for p in book.get("publishers", [])),
                "pages":            str(book.get("number_of_pages", "")),
                "couverture":       book.get("cover", {}).get("medium"),
                "tags":             [s["name"] for s in book.get("subjects", [])[:5]],
                "source":           "openlibrary",
            }
        except Exception:
            return None

    def _isbn_googlebooks(self, isbn):
        """Google Books API (fallback)."""
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
            if not data.get("items"):
                return None
            info = data["items"][0]["volumeInfo"]
            return {
                "titre":            info.get("title"),
                "auteurs":          info.get("authors", []),
                "isbn":             isbn,
                "date_publication": info.get("publishedDate"),
                "editeur":          info.get("publisher"),
                "pages":            str(info.get("pageCount", "")),
                "langue":           info.get("language"),
                "couverture":       info.get("imageLinks", {}).get("thumbnail"),
                "tags":             info.get("categories", [])[:5],
                "source":           "googlebooks",
            }
        except Exception:
            return None

    def ajouter_par_isbn(self, isbn, type_res="livre_papier", **kwargs):
        """
        Récupère les métadonnées via ISBN et ajoute la ressource.
        Les kwargs écrasent les données de l'API (ex: localisation, statut).
        """
        print(f"🔍 Recherche ISBN {isbn}...")
        meta = self.isbn_lookup(isbn)
        if not meta:
            raise ValueError(f"ISBN {isbn} non trouvé dans Open Library ni Google Books")

        # Les kwargs ont priorité sur l'API
        meta.update(kwargs)
        meta["type_res"] = type_res
        meta["isbn"] = isbn

        rid = self.ajouter(**meta)
        print(f"✅ '{meta['titre']}' ajouté (ID: {rid})")
        return rid

    # ── EXPORT JSON ───────────────────────────────────────────────────────────

    def exporter_json(self, fichier_sortie=None):
        """Exporte toute la base en JSON (pour sauvegarde / Proton Drive)."""
        cur = self.con.cursor()
        rows = cur.execute("""
            SELECT r.*, t.libelle as type, s.libelle as statut
            FROM ressources r
            JOIN types t ON t.id = r.type_id
            JOIN statuts s ON s.id = r.statut_id
            ORDER BY r.titre
        """).fetchall()

        data = [self._row_to_dict(r) for r in rows]

        if fichier_sortie is None:
            fichier_sortie = Path(self.db_file).parent / "bibliotheque_export.json"

        with open(fichier_sortie, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(data)} ressources exportées → {fichier_sortie}")
        return fichier_sortie

    # ── STATS ─────────────────────────────────────────────────────────────────

    def stats(self):
        """Retourne un dict de statistiques sur la base."""
        cur = self.con.cursor()
        s = {}
        s["total"] = cur.execute("SELECT COUNT(*) FROM ressources").fetchone()[0]
        s["par_type"] = dict(cur.execute("""
            SELECT t.libelle, COUNT(*) FROM ressources r
            JOIN types t ON t.id = r.type_id GROUP BY t.libelle
        """).fetchall())
        s["par_statut"] = dict(cur.execute("""
            SELECT s.libelle, COUNT(*) FROM ressources r
            JOIN statuts s ON s.id = r.statut_id GROUP BY s.libelle
        """).fetchall())
        s["nb_auteurs"] = cur.execute("SELECT COUNT(*) FROM auteurs").fetchone()[0]
        s["nb_tags"]    = cur.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        return s
    
    # ── PROPRIÉTAIRES ─────────────────────────────────────────────────────────

    def _get_proprietaire_id(self, nom):
        if not nom:
            return None
        cur = self.con.cursor()
        row = cur.execute("SELECT id FROM proprietaires WHERE nom=?", (nom,)).fetchone()
        return row[0] if row else None

    def lister_proprietaires(self):
        cur = self.con.cursor()
        rows = cur.execute("SELECT id, nom FROM proprietaires ORDER BY nom").fetchall()
        return [{"id": r[0], "nom": r[1]} for r in rows]

    def ajouter_proprietaire(self, nom):
        nom = nom.strip()
        if not nom:
            raise ValueError("Nom vide")
        cur = self.con.cursor()
        cur.execute("INSERT OR IGNORE INTO proprietaires (nom) VALUES (?)", (nom,))
        self.con.commit()
        row = cur.execute("SELECT id FROM proprietaires WHERE nom=?", (nom,)).fetchone()
        return {"id": row[0], "nom": nom}

    def supprimer_proprietaire(self, pid):
        cur = self.con.cursor()
        # Désassocier les ressources avant suppression
        cur.execute("UPDATE ressources SET proprietaire_id=NULL WHERE proprietaire_id=?", (pid,))
        cur.execute("DELETE FROM proprietaires WHERE id=?", (pid,))
        self.con.commit()


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════
def afficher_ressource(r, court=False):
    if not r:
        print("❌ Ressource introuvable")
        return
    if court:
        auteurs = ", ".join(r.get("auteurs") or []) or "—"
        print(f"  [{r['id']}] {r['titre'][:55]:<55} {auteurs[:25]:<25} {r.get('type',''):<12} {r.get('statut','')}")
        return
    print(f"""
  ┌─ {r['titre']}
  │  ID          : {r['id']}
  │  Type        : {r.get('type')}
  │  Statut      : {r.get('statut')}
  │  Auteurs     : {', '.join(r.get('auteurs') or []) or '—'}
  │  Tags        : {', '.join(r.get('tags') or []) or '—'}
  │  ISBN        : {r.get('isbn') or '—'}
  │  Éditeur     : {r.get('editeur') or '—'}
  │  Publication : {r.get('date_publication') or '—'}
  │  Pages       : {r.get('pages') or '—'}
  │  Langue      : {r.get('langue') or '—'}
  │  Localisation: {r.get('localisation') or '—'}
  │  Série       : {r.get('serie') or '—'}
  │  Commentaire : {r.get('commentaire') or '—'}
  │  Fichier     : {r.get('fichier') or '—'}
  └─ Ajouté le   : {r.get('date_ajout') or '—'}""")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════╗
║           Gestionnaire de bibliothèque personnelle           ║
╚══════════════════════════════════════════════════════════════╝

Usage :
  python bibliotheque.py stats
  python bibliotheque.py chercher <mots clés>
  python bibliotheque.py chercher --type audio
  python bibliotheque.py chercher --tag SF
  python bibliotheque.py chercher --auteur Werber
  python bibliotheque.py get <ID>
  python bibliotheque.py isbn <ISBN>               → chercher infos
  python bibliotheque.py ajouter_isbn <ISBN>       → ajouter depuis ISBN
  python bibliotheque.py ajouter                   → saisie interactive
  python bibliotheque.py modifier <ID> titre="..." → modifier un champ
  python bibliotheque.py supprimer <ID>
  python bibliotheque.py exporter                  → export JSON
        """)
        sys.exit(0)

    commande = sys.argv[1].lower()

    with Bibliotheque() as bib:

        if commande == "stats":
            s = bib.stats()
            print(f"\n📚 Total : {s['total']} ressources\n")
            print("Par type :")
            for k, v in s["par_type"].items():
                print(f"  {k:<20} {v}")
            print("\nPar statut :")
            for k, v in s["par_statut"].items():
                print(f"  {k:<20} {v}")
            print(f"\n✍️  {s['nb_auteurs']} auteurs  |  🏷 {s['nb_tags']} tags")

        elif commande == "chercher":
            args = sys.argv[2:]
            kwargs = {}
            query_parts = []
            i = 0
            while i < len(args):
                if args[i] in ("--type", "--statut", "--tag", "--auteur", "--langue") and i+1 < len(args):
                    kwargs[args[i][2:].replace("type", "type_res")] = args[i+1]
                    i += 2
                else:
                    query_parts.append(args[i])
                    i += 1
            query = " ".join(query_parts) or None
            resultats = bib.rechercher(query=query, **kwargs)
            print(f"\n🔍 {len(resultats)} résultat(s)\n")
            for r in resultats:
                afficher_ressource(r, court=True)

        elif commande == "get" and len(sys.argv) >= 3:
            afficher_ressource(bib.get(sys.argv[2]))

        elif commande == "isbn" and len(sys.argv) >= 3:
            meta = bib.isbn_lookup(sys.argv[2])
            if meta:
                print("\n📖 Métadonnées trouvées :")
                for k, v in meta.items():
                    print(f"  {k:<20} {v}")
            else:
                print("❌ ISBN non trouvé")

        elif commande == "ajouter_isbn" and len(sys.argv) >= 3:
            isbn = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2]
            loc = input("  Localisation (étagère) : ").strip() or None
            bib.ajouter_par_isbn(isbn, localisation=loc)

        elif commande == "ajouter":
            print("\n➕ Nouvelle ressource")
            titre    = input("  Titre          : ").strip()
            type_res = input(f"  Type {TYPES_VALIDES} : ").strip() or "livre_papier"
            statut   = input(f"  Statut {STATUTS_VALIDES} : ").strip() or "possédé"
            auteurs  = [a.strip() for a in input("  Auteurs (séparés par ,) : ").split(",") if a.strip()]
            tags     = [t.strip() for t in input("  Tags    (séparés par ,) : ").split(",") if t.strip()]
            isbn     = input("  ISBN           : ").strip() or None
            editeur  = input("  Éditeur        : ").strip() or None
            loc      = input("  Localisation   : ").strip() or None
            rid = bib.ajouter(titre=titre, type_res=type_res, statut=statut,
                              auteurs=auteurs, tags=tags, isbn=isbn,
                              editeur=editeur, localisation=loc)
            print(f"✅ Ajouté (ID: {rid})")

        elif commande == "modifier" and len(sys.argv) >= 3:
            rid = sys.argv[2]
            champs = {}
            for arg in sys.argv[3:]:
                if "=" in arg:
                    cle, val = arg.split("=", 1)
                    if cle in ("auteurs", "tags"):
                        val = [v.strip() for v in val.split(",")]
                    champs[cle] = val
            if champs:
                bib.modifier(rid, **champs)
                print(f"✅ Ressource {rid} modifiée")
            else:
                print("❌ Précisez les champs : ex. titre='...' statut=lu")

        elif commande == "supprimer" and len(sys.argv) >= 3:
            rid = sys.argv[2]
            r = bib.get(rid)
            if r and input(f"  Supprimer '{r['titre']}' ? (oui/non) : ").lower() == "oui":
                bib.supprimer(rid)
                print("✅ Supprimé")

        elif commande == "exporter":
            bib.exporter_json()

        else:
            print(f"❌ Commande inconnue : {commande}")
