import streamlit as st
import numpy as np
import itertools

def calculate_mean(attendue, anova_cst, nb_mes, sd_nb_mes, ratio_ser, sd_ratio_ser):
    ratio_ser_eq = ratio_ser / 100  # Conversion du ratio en fraction
    return (attendue / 100) * (anova_cst + (nb_mes * sd_nb_mes) + (ratio_ser_eq * sd_ratio_ser))

def calculate_std(nb_mes, fact_nb_mes, ratio_ser, fact_ratio_ser, attendue):
    facteur_lineaire = 2  # Facteur linéaire donné
    equation_ratio_ser = -26.15 * np.log(ratio_ser) + 95
    equation_nb_mes = facteur_lineaire * nb_mes
    ds_pour_100 = equation_ratio_ser + equation_nb_mes
    attendue_ratio = attendue / 100
    ds_normalise = ds_pour_100 * attendue_ratio
    return abs(ds_normalise) / (1.96 * 2)

def calculate_confidence_interval(mean, std_dev):
    lower_bound = max(0, mean - 1.96 * std_dev)
    upper_bound = mean + 1.96 * std_dev
    return lower_bound, upper_bound

def optimize_dosage(poids, dose_kg, concentration):
    anova_cst = 109
    sd_nb_mes = 0.7
    sd_ratio_ser = 7.9
    fact_nb_mes = 0.5
    fact_ratio_ser = 1.2
    nb_mes_range = range(1, 10)
    available_syringes = [1, 5, 10, 20]
    min_ratio = 30
    
    attendue = poids * dose_kg
    volume_necessaire = attendue / concentration
    
    best_combination = None
    min_variability = float('inf')
    min_error = float('inf')
    
    for nb_mes, syringe in itertools.product(nb_mes_range, available_syringes):
        if syringe < volume_necessaire:
            continue
        
        ratio_ser = (volume_necessaire / syringe) * 100
        if ratio_ser < min_ratio or ratio_ser > 100:
            continue
        
        mean = calculate_mean(attendue, anova_cst, nb_mes, sd_nb_mes, ratio_ser, sd_ratio_ser)
        std_dev = calculate_std(nb_mes, fact_nb_mes, ratio_ser, fact_ratio_ser, attendue)
        error = abs(mean - attendue)
        
        if error < min_error or (error == min_error and std_dev < min_variability):
            min_error = error
            min_variability = std_dev
            best_combination = (nb_mes, ratio_ser, syringe, mean, std_dev)
    
    if not best_combination:
        best_combination = (nb_mes_range[0], min_ratio, min(available_syringes), 
                            calculate_mean(attendue, anova_cst, nb_mes_range[0], sd_nb_mes, min_ratio, sd_ratio_ser), 
                            calculate_std(nb_mes_range[0], fact_nb_mes, min_ratio, fact_ratio_ser, attendue))
    
    return best_combination, volume_necessaire, attendue

st.set_page_config(page_title="Optimisation du Dosage Médical", layout="wide")

# Personnalisation du fond
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f1f1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Disposition des logos
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.image("amu_logo.jpg", width=160)
with col3:
    st.image("hopital_logo.PNG", width=160)

st.title("Optimisation du Dosage Médical")

poids = st.number_input("Entrez le poids du bébé (kg) :", min_value=0.1, value=3.0, step=0.1)
dose_kg = st.number_input("Entrez la dose prescrite (mg/kg) :", min_value=0.1, value=10.0, step=0.1)
concentration = st.number_input("Entrez la concentration du médicament (mg/mL) :", min_value=0.1, value=5.0, step=0.1)

if st.button("Optimiser le dosage"):
    best_choice, volume_manipule, dose_attendue = optimize_dosage(poids, dose_kg, concentration)
    confidence_interval = calculate_confidence_interval(best_choice[3], best_choice[4])
    
    st.write("## Résultats de l'optimisation :")
    st.write(f"**Poids du bébé :** {poids} kg")
    st.write(f"**Dose prescrite :** {dose_kg} mg/kg")
    st.write(f"**Dose attendue :** {dose_attendue:.2f} mg")
    st.write(f"**Volume manipulé :** {volume_manipule:.2f} mL")
    st.write(f"**Meilleur choix :** NbMes = {best_choice[0]}, RatioSer = {best_choice[1]:.2f}%, Seringue = {best_choice[2]} mL")
    st.write(f"**Moyenne :** {best_choice[3]:.2f}")
    st.write(f"**Ecart-Type :** {best_choice[4]:.2f}")
    st.write(f"**Intervalle de confiance :** [{confidence_interval[0]:.2f}, {confidence_interval[1]:.2f}]")
