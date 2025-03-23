import streamlit as st
import numpy as np
import itertools

def calculate_mean(attendue, anova_cst, nb_mes, sd_nb_mes, ratio_ser, sd_ratio_ser):
    ratio_ser_eq = ratio_ser / 100
    return (attendue / 100) * (anova_cst + (nb_mes * sd_nb_mes) + (ratio_ser_eq * sd_ratio_ser))

def calculate_std(nb_mes, ratio_ser, attendue):
    facteur_lineaire = 2
    eq_ratio = -26.15 * np.log(ratio_ser) + 95
    eq_mes = facteur_lineaire * nb_mes
    ds_100 = eq_ratio + eq_mes
    ds_norm = ds_100 * (attendue / 100)
    return abs(ds_norm) / (1.96 * 2)

def calculate_confidence_interval(mean, std_dev):
    return max(0, mean - 1.96 * std_dev), mean + 1.96 * std_dev

def optimize_dosage(poids, dose_kg, concentration, volume_final_fixe=None, admin_type="discontinue"):
    anova_cst = 109
    sd_mes = 0.7
    sd_ratio = 7.9
    nb_mes_range = range(1, 11)

    available_syringes = {
        2: 0.1, 5: 0.2, 10: 0.2, 20: 1.0, 60: 1.0
    }

    min_ratio = 30
    min_ratio_mesurable = 50

    dose_attendue = poids * dose_kg
    base_volume_unitaire = dose_attendue / concentration

    if volume_final_fixe and volume_final_fixe > 0:
        volume_final = volume_final_fixe
        msg_final = f"Le volume final prescrit de {volume_final:.1f} mL a été respecté."
    else:
        volume_final = 50 if admin_type == "continue" else max(base_volume_unitaire, 3)
        msg_final = f"Le volume final permis a été limité à {volume_final:.0f} mL, mais la solution trouvée n’a utilisé que {{}} mL."

    best_combination = None
    min_error = float("inf")
    min_std = float("inf")

    for volume_unitaire in [base_volume_unitaire] + [x / 100 for x in range(10, 100, 5) if x / 100 > base_volume_unitaire]:
        for nb_mes, (syringe, grad) in itertools.product(nb_mes_range, available_syringes.items()):
            volume_total = volume_unitaire * nb_mes
            ratio_ser = (volume_unitaire / syringe) * 100

            print(f"🔍 Test NbMes={nb_mes}, Seringue={syringe} mL, VolumeUnitaire={volume_unitaire:.3f} mL, RatioSer={ratio_ser:.2f}%")

            if syringe < volume_unitaire:
                continue
            if volume_total > volume_final:
                continue
            if ratio_ser < min_ratio or ratio_ser > 100:
                continue
            if ratio_ser < min_ratio_mesurable and nb_mes == 1:
                continue
            if round(volume_unitaire / grad, 2) % 1 != 0:
                continue

            debit = max(0.1, round(volume_total / 24, 1))
            mean = calculate_mean(dose_attendue, anova_cst, nb_mes, sd_mes, ratio_ser, sd_ratio)
            std_dev = calculate_std(nb_mes, ratio_ser, dose_attendue)
            error = abs(mean - dose_attendue)

            print(f"✅ Accepté : Moyenne={mean:.2f}, Écart-Type={std_dev:.2f}, Erreur={error:.2f}")

            if error < min_error or (error == min_error and std_dev < min_std):
                min_error = error
                min_std = std_dev
                best_combination = (nb_mes, ratio_ser, syringe, mean, std_dev, volume_total, debit)

        if best_combination:
            break  # On arrête dès qu’une solution valide est trouvée

    return best_combination, base_volume_unitaire, dose_attendue, msg_final

# Interface Streamlit
st.set_page_config(page_title="Optimisation du Dosage Médical", layout="wide")
st.title("Optimisation du Dosage Médical")

poids = st.number_input("Entrez le poids du bébé (kg) :", min_value=0.1, value=3.0, step=0.1)
dose_kg = st.number_input("Entrez la dose prescrite (mg/kg) :", min_value=0.1, value=10.0, step=0.1)
concentration = st.number_input("Entrez la concentration du médicament (mg/mL) :", min_value=0.1, value=5.0, step=0.1)
volume_final = st.number_input("Volume final prescrit (laisser vide si non imposé) :", min_value=0.0, step=0.1)
admin_type = st.selectbox("Type d'administration :", ["discontinue", "continue"])

if st.button("Optimiser le dosage"):
    best_choice, volume_manipule, dose_attendue, message_final = optimize_dosage(
        poids, dose_kg, concentration, volume_final or None, admin_type
    )

    if best_choice:
        ci = calculate_confidence_interval(best_choice[3], best_choice[4])
        st.write("## Résultats de l'optimisation :")
        st.write(f"**Poids du bébé :** {poids} kg")
        st.write(f"**Dose prescrite :** {dose_kg} mg/kg")
        st.write(f"**Dose attendue :** {dose_attendue:.2f} mg")
        st.write(f"**Volume manipulé :** {best_choice[5]:.2f} mL")
        st.write(f"**Meilleur choix :** NbMes = {best_choice[0]}, RatioSer = {best_choice[1]:.2f}%, Seringue = {best_choice[2]} mL")
        st.write(f"**Moyenne :** {best_choice[3]:.2f}")
        st.write(f"**Écart-Type :** {best_choice[4]:.2f}")
        st.write(f"**Débit ajusté :** {best_choice[6]:.1f} mL/h")
        st.write(f"**Intervalle de confiance :** [{ci[0]:.2f}, {ci[1]:.2f}]")
        st.info(message_final.format(best_choice[5]))
    else:
        st.warning("⚠ Aucune combinaison trouvée qui respecte toutes les contraintes.")
