# app_dilution.py
import streamlit as st
import numpy as np
import math
from fpdf import FPDF
import tempfile

# ----------------------------- PARAMÈTRES -----------------------------
SYRINGES = {
    2: 0.1,
    5: 0.2,
    10: 0.2,
    20: 1.0,
    50: 1.0,
    60: 1.0
}

ANOVA = 109
SIGMA_MES = 0.7
SIGMA_RATIO = 7.9

# ----------------------------- FONCTIONS UTILES -----------------------------
def arrondir_volume(volume, graduation):
    return round(round(volume / graduation) * graduation, 2)

def est_mesurable(volume, graduation):
    return abs(volume - arrondir_volume(volume, graduation)) <= 0.01

def calculer_moyenne_precision(dose, nb_mes, ratio_ser):
    return (dose / 100) * (ANOVA + nb_mes * SIGMA_MES + (ratio_ser / 100) * SIGMA_RATIO)

def calculer_ecart_type(dose, nb_mes, ratio_ser):
    numerateur = abs((-26.15 * math.log(ratio_ser)) + 95 + 2 * nb_mes) * (dose / 100)
    return numerateur / (1.96 * 2)

def calculer_IC(moyenne, et):
    borne_inf = moyenne - 1.96 * et
    borne_sup = moyenne + 1.96 * et
    return (round(borne_inf, 2), round(borne_sup, 2))

# ---------------------- MODE DISCONTINU ----------------------
def generate_dilution_steps_discontinu(dose_mg, concentration_init):
    current_concentration = concentration_init
    steps = []
    cible_min = dose_mg - 1.0
    cible_max = dose_mg + 1.0

    for etape in range(5):
        meilleures_options = []
        for syringe_volume, graduation in SYRINGES.items():
            vol_prelevables = np.arange(graduation, syringe_volume + 0.01, graduation)
            for volume_prelevé in vol_prelevables:
                if volume_prelevé < 2 * graduation:
                    continue
                if not est_mesurable(volume_prelevé, graduation):
                    continue
                if (volume_prelevé / syringe_volume) * 100 < 30:
                    continue

                max_ajout = syringe_volume - volume_prelevé
                for vol_ajouté in np.arange(0, max_ajout + 0.01, graduation):
                    volume_total = round(volume_prelevé + vol_ajouté, 2)
                    if volume_total > syringe_volume:
                        continue
                    if not est_mesurable(volume_total, graduation):
                        continue

                    ratio = round((volume_total / syringe_volume) * 100, 2)
                    if ratio < 30:
                        continue

                    new_concentration = round(current_concentration * (volume_prelevé / volume_total), 2)

                    for volume_injecte in np.arange(graduation, syringe_volume + 0.01, graduation):
                        volume_injecte = arrondir_volume(volume_injecte, graduation)
                        if volume_injecte > syringe_volume:
                            continue

                        dose = round(new_concentration * volume_injecte, 2)
                        if dose > dose_mg + 1.5:
                            continue

                        moyenne_precision = calculer_moyenne_precision(dose, etape + 1, ratio)
                        ecart_type = calculer_ecart_type(dose, etape + 1, ratio)
                        ic_inf, ic_sup = calculer_IC(moyenne_precision, ecart_type)

                        option = {
                            "étape": etape + 1,
                            "seringue": syringe_volume,
                            "volume prélevé": volume_prelevé,
                            "volume ajouté": round(vol_ajouté, 2),
                            "volume total": volume_total,
                            "ratio": ratio,
                            "concentration": new_concentration,
                            "dose": dose,
                            "volume injecté": volume_injecte,
                            "moyenne_precision": moyenne_precision,
                            "ecart_type": ecart_type,
                            "IC": (ic_inf, ic_sup)
                        }

                        if etape == 0 and volume_prelevé <= 1.0:
                            option["remarque"] = "📏 Volume mesuré avec seringue de 1 mL pour précision."

                        meilleures_options.append(option)

        meilleures_options = sorted(meilleures_options, key=lambda x: (abs(x['dose'] - dose_mg), x['moyenne_precision']))

        if not meilleures_options:
            break

        meilleure = meilleures_options[0]
        steps.append(meilleure)

        if cible_min <= meilleure['dose'] <= cible_max:
            break

        current_concentration = meilleure['concentration']

    return steps

# ---------------------- MODE CONTINU (LOGIQUE MODIFIÉE) ----------------------
def generate_dilution_steps_continu(dose_mg, concentration_init, nb_hours=24, debit_mlh=0.1):
    current_concentration = concentration_init
    steps = []
    cible_min = dose_mg - 1.0
    cible_max = dose_mg + 1.0
    volume_injecte = round(debit_mlh * nb_hours, 2)
    affichage_etapes = []
    derniere_etape = None

    for etape in range(5):
        meilleures_options = []
        for syringe_volume, graduation in SYRINGES.items():
            vol_prelevables = np.arange(graduation, syringe_volume + 0.01, graduation)
            for volume_prelevé in vol_prelevables:
                if volume_prelevé < 2 * graduation:
                    continue
                if not est_mesurable(volume_prelevé, graduation):
                    continue
                if (volume_prelevé / syringe_volume) * 100 < 30:
                    continue
                if steps and volume_prelevé > steps[-1]['volume total']:
                    continue

                max_ajout = syringe_volume - volume_prelevé
                for vol_ajouté in np.arange(0, max_ajout + 0.01, graduation):
                    volume_total = round(volume_prelevé + vol_ajouté, 2)
                    if volume_total > syringe_volume:
                        continue
                    if not est_mesurable(volume_total, graduation):
                        continue
                    if (volume_total / syringe_volume) * 100 < 30:
                        continue
                    if etape >= 1 and volume_total < volume_injecte:
                        continue
                    if etape >= 1 and syringe_volume < 5:
                        continue

                    new_concentration = round(current_concentration * (volume_prelevé / volume_total), 2)
                    dose = round(new_concentration * volume_injecte, 2)
                    ratio_ser = round((volume_total / syringe_volume) * 100, 2)
                    moyenne_precision = calculer_moyenne_precision(dose, etape + 1, ratio_ser)
                    ecart_type = calculer_ecart_type(dose, etape + 1, ratio_ser)
                    ic_inf, ic_sup = calculer_IC(moyenne_precision, ecart_type)

                    option = {
                        "étape": etape + 1,
                        "seringue": syringe_volume,
                        "volume prélevé": volume_prelevé,
                        "volume ajouté": round(vol_ajouté, 2),
                        "volume total": volume_total,
                        "ratio": ratio_ser,
                        "concentration": new_concentration,
                        "dose": dose,
                        "moyenne_precision": moyenne_precision,
                        "ecart_type": ecart_type,
                        "IC": (ic_inf, ic_sup)
                    }

                    meilleures_options.append(option)

        meilleures_options = sorted(meilleures_options, key=lambda x: (abs(x['dose'] - dose_mg), x['moyenne_precision']))

        if not meilleures_options:
            break

        meilleure = meilleures_options[0]

        if meilleure['volume ajouté'] != 0:
            ratio_virtuel = round((meilleure['volume prélevé'] / meilleure['seringue']) * 100, 2)
            concentration_virtuelle = (meilleure['volume total'] * meilleure['concentration']) / meilleure['volume prélevé']
            concentration_virtuelle = round(concentration_virtuelle + 1e-3, 2)
            dose_obtenue = round(concentration_virtuelle * volume_injecte, 2)
            etape_virtuelle = {
                "type": "virtuelle",
                "seringue": meilleure['seringue'],
                "volume prélevé": meilleure['volume prélevé'],
                "ratio": ratio_virtuel,
                "concentration": concentration_virtuelle,
                "dose": dose_obtenue
            }
            affichage_etapes.append(etape_virtuelle)

        meilleure["type"] = "réelle"
        steps.append(meilleure)
        affichage_etapes.append(meilleure)
        derniere_etape = meilleure

        if cible_min <= meilleure['dose'] <= cible_max:
            break

        current_concentration = meilleure['concentration']

    if derniere_etape:
        affichage_etapes.append({
            "type": "metriques",
            "moyenne_precision": derniere_etape['moyenne_precision'],
            "ecart_type": derniere_etape['ecart_type'],
            "IC": derniere_etape['IC']
        })

    return affichage_etapes
