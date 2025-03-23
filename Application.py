
import streamlit as st
import numpy as np
import itertools

def calculate_mean(attendue, anova_cst, nb_mes, sd_nb_mes, ratio_ser, sd_ratio_ser):
    """Calcule la moyenne de la dose obtenue en fonction des paramètres du modèle."""
    ratio_ser_eq = ratio_ser / 100  
    return (attendue / 100) * (anova_cst + (nb_mes * sd_nb_mes) + (ratio_ser_eq * sd_ratio_ser))

def calculate_std(nb_mes, ratio_ser, attendue):
    """Calcule l'écart-type du dosage en fonction du nombre de mesures et du ratio seringue."""
    facteur_lineaire = 2  
    equation_ratio_ser = -26.15 * np.log(ratio_ser) + 95
    equation_nb_mes = facteur_lineaire * nb_mes
    ds_pour_100 = equation_ratio_ser + equation_nb_mes
    attendue_ratio = attendue / 100
    ds_normalise = ds_pour_100 * attendue_ratio
    return abs(ds_normalise) / (1.96 * 2)

def calculate_confidence_interval(mean, std_dev):
    """Calcule l'intervalle de confiance à 95% autour de la moyenne obtenue."""
    lower_bound = max(0, mean - 1.96 * std_dev)  
    upper_bound = mean + 1.96 * std_dev
    return lower_bound, upper_bound

def optimize_dosage(poids, dose_kg, concentration, volume_final_fixé=None):
    """Optimise le dosage en tenant compte des contraintes de volume, seringues et NbMes."""
    
    # ✅ Définition des constantes du modèle
    anova_cst = 109
    sd_nb_mes = 0.7
    sd_ratio_ser = 7.9
    nb_mes_range = range(1, 10)  
    available_syringes = [2, 5, 10, 20]  
    min_ratio = 30  

    # ✅ Calcul de la dose attendue et du volume nécessaire
    attendue = poids * dose_kg  
    volume_necessaire = attendue / concentration  
    
    # ✅ Gestion du volume final
    if volume_final_fixé and volume_final_fixé > 0:
        volume_final = volume_final_fixé
    else:
        volume_final = max(volume_necessaire, 3)  

    best_combination = None
    min_variability = float('inf')
    min_error = float('inf')

    # 🔹 Parcours des combinaisons (NbMes, Seringue)
    for nb_mes, syringe in itertools.product(nb_mes_range, available_syringes):
        if syringe < volume_necessaire:
            continue  

        ratio_ser = (volume_necessaire / syringe) * 100

        # ✅ Vérification des contraintes RatioSer
        if ratio_ser < min_ratio:
            continue  

        # ✅ Éviter les volumes trop grands
        volume_manipule = round(volume_necessaire * nb_mes, 2)
        if volume_manipule > volume_final:
            continue  

        # ✅ Calcul de la moyenne et de l'écart-type
        mean = calculate_mean(attendue, anova_cst, nb_mes, sd_nb_mes, ratio_ser, sd_ratio_ser)
        std_dev = calculate_std(nb_mes, ratio_ser, attendue)
        error = abs(mean - attendue)

        # ✅ Sélection du meilleur choix basé sur l’erreur et la variabilité
        if error < min_error or (error == min_error and std_dev < min_variability):
            min_error = error
            min_variability = std_dev
            best_combination = (nb_mes, ratio_ser, syringe, mean, std_dev, volume_manipule)

    # ✅ Sécurisation si aucune solution optimale trouvée
    if not best_combination:
        best_combination = (
            nb_mes_range[0], min_ratio, min(available_syringes),
            calculate_mean(attendue, anova_cst, nb_mes_range[0], sd_nb_mes, min_ratio, sd_ratio_ser),
            calculate_std(nb_mes_range[0], min_ratio, attendue),
            round(volume_necessaire, 2)
        )

    return best_combination, volume_necessaire, attendue

# ✅ Interface utilisateur avec Streamlit
st.set_page_config(page_title="Optimisation du Dosage Médical", layout="wide")

st.title("Optimisation du Dosage Médical")

poids = st.number_input("Entrez le poids du bébé (kg) :", min_value=0.1, value=3.0, step=0.1)
dose_kg = st.number_input("Entrez la dose prescrite (mg/kg) :", min_value=0.1, value=10.0, step=0.1)
concentration = st.number_input("Entrez la concentration du médicament (mg/mL) :", min_value=0.1, value=5.0, step=0.1)
volume_final_fixé = st.number_input("Volume final prescrit (laisser vide si non imposé) :", min_value=0.0, step=0.1)

if st.button("Optimiser le dosage"):
    best_choice, volume_manipule, dose_attendue = optimize_dosage(poids, dose_kg, concentration, volume_final_fixé or None)
    confidence_interval = calculate_confidence_interval(best_choice[3], best_choice[4])
    
    st.write("## Résultats de l'optimisation :")
    st.write(f"**Poids du bébé :** {poids} kg")
    st.write(f"**Dose prescrite :** {dose_kg} mg/kg")
    st.write(f"**Dose attendue :** {dose_attendue:.2f} mg")
    st.write(f"**Volume manipulé :** {best_choice[5]:.2f} mL")
    st.write(f"**Meilleur choix :** NbMes = {best_choice[0]}, RatioSer = {best_choice[1]:.2f}%, Seringue = {best_choice[2]} mL")
    st.write(f"**Moyenne :** {best_choice[3]:.2f}")
    st.write(f"**Écart-Type :** {best_choice[4]:.2f}")
    st.write(f"**Intervalle de confiance :** [{confidence_interval[0]:.2f}, {confidence_interval[1]:.2f}]")
