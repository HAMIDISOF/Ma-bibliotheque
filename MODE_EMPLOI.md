# 📚 Ma Bibliothèque — Mode d'emploi
*Version 1.0 — février 2026*

---

## 🚀 Lancement de l'application

Ouvre un terminal (invite de commandes) dans le dossier du projet et tape :

```
py -3.11 app.py
```

> ⚠️ **Important** : toujours utiliser `py -3.11` et non `python` ou `py` seul —
> l'application nécessite Python 3.11 (pas la 3.13 ni la 3.14 installées par défaut).

Une fenêtre s'ouvre automatiquement. Dans le terminal, tu verras aussi s'afficher :

```
📚 Ma Bibliothèque démarrée !
   PC        → http://127.0.0.1:XXXXX
   Téléphone → http://192.168.1.XX:XXXXX
```

**Note l'adresse "Téléphone" — tu en auras besoin pour l'accès mobile.**

---

## ❌ Fermeture de l'application

Clique simplement sur la **croix ✕** de la fenêtre. Tout s'arrête proprement,
pas besoin de Ctrl+C.

---

## 📱 Accès depuis le téléphone

Pratique pour ajouter un livre directement devant ta bibliothèque !

**Conditions :**
- Ton PC doit être allumé avec l'application lancée
- Ton téléphone doit être connecté au **même réseau WiFi** que ton PC

**Étapes :**
1. Lance l'appli sur ton PC (`py -3.11 app.py`)
2. Regarde l'adresse "Téléphone" affichée dans le terminal
   (ressemble à `http://192.168.1.42:55322`)
3. Sur ton téléphone → ouvre ton navigateur (Chrome, Safari, Opera...)
4. Tape cette adresse dans la barre d'adresse
5. L'interface s'affiche — elle est adaptée aux petits écrans

> ⚠️ **Ne pas utiliser `localhost`** depuis le téléphone — ça ne marche pas,
> `localhost` sur le téléphone pointe sur le téléphone lui-même, pas sur ton PC !

---

## ➕ Ajouter une ressource

1. Clique sur le bouton rouge **＋ Ajouter** (dans la barre de recherche)
2. Remplis les champs — **seul le titre est obligatoire**, tout le reste est optionnel
3. Pour un livre : tu peux saisir l'ISBN et cliquer **🔍 Chercher** pour remplir
   automatiquement titre, auteur, éditeur, année, pages...
4. Choisis le **Type** (Livre papier, Audio, E-book, PDF, BD...)
5. Choisis le **Statut** :
   - **Possédé** → tu l'as déjà
   - **Souhaité** → tu veux l'acheter (liste de souhaits !)
   - **Prêté** → tu l'as prêté à quelqu'un
   - **Lu** → déjà lu
6. Clique **✓ Enregistrer**

---

## ✏️ Modifier une ressource

1. Clique sur la carte du livre pour ouvrir sa fiche
2. Clique sur **✏️ Modifier**
3. Modifie les champs souhaités
4. Clique **✓ Enregistrer**

**Cas fréquent — passer un "Souhaité" en "Possédé" :**
1. Ouvre la fiche du livre souhaité
2. Clique **✏️ Modifier**
3. Change le **Statut** de "Souhaité" à "Possédé"
4. Complète les infos manquantes si besoin (localisation, étagère...)
5. Clique **✓ Enregistrer**

---

## 🗑 Supprimer une ressource

1. Clique sur la carte pour ouvrir la fiche
2. Clique sur **🗑 Supprimer** (bouton rouge en bas)
3. Confirme la suppression

> ⚠️ La suppression est définitive et irréversible !

---

## 🔍 Recherche et filtres

### Recherche rapide
Tape n'importe quoi dans la barre de recherche — elle cherche dans les titres,
auteurs, tags et commentaires simultanément.

### Filtres sidebar (colonne gauche)
- **Type** : filtre par type de ressource (Livre, Audio, E-book...)
- **Genres / Tags** : filtre par genre (Roman, SF, Histoire...)
- **Statut** : filtre par statut (Possédé, Souhaité, Prêté...)

Clique une seconde fois sur un filtre actif pour le désactiver.

### Recherche avancée
Clique sur **⚙ Avancé** pour accéder aux filtres supplémentaires :
- Par auteur
- Par localisation (étagère)
- Par période de publication (de... à...)

### Réinitialiser
Clique **✕ Réinitialiser** dans le panneau avancé pour effacer tous les filtres.

---

## 📖 Recherche par ISBN

Dans le formulaire d'ajout :
1. Saisis ou scanne l'ISBN dans le champ **"Recherche par ISBN"**
2. Clique **🔍 Chercher**
3. Les métadonnées se remplissent automatiquement depuis Open Library / Google Books
4. Vérifie et complète si besoin
5. Clique **✓ Enregistrer**

> 💡 **Depuis le téléphone** : si ton téléphone a un lecteur de codes-barres,
> tu peux scanner directement le code-barres du livre et coller l'ISBN dans le champ !

---

## 🖼 Vues disponibles

- **▦ Grille** : affichage en cartes avec couvertures (vue par défaut)
- **☰ Liste** : affichage en tableau avec titre, auteur, éditeur, année, localisation

Les boutons sont en haut à droite de la barre de recherche.

---

## 💡 Astuces

- **Localisation** : utilise un format cohérent pour retrouver facilement tes livres,
  par exemple `Salon — étagère 2` ou `Bureau — rangée 1`
- **Tags depuis la fiche** : en ouvrant une fiche, clique sur un tag pour filtrer
  immédiatement toutes les ressources avec ce tag
- **Tri** : utilise le menu déroulant en haut à droite pour trier par titre,
  auteur, date de publication ou date d'ajout

---

## 📁 Fichiers du projet

| Fichier | Rôle |
|---|---|
| `app.py` | Lanceur principal — à exécuter avec `py -3.11 app.py` |
| `bibliotheque.py` | Moteur de la base de données |
| `bibliotheque.db` | Base de données SQLite (ne pas supprimer !) |
| `index.html` | Interface graphique |

---

## 🆘 En cas de problème

**La fenêtre ne s'ouvre pas :**
Regarde le terminal — l'adresse PC s'affiche quand même.
Ouvre `http://127.0.0.1:XXXXX` dans ton navigateur.

**Le téléphone n'accède pas à l'appli :**
- Vérifie que PC et téléphone sont sur le même WiFi
- N'utilise pas `localhost` — utilise l'adresse IP affichée dans le terminal
- Vérifie que l'appli est bien lancée sur le PC

**Un filtre ne répond pas :**
Clique sur **✕ Réinitialiser** et réessaie.

---

*📚 Bonne lecture !*
