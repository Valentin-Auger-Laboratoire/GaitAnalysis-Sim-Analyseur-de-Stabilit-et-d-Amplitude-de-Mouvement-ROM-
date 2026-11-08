"""Génère images/marche.png (nécessite matplotlib) : python figures.py"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gaitanalysis import simuler, analyser, SCENARIOS

fig, ax = plt.subplots(1, 3, figsize=(14, 4))
s = simuler(bruit=0.5, graine=3, **SCENARIOS["genou_raide_droit"])
r = analyser(s)
m = s["t"] < 3.3
ax[0].plot(s["t"][m], s["genou_droit"][m], label="genou droit (raide)")
ax[0].plot(s["t"][m], s["genou_gauche"][m], label="genou gauche")
for a in r["attaques_droit"][r["attaques_droit"] < 3.3]:
    ax[0].axvline(a, c="#c8102e", lw=.8, ls="--")
ax[0].set(xlabel="temps (s)", ylabel="flexion (°)", title="Genou raide à droite : ROM 33° contre 59°")
ax[0].legend(fontsize=8)
phi = np.linspace(0, 1, 300)
from gaitanalysis import gabarit
for a, c in (("hanche", "C0"), ("genou", "C1"), ("cheville", "C2")):
    ax[1].plot(phi * 100, gabarit(a, phi), c, label=a)
ax[1].set(xlabel="% du cycle de marche", ylabel="angle (°)", title="Gabarits d'une marche normale")
ax[1].axvspan(60, 100, alpha=.08, color="gray"); ax[1].text(78, -18, "oscillation", ha="center", fontsize=8)
ax[1].legend(fontsize=8)
for nom, c in (("normal", "C0"), ("instable", "#c8102e")):
    s = simuler(graine=3, **SCENARIOS[nom])
    v = np.gradient(s["com_ml"], 1 / s["fe"])
    xcom = s["com_ml"] + v / math.sqrt(9.81 / 0.9)
    w = s["verite"]["largeur_pas"]
    mm = s["t"] < 4
    ax[2].plot(s["t"][mm], (w / 2 - np.abs(xcom[mm])) * 100, c=c, label=nom)
ax[2].axhline(0, c="k", lw=.8)
ax[2].set(xlabel="temps (s)", ylabel="marge de stabilité (cm)", title="Marge de stabilité médio-latérale (Hof)")
ax[2].legend(fontsize=8)
for a in ax: a.grid(alpha=.3)
fig.tight_layout(); fig.savefig("images/marche.png", dpi=120)
