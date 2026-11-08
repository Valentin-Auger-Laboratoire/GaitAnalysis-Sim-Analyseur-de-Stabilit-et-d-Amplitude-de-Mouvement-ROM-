"""Simulation et analyse de la marche : amplitudes articulaires (ROM), cycles, stabilité.

Les courbes articulaires sont des gabarits simplifiés d'une marche normale dans le plan
sagittal (hanche, genou, cheville, en degrés), indicés par la phase du cycle :
0 = attaque du talon, 1 = attaque suivante du même pied.
"""
import math
import numpy as np

G = 9.81
ARTICULATIONS = ("hanche", "genou", "cheville")
# Ordres de grandeur d'une marche adulte normale (indicatifs).
ROM_REFERENCE = {"hanche": (35, 50), "genou": (55, 70), "cheville": (20, 35)}


def _bosse(phi, centre, largeur):
    """Gaussienne périodique sur la phase (somme sur les cycles voisins)."""
    return sum(np.exp(-0.5 * ((phi - centre + k) / largeur) ** 2) for k in (-1, 0, 1))


def gabarit(articulation, phi, raideur_genou=1.0):
    phi = np.mod(phi, 1.0)
    if articulation == "hanche":  # flexion maximale à l'attaque du talon
        return 10 + 20 * np.cos(2 * np.pi * phi) + 3 * np.cos(4 * np.pi * phi)
    if articulation == "genou":  # petite flexion de mise en charge puis grande flexion en oscillation
        return 3 + 14 * _bosse(phi, 0.15, 0.06) + 58 * raideur_genou * _bosse(phi, 0.72, 0.09)
    if articulation == "cheville":  # flexion dorsale en appui puis flexion plantaire à la poussée
        return 2 + 10 * _bosse(phi, 0.45, 0.09) - 18 * _bosse(phi, 0.63, 0.05)
    raise ValueError(articulation)


SCENARIOS = {
    "normal": dict(),
    "genou_raide_droit": dict(raideur_genou_droit=0.55),
    "variabilite": dict(cv_foulee=0.08),
    "instable": dict(balancement=0.04, largeur_pas=0.10, cv_foulee=0.05),
}


def simuler(n_foulees=20, duree_foulee=1.1, fe=100.0, cv_foulee=0.02, raideur_genou_droit=1.0,
            balancement=0.02, largeur_pas=0.16, longueur_jambe=0.9, bruit=0.0, graine=0):
    """Simule une marche. Renvoie un dictionnaire de signaux et la vérité terrain.

    Côté droit en phase, côté gauche décalé d'une demi-foulée. Le centre de masse
    oscille latéralement d'un pied à l'autre (amplitude `balancement`, en m).
    """
    rng = np.random.default_rng(graine)
    durees = np.maximum(0.6, duree_foulee * (1 + cv_foulee * rng.standard_normal(n_foulees)))
    attaques_d = np.r_[0.0, np.cumsum(durees)]
    t = np.arange(0, attaques_d[-1], 1 / fe)
    i = np.clip(np.searchsorted(attaques_d, t, side="right") - 1, 0, n_foulees - 1)
    phase_d = i + (t - attaques_d[i]) / durees[i]  # phase continue, côté droit
    phase_g = phase_d + 0.5
    s = {"t": t, "fe": fe}
    for a in ARTICULATIONS:
        s[a + "_droit"] = gabarit(a, phase_d, raideur_genou_droit if a == "genou" else 1.0)
        s[a + "_gauche"] = gabarit(a, phase_g)
        if bruit:
            s[a + "_droit"] = s[a + "_droit"] + bruit * rng.standard_normal(len(t))
            s[a + "_gauche"] = s[a + "_gauche"] + bruit * rng.standard_normal(len(t))
    # centre de masse médio-latéral : vers le pied d'appui, une oscillation par foulée
    s["com_ml"] = balancement * np.sin(2 * np.pi * (phase_d - 0.25))
    s["verite"] = {"attaques_droit": attaques_d[:-1], "durees": durees,
                   "largeur_pas": largeur_pas, "longueur_jambe": longueur_jambe}
    return s


# --- Analyse ----------------------------------------------------------------

def detecter_attaques(hanche, fe, duree_min=0.6):
    """Attaques du talon = maximums de flexion de hanche (un par foulée).

    Le signal est lissé (moyenne glissante de 90 ms) pour ne pas se laisser piéger par le
    bruit sur le sommet arrondi de la courbe. Un pic est retenu s'il dépasse le milieu de
    l'amplitude et s'il est à au moins `duree_min` s du précédent ; sa position est affinée
    par une parabole ajustée sur ± 100 ms. Les bords du signal sont ignorés.
    """
    x = np.asarray(hanche, float)
    k = max(3, int(0.09 * fe) | 1)
    noyau = np.ones(k) / k
    xl = np.convolve(np.pad(x, k // 2, mode="edge"), noyau, mode="valid")
    seuil = 0.5 * (np.percentile(xl, 95) + np.percentile(xl, 5))
    ecart = int(duree_min * fe)
    demi = max(2, int(0.1 * fe))
    pics = []
    i = demi
    while i < len(xl) - demi:
        if xl[i] >= xl[i - 1] and xl[i] > xl[i + 1] and xl[i] > seuil:
            j = i + int(np.argmax(xl[i:i + ecart // 2]))  # le plus haut de la bosse
            if demi <= j < len(xl) - demi and (not pics or j - pics[-1] >= ecart):
                pics.append(j)
            i = j + ecart // 2
        else:
            i += 1
    temps = []
    for p in pics:
        u = np.arange(-demi, demi + 1)
        c2, c1, _ = np.polyfit(u, xl[p - demi:p + demi + 1], 2)
        dec = -c1 / (2 * c2) if c2 < 0 else 0.0
        temps.append((p + float(np.clip(dec, -demi, demi))) / fe)
    return np.array(temps)


def rom_par_cycle(signal, t, attaques):
    """Amplitude (max - min) de chaque cycle complet entre deux attaques."""
    out = []
    for a, b in zip(attaques[:-1], attaques[1:]):
        m = (t >= a) & (t < b)
        if m.sum() > 3:
            out.append(signal[m].max() - signal[m].min())
    return np.array(out)


def indice_symetrie(droit, gauche):
    """Indice de symétrie de Robinson, en % (0 = parfaitement symétrique)."""
    return abs(droit - gauche) / (0.5 * (droit + gauche)) * 100


def marge_stabilite(com, vitesse, bord_appui, longueur_jambe):
    """Marge de stabilité de Hof (2005) : bord de la base d'appui moins le centre de masse
    extrapolé XCoM = x + v / omega0, avec omega0 = racine(g / l). Négative = déséquilibre.
    Calculée pour un appui à droite (bord positif) ; symétrique à gauche.
    """
    omega0 = math.sqrt(G / longueur_jambe)
    return bord_appui - (com + vitesse / omega0)


def analyser(s):
    t, fe = s["t"], s["fe"]
    att_d = detecter_attaques(s["hanche_droit"], fe)
    att_g = detecter_attaques(s["hanche_gauche"], fe)
    durees = np.diff(att_d)
    res = {"attaques_droit": att_d, "attaques_gauche": att_g,
           "duree_foulee": durees.mean(), "cv_foulee": durees.std(ddof=1) / durees.mean() * 100,
           "cadence": 120 / durees.mean()}  # pas par minute : 2 pas par foulée
    for a in ARTICULATIONS:
        rd = rom_par_cycle(s[a + "_droit"], t, att_d)
        rg = rom_par_cycle(s[a + "_gauche"], t, att_g)
        res[a] = {"droit": rd.mean(), "gauche": rg.mean(), "ecart_type": np.r_[rd, rg].std(),
                  "symetrie": indice_symetrie(rd.mean(), rg.mean()),
                  "reference": ROM_REFERENCE[a]}
    # stabilité médio-latérale : pire marge de chaque foulée, côté droit comme côté gauche
    v = np.gradient(s["com_ml"], 1 / fe)
    w, l = s["verite"]["largeur_pas"], s["verite"]["longueur_jambe"]
    xcom = s["com_ml"] + v / math.sqrt(G / l)
    marge = w / 2 - np.abs(xcom)  # = marge_stabilite(...) vers le pied le plus proche
    mos = [marge[(t >= a) & (t < b)].min() for a, b in zip(att_d[:-1], att_d[1:])]
    res["marges_stabilite"] = np.array(mos)
    res["marge_stabilite_min"] = float(np.min(mos))
    res["marge_stabilite_moy"] = float(np.mean(mos))
    return res
