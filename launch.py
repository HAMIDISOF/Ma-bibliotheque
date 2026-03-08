#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Lanceur de la bibliothèque personnelle
Démarre Flask et ouvre automatiquement dans une nouvelle fenêtre navigateur
"""

import webbrowser
import threading
import subprocess
import sys
from pathlib import Path

URL = "http://localhost:5000"

def ouvrir_navigateur():
    webbrowser.open_new(URL)

if __name__ == "__main__":
    print("?? Démarrage de la bibliothèque personnelle...")
    print(f"?? Ouverture de {URL} dans une nouvelle fenêtre...")
    
    # Ouvre le navigateur après 1.5s (le temps que Flask démarre)
    threading.Timer(1.5, ouvrir_navigateur).start()
    
    # Lance bibliotheque.py
    script = Path(__file__).parent / "bibliotheque.py"
    subprocess.run([sys.executable, str(script)])