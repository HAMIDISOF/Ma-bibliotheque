#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generer_certificat.py
=====================
Génère un certificat SSL auto-signé pour activer HTTPS sur Ma Bibliothèque.
Lance ce script UNE SEULE FOIS depuis le dossier Bibliothèque.

Dépendance :
    pip install cryptography
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime
import ipaddress
import socket
import pathlib

# ── Trouver l'IP locale automatiquement ──────────────────────────────────────
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_locale = s.getsockname()[0]
    s.close()
except Exception:
    ip_locale = "192.168.1.113"

print(f"📡 IP locale détectée : {ip_locale}")

# ── Générer la clé privée ─────────────────────────────────────────────────────
print("🔑 Génération de la clé privée...")
cle = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# ── Générer le certificat ─────────────────────────────────────────────────────
print("📜 Génération du certificat...")
sujet = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u"Ma Bibliotheque"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Jardin Cooperatif"),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(sujet)
    .issuer_name(sujet)
    .public_key(cle.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))  # 10 ans
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address(ip_locale)),
        ]),
        critical=False,
    )
    .sign(cle, hashes.SHA256(), default_backend())
)

# ── Sauvegarder les fichiers ──────────────────────────────────────────────────
dossier = pathlib.Path(__file__).parent

cle_path  = dossier / "ssl_key.pem"
cert_path = dossier / "ssl_cert.pem"

with open(cle_path, "wb") as f:
    f.write(cle.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

with open(cert_path, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print(f"✅ Certificat généré !")
print(f"   🔑 Clé     : {cle_path}")
print(f"   📜 Certificat : {cert_path}")
print()
print(f"🌐 Ton appli sera accessible en HTTPS :")
print(f"   PC        → https://127.0.0.1:5678")
print(f"   Téléphone → https://{ip_locale}:5678")
print()
print("⚠️  La première fois, Brave affichera 'site non sécurisé'.")
print("    Clique sur 'Avancé' → 'Continuer quand même' — une seule fois !")
