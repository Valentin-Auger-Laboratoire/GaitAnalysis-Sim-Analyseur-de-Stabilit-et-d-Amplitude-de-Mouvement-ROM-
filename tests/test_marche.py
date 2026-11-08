"""Vérifications : python tests/test_marche.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gaitanalysis import (gabarit, simuler, SCENARIOS, detecter_attaques, rom_par_cycle,
                          indice_symetrie, marge_stabilite, analyser, ARTICULATIONS)

n_ok = 0


def ok(cond, msg):
    global n_ok
    if not cond:
        raise AssertionError(msg)
    n_ok += 1


phi = np.linspace(0, 1, 100001)
rom_vrai = {a: gabarit(a, phi).max() - gabarit(a, phi).min() for a in ARTICULATIONS}

# Gabarits : périodiques, attaque du talon = flexion maximale de hanche
for a in ARTICULATIONS:
    ok(abs(gabarit(a, 0.0) - gabarit(a, 1.0)) < 1e-9, f"{a} périodique")
ok(abs(phi[np.argmax(gabarit("hanche", phi))] % 1.0) < 1e-3 or abs(phi[np.argmax(gabarit("hanche", phi))] - 1) < 1e-3,
   "flexion maximale de hanche à l'attaque du talon")
ok(0.65 < phi[np.argmax(gabarit("genou", phi))] < 0.8, "flexion maximale du genou en oscillation")

# Détection des attaques du talon : nombre exact et précision < 15 ms, même avec du bruit
for graine in range(5):
    s = simuler(n_foulees=25, cv_foulee=0.05, bruit=0.5, graine=graine)
    vrai = s["verite"]["attaques_droit"][1:]  # la première est au tout premier échantillon : pas de pic visible
    det = detecter_attaques(s["hanche_droit"], s["fe"])
    ok(len(det) == len(vrai), f"nombre d'attaques (graine {graine}) : {len(det)} / {len(vrai)}")
    ok(np.max(np.abs(det - vrai)) < 0.015, f"précision des attaques (graine {graine})")

# ROM : retrouve l'amplitude du gabarit sur une marche sans bruit
s = simuler(n_foulees=15, cv_foulee=0.0, bruit=0.0, fe=500)
r = analyser(s)
for a in ARTICULATIONS:
    ok(abs(r[a]["droit"] - rom_vrai[a]) < 0.2 and abs(r[a]["gauche"] - rom_vrai[a]) < 0.2, f"ROM {a}")
    ok(r[a]["symetrie"] < 0.5, f"marche normale symétrique ({a})")
ok(abs(r["duree_foulee"] - 1.1) < 1e-3 and abs(r["cadence"] - 120 / 1.1) < 0.1, "durée de foulée et cadence")

# Genou raide : ROM réduite et asymétrie détectée, uniquement au genou
r = analyser(simuler(**SCENARIOS["genou_raide_droit"]))
ok(r["genou"]["droit"] < 0.7 * r["genou"]["gauche"] and r["genou"]["symetrie"] > 30, "genou raide détecté")
ok(r["hanche"]["symetrie"] < 2 and r["cheville"]["symetrie"] < 2, "hanche et cheville restent symétriques")

# Variabilité : le coefficient de variation suit celui qu'on a simulé
for cv in (0.02, 0.08):
    r = analyser(simuler(n_foulees=200, cv_foulee=cv, graine=11))
    ok(abs(r["cv_foulee"] - cv * 100) < 0.25 * cv * 100 + 0.3, f"variabilité {cv * 100:.0f} %")

# Indice de symétrie
ok(indice_symetrie(50, 50) == 0 and abs(indice_symetrie(60, 40) - 40) < 1e-12, "indice de symétrie")

# Marge de stabilité de Hof : formule et valeur théorique sur un balancement sinusoïdal
ok(abs(marge_stabilite(0.01, 0.0, 0.08, 0.9) - 0.07) < 1e-12, "MoS sans vitesse = bord - CoM")
ok(abs(marge_stabilite(0.0, math.sqrt(9.81 / 0.9) * 0.05, 0.08, 0.9) - 0.03) < 1e-12, "MoS : v / omega0 s'ajoute")
s = simuler(n_foulees=10, cv_foulee=0.0, fe=1000, balancement=0.02, largeur_pas=0.16)
r = analyser(s)
w = 2 * math.pi / 1.1
theorie = 0.08 - 0.02 * math.sqrt(1 + (w / math.sqrt(9.81 / 0.9)) ** 2)
ok(abs(r["marge_stabilite_min"] - theorie) < 2e-4, f"MoS théorique {theorie:.4f} / {r['marge_stabilite_min']:.4f}")
ok(analyser(simuler(**SCENARIOS["instable"]))["marge_stabilite_min"] < 0 < r["marge_stabilite_min"],
   "scénario instable : marge négative")

print(f"{n_ok} vérifications réussies")
