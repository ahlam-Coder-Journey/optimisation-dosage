import streamlit as st
import numpy as np
from fpdf import FPDF
import tempfile

# Seringues disponibles
SYRINGES_CONTINU = {
    2: 0.1,
    5: 0.2,
    10: 0.2,
    20: 1.0,
    50: 1.0,
    60: 1.0
}

SYRINGES_DISCONTINU = {
    5: 0.2,
    10: 0.2,
    20: 1.0,
    50: 1.0,
    60: 1.0
}

def arrondir_volume(volume, graduation):
    return round(round(volume / graduation) * graduation, 2)

def est_mesurable(volume, graduation):
    return abs(volume - arrondir_volume(volume, graduation)) <= 0.01

def generate_dilution_discontinu(dose_mg, concentration_init):
    current_concentration = concentration_init
    steps = []
    cible_min = dose_mg - 2
    cible_max = dose_mg + 2

    for etape in range(3):
        meilleures_options = []
        for syringe_volume, graduation in SYRINGES_DISCONTINU.items():
            vol_prelevables = np.arange(graduation, syringe_volume + 0.01, graduation)
            for volume_prelevé in vol_prelevables:
                if volume_prelevé < 5 * graduation:
                    continue
                if not est_mesurable(volume_prelevé, graduation):
                    continue

                max_ajout = syringe_volume - volume_prelevé
                vol_ajoutes = np.arange(0, max_ajout + 0.01, graduation)
                for vol_ajouté in vol_ajoutes:
                    volume_total = volume_prelevé + vol_ajouté
                    volume_total = arrondir_volume(volume_total, graduation)

                    if volume_total > syringe_volume or volume_total < 0.8:
                        continue

                    ratio = round((volume_total / syringe_volume) * 100, 2)
                    if ratio < 30:
                        continue

                    new_concentration = round(current_concentration * (volume_prelevé / volume_total), 2)

                    for volume_injecte in np.arange(graduation, volume_total + 0.01, graduation):
                        volume_injecte = arrondir_volume(volume_injecte, graduation)

                        if volume_injecte > syringe_volume or volume_injecte > volume_total:
                            continue

                        dose = round(new_concentration * volume_injecte, 2)
                        if dose > dose_mg + 2:
                            continue

                        if steps and abs(new_concentration - steps[-1]['concentration']) < 0.01:
                            continue

                        option = {
                            "étape": etape + 1,
                            "seringue": syringe_volume,
                            "volume prélevé": round(volume_prelevé, 2),
                            "volume ajouté": round(vol_ajouté, 2),
                            "volume total": volume_total,
                            "ratio": ratio,
                            "concentration": new_concentration,
                            "dose": dose,
                            "volume injecté": volume_injecte
                        }

                        meilleures_options.append(option)

        meilleures_options = sorted(meilleures_options, key=lambda x: (abs(x['dose'] - dose_mg), x['étape']))
        if not meilleures_options:
            break

        meilleure = meilleures_options[0]
        steps.append(meilleure)

        if cible_min <= meilleure['dose'] <= cible_max:
            break

        current_concentration = meilleure['concentration']

    return steps

def generate_dilution_continu(dose_mg, concentration_init, nb_hours=24, debit_mlh=0.1):
    current_concentration = concentration_init
    steps = []
    cible_min = dose_mg - 1.0
    cible_max = dose_mg + 1.0
    for etape in range(5):  
        meilleures_options = []
        for syringe_volume, graduation in SYRINGES_CONTINU.items():
            vol_prelevables = np.arange(graduation, syringe_volume + 0.01, graduation)
            for volume_prelevé in vol_prelevables:
                volume_prelevé = round(volume_prelevé, 2)
                max_ajout = syringe_volume - volume_prelevé
                for vol_ajouté in range(0, int(max_ajout) + 1):
                    volume_total = volume_prelevé + vol_ajouté
                    if volume_total > syringe_volume:
                        continue
                    ratio = round((volume_total / syringe_volume) * 100, 2)
                    if ratio < 30:
                        continue
                    volume_total = arrondir_volume(volume_total, graduation)
                    if volume_total > syringe_volume:
                        continue
                    new_concentration = round(current_concentration * (volume_prelevé / volume_total), 2)
                    if steps and abs(new_concentration - steps[-1]['concentration finale']) < 0.01:
                        continue
                    dose = round(new_concentration * debit_mlh * nb_hours, 2)
                    meilleures_options.append({
                        "étape": etape + 1,
                        "seringue": syringe_volume,
                        "volume prélevé": volume_prelevé,
                        "volume ajouté": vol_ajouté,
                        "volume total": volume_total,
                        "ratio": ratio,
                        "concentration finale": new_concentration,
                        "dose obtenue": dose
                    })
        meilleures_options = sorted(meilleures_options, key=lambda x: (x['dose obtenue'] < dose_mg, abs(x['dose obtenue'] - dose_mg)))
        if not meilleures_options:
            break
        meilleure = meilleures_options[0]
        steps.append(meilleure)
        if cible_min <= meilleure['dose obtenue'] <= cible_max:
            break
        current_concentration = meilleure['concentration finale']
    return steps

def generate_pdf(mode, dose, concentration, resultats):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Protocole de dilution médicamenteuse", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Mode : {mode}", ln=True)
    pdf.cell(200, 10, txt=f"Dose cible : {dose} mg", ln=True)
    pdf.cell(200, 10, txt=f"Concentration initiale : {concentration} mg/mL", ln=True)
    if mode == "Discontinu":
        pdf.cell(200, 10, txt=f"Volume injecté : {resultats[-1]['volume injecté']} mL", ln=True)
    else:
        pdf.cell(200, 10, txt="Vitesse de perfusion : 0.1 mL/h", ln=True)
    pdf.ln(5)

    for step in resultats:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(200, 10, txt=f"Étape {step['étape']} :", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(200, 8, txt=f" - Seringue : {step['seringue']} mL", ln=True)
        pdf.cell(200, 8, txt=f" - Volume prélevé : {step['volume prélevé']} mL", ln=True)
        pdf.cell(200, 8, txt=f" - Volume ajouté : {step['volume ajouté']} mL", ln=True)
        pdf.cell(200, 8, txt=f" - Volume total : {step['volume total']} mL", ln=True)
        pdf.cell(200, 8, txt=f" - Ratio rempli : {step['ratio']}%", ln=True)
        if mode == "Discontinu":
            pdf.cell(200, 8, txt=f" - Concentration obtenue : {step['concentration']} mg/mL", ln=True)
            pdf.cell(200, 8, txt=f" - Dose obtenue : {step['dose']} mg", ln=True)
            pdf.cell(200, 8, txt=f" - Volume injecté : {step['volume injecté']} mL", ln=True)
        else:
            pdf.cell(200, 8, txt=f" - Concentration finale : {step['concentration finale']} mg/mL", ln=True)
            pdf.cell(200, 8, txt=f" - Dose obtenue : {step['dose obtenue']} mg", ln=True)
        pdf.ln(3)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# Interface Streamlit
st.set_page_config(page_title="Calcul de dosage intelligent", page_icon="🧪", layout="centered")
st.title("💉 Application de calcul de dilution médicamenteuse")

mode = st.radio("Mode d'administration :", ["Continu", "Discontinu"])
dose = st.number_input("Dose cible (en mg) :", min_value=0.0, step=0.1)
concentration = st.number_input("Concentration initiale (en mg/mL) :", min_value=0.0, step=1.0)

if st.button("🧪 Générer le protocole de dilution"):
    if dose == 0 or concentration == 0:
        st.warning("Veuillez entrer une dose et une concentration valides.")
    else:
        resultats = generate_dilution_continu(dose, concentration) if mode == "Continu" else generate_dilution_discontinu(dose, concentration)

        if not resultats:
            st.error("❌ Aucun protocole trouvé.")
        else:
            st.success(f"✅ Protocole généré pour {dose} mg :")
            for step in resultats:
                with st.expander(f"🧪 Étape {step['étape']}"):
                    st.write(f"**Seringue utilisée** : {step['seringue']} mL")
                    st.write(f"**Volume prélevé** : {step['volume prélevé']} mL")
                    st.write(f"**Volume ajouté** : {step['volume ajouté']} mL")
                    st.write(f"**Volume total** : {step['volume total']} mL")
                    st.write(f"**Ratio seringue rempli** : {step['ratio']}%")
                    if mode == "Discontinu":
                        st.write(f"**Concentration obtenue** : {step['concentration']} mg/mL")
                        st.write(f"**Dose obtenue** : {step['dose']} mg")
                        st.write(f"**Volume injecté** : {step['volume injecté']} mL")
                    else:
                        st.write(f"**Concentration finale** : {step['concentration finale']} mg/mL")
                        st.write(f"**Dose obtenue** : {step['dose obtenue']} mg")
            if mode == "Discontinu":
                st.subheader(f"💉 Volume injecté : {resultats[-1]['volume injecté']} mL")
            else:
                st.subheader("💧 Mode continu avec une vitesse de perfusion de 0.1 mL/h")

            # Export PDF
            pdf_file = generate_pdf(mode, dose, concentration, resultats)
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="📄 Exporter le protocole en PDF",
                    data=f,
                    file_name=f"protocole_dosage_{mode.lower()}.pdf",
                    mime="application/pdf"
                )
