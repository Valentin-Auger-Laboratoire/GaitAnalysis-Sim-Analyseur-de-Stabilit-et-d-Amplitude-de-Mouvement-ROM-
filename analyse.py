"""Rapport d'analyse de marche sur une marche simulée.

Usage : python analyse.py [normal | genou_raide_droit | variabilite | instable]
"""
import sys

from gaitanalysis import simuler, analyser, SCENARIOS, ARTICULATIONS


def rapport(nom):
    s = simuler(bruit=0.5, graine=3, **SCENARIOS[nom])
    r = analyser(s)
    print(f"Scénario : {nom}")
    print(f"Foulées détectées : {len(r['attaques_droit'])} à droite, {len(r['attaques_gauche'])} à gauche")
    print(f"Durée de foulée : {r['duree_foulee']:.2f} s · cadence {r['cadence']:.0f} pas/min · "
          f"variabilité {r['cv_foulee']:.1f} %" + ("  ⚠ élevée (> 4 %)" if r["cv_foulee"] > 4 else ""))
    print("Amplitudes articulaires (ROM), en degrés :")
    for a in ARTICULATIONS:
        x = r[a]
        lo, hi = x["reference"]
        alerte = []
        if min(x["droit"], x["gauche"]) < lo:
            alerte.append("réduite")
        if x["symetrie"] > 10:
            alerte.append("asymétrique")
        print(f"  {a:9s} droite {x['droit']:5.1f} · gauche {x['gauche']:5.1f} · symétrie {x['symetrie']:4.1f} % "
              f"(repère {lo}–{hi}°)" + (f"  ⚠ {', '.join(alerte)}" if alerte else ""))
    m = r["marge_stabilite_min"]
    print(f"Marge de stabilité médio-latérale : min {m * 100:.1f} cm, moyenne {r['marge_stabilite_moy'] * 100:.1f} cm"
          + ("  ⚠ négative : le centre de masse sort de la base d'appui" if m < 0 else "  ⚠ faible" if m < 0.02 else ""))


if __name__ == "__main__":
    for nom in (sys.argv[1:] or SCENARIOS):
        rapport(nom)
        print()
