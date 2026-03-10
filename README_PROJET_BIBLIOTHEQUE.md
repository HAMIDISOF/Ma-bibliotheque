# 📚 PROJET BIBLIOTHÈQUE PERSONNELLE — Document mémoire
*Dernière mise à jour : 11 mars 2026*

---

## 🎯 Objectif

Construire un gestionnaire de bibliothèque personnelle **local**, dans l'esprit d'eSciDoc mais en plus light : **"en plus petit avec des bretelles"** — solide, fonctionnel, sans fioritures inutiles.

---

## 👤 Contexte utilisateur

- Bibliothèque personnelle avec **plusieurs centaines de ressources**
- Données **éparpillées** à différents endroits
- Une partie des livres papier déjà saisie dans l'appli **"Ma Bibliothèque"** (export CSV/txt avec séparateurs disponible)
- L'appli "Ma Bibliothèque" permettait le **scan de code-barre ISBN** → récupération automatique des métadonnées
- Interface souhaitée : **application desktop** (fenêtre native via pywebview)
- Hébergement : **local sur l'ordi** (pas de serveur distant)
- Accès téléphone : **via WiFi local** (même réseau)
- Pas de lien avec Proton Drive pour l'instant (première version stable d'abord !)

---

## 📦 Types de ressources à gérer

| Type | Spécificités |
|---|---|
| 📖 Livres papier | ISBN, localisation physique (étagère) |
| 📱 E-books (epub, mobi) | Chemin fichier local |
| 📄 PDFs / Documents | Chemin fichier local |
| 🎧 Audio (mp3, m4b) | Chemin fichier local, narrateur, durée |
| 📰 Articles / Revues | DOI, revue, volume, numéro |
| 🎨 BD / Manga | |
| 🎬 Films | |
| 🎮 Jeux vidéo | |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────┐
│  COUCHE 4 — Interface web locale        │
│  (pywebview + Flask, index.html)        │
├─────────────────────────────────────────┤
│  COUCHE 3 — Serveur Flask (app.py)      │
│  (API JSON, routes CRUD + ISBN)         │
├─────────────────────────────────────────┤
│  COUCHE 2 — Gestionnaire de ressources  │
│  (bibliotheque.py, classe Bibliotheque) │
├─────────────────────────────────────────┤
│  COUCHE 1 — Stockage SQLite             │
│  (bibliotheque.db, FTS5)                │
└─────────────────────────────────────────┘
```

---

## 🗂 Schéma base de données SQLite

```sql
-- Table principale
ressources (id, type_id, titre, serie, isbn, date_publication,
            editeur, pages, langue, localisation, statut_id,
            fichier, narrateur, duree, plateforme, format,
            lu, commentaire, couverture, lien_amazon, lien_fnac,
            date_ajout, source, proprietaire_id)

-- Propriétaires (ajouté 11/03/2026)
proprietaires (id, nom)     -- Kim, Lana, Jac, Sof, Invité + liste configurable depuis l'interface

-- Tables de référence
types      (id, libelle)       -- livre_papier, audio, ebook, pdf, article, bd, film, jeu_video
statuts    (id, libelle)       -- possédé, souhaité, prêté, lu, abandonné

-- Relations N-N
auteurs              (id, nom)
ressource_auteurs    (ressource_id, auteur_id)

tags                 (id, libelle)
ressource_tags       (ressource_id, tag_id)

-- Recherche fulltext (FTS5)
ressources_fts       (id, titre, auteurs, tags, commentaire)
```

---

## 🔑 Notes de conception importantes

- **Tags stockés en table relationnelle** (N-N via `ressource_tags`) — PAS en JSON. C'est ce qui permet les filtres par tag dans l'interface. Un champ JSON texte ne serait pas interrogeable proprement.
- **FTS5** pour la recherche fulltext sur titre, auteurs, tags, commentaire
- **pywebview** pour la fenêtre desktop : Flask tourne en thread daemon, pywebview ouvre une fenêtre native. Fermer la fenêtre = tout s'arrête proprement (pas de Ctrl+C)
- **Python 3.11.9 obligatoire** : pywebview n'est pas compatible Python 3.13/3.14 sur Windows (pythonnet manque)

---

## 🔌 API Flask (app.py)

| Méthode | Route | Action |
|---|---|---|
| GET | `/` | Sert index.html |
| GET | `/api/stats` | Statistiques globales |
| GET | `/api/types` | Liste des types avec compteurs |
| GET | `/api/tags` | Liste des tags avec compteurs |
| GET | `/api/rechercher` | Recherche multicritères (q, type, statut, tag, auteur, langue, localisation, proprietaire) |
| GET | `/api/ressource/<id>` | Fiche complète |
| POST | `/api/ressource` | Ajout |
| PUT | `/api/ressource/<id>` | Modification |
| DELETE | `/api/ressource/<id>` | Suppression |
| GET | `/api/isbn/<isbn>` | Lookup ISBN (Open Library + Google Books) |
| GET | `/api/proprietaires` | Liste des propriétaires |
| POST | `/api/proprietaires` | Ajouter un propriétaire |
| DELETE | `/api/proprietaires/<id>` | Supprimer un propriétaire |

---

## 🔌 API externes

| Service | Usage | Coût |
|---|---|---|
| **Open Library** | Récupération métadonnées via ISBN | Gratuit |
| **Google Books API** | Fallback si Open Library incomplet | Gratuit |

---

## 📋 Plan de développement

### Étape 1 ✅ — Conception
- Architecture définie, structure JSON validée, types listés

### Étape 2 ✅ — Import initial
- 150 ressources importées : 145 livres papier + 5 audio
- Script `import_mabibli.py` (xlsx → SQLite)

### Étape 3 ✅ — Terminée
- Schéma SQLite créé avec FTS5
- Script `bibliotheque.py` : CRUD complet, recherche multicritères, API ISBN

### Étape 4 ✅ — Terminée
- Interface web `index.html` : grille/liste, filtres, fiche détail, formulaire ajout/modif
- Serveur Flask `app.py` avec toutes les routes API
- Fenêtre desktop via **pywebview** (vraie appli, croix ✕ fonctionnelle)
- Accès téléphone via WiFi local
- Mode d'emploi `MODE_EMPLOI.md` rédigé

### Étape 5 — En cours de test
- Tests utilisateur : ajout ✅, suppression ✅, filtres ✅, recherche ✅
- Modifier ✅ (bug corrigé : `currentRessource` remis à null trop tôt)
- À valider : lookup ISBN, accès téléphone (404 à élucider)
- ✅ **11/03/2026** : Champ Propriétaire ajouté (filtre sidebar + gestion liste depuis l'interface)
- ✅ **11/03/2026** : Scan ISBN par caméra mobile (html5-qrcode, sans installation pip)

### Étape 6 — À faire
- Moteur de recherche fulltext (FTS5 déjà en place côté DB, à brancher finement)
- Gestion des prêts (à qui, depuis quand)
- Alertes stock / liste de souhaits améliorée

### Étape 7 — Évolutions futures
- Synchronisation Proton Drive (rclone)
- ~~Scan ISBN depuis mobile~~ ✅ Fait le 11/03/2026
- Export bibliographique (BibTeX, RIS)

---

## 📁 Fichiers du projet

| Fichier | Rôle |
|---|---|
| `app.py` | Lanceur principal (Flask + pywebview) |
| `bibliotheque.py` | Moteur SQLite — classe `Bibliotheque` |
| `bibliotheque.db` | Base de données SQLite principale |
| `index.html` | Interface web (couche 4) |
| `import_mabibli.py` | Script d'import xlsx → SQLite ✅ |
| `MODE_EMPLOI.md` | Guide utilisateur détaillé |
| `README_PROJET.md` | Ce document |

---

## ⚠️ Points d'attention / bugs connus

- **Accès téléphone** : 404 en cours d'investigation (fonctionne en local, pas encore validé en WiFi)
- **Python 3.11.9 obligatoire** : toujours lancer avec `py -3.11 app.py`
- **pywebview** : installé avec `--no-deps` + `proxy_tools bottle` (pythonnet non dispo sur Python 3.14)

---

## 💡 Notes de session

- Les filtres sidebar fonctionnent grâce à la table relationnelle `ressource_tags` — un champ texte JSON ne permettrait pas de filtrer proprement
- Bug Modifier corrigé : `fermerFiche()` remettait `currentRessource = null` avant que `ouvrirFormulaire()` puisse l'utiliser → sauvegarde de la variable avant l'appel
- Le bouton ＋ Ajouter a été déplacé du header (invisible sur fond noir) vers la toolbar crème

---

- **11/03/2026** : Champ Propriétaire — migration automatique DB existante, liste configurable via ⚙ dans la sidebar
- **11/03/2026** : Scan ISBN caméra — html5-qrcode via CDN, bouton 📷 dans le formulaire, fonctionne sur mobile
- **Note** : l'ancien `proprietaires.json` n'est plus utilisé — tout est en DB SQLite

---

*Pour reprendre le projet : donner ce document à Claude + les fichiers du projet*
