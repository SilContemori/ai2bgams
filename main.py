"""Primo step dell'MVP: raccolta conversazionale dei dati dell'utente.

I dati vivono solo in ``st.session_state`` e sono predisposti per essere
passati successivamente al classificatore LLM.
"""

from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from groq_service import GroqService, GroqServiceError
from case_comunita import (
    LocationError,
    geocode_address,
    nearest_available_case_comunita,
)
from farmacie import nearest_open_farmacie
from pronto_soccorso import SORT_OPTIONS, nearest_pronto_soccorso, sort_candidates
from safety import emergency_analysis


INITIAL_QUESTION = (
    "Descrivi nel modo più dettagliato possibile il problema che stai "
    "riscontrando e da quanto tempo è presente. Indica sintomi, area del corpo "
    "interessata, intensità, modalità di comparsa ed eventuali sintomi associati."
)

def reset_conversation() -> None:
    """Rimuove i dati della conversazione dalla sola sessione corrente."""
    for key in (
        "started", "profile", "messages", "answers", "follow_up_count", "intake_complete",
        "analysis", "last_error", "user_coordinates", "location_error",
    ):
        st.session_state.pop(key, None)


def initialize_conversation(profile: dict[str, Any]) -> None:
    st.session_state.started = True
    st.session_state.profile = profile
    st.session_state.messages = [{"role": "assistant", "content": INITIAL_QUESTION}]
    st.session_state.answers = []
    st.session_state.follow_up_count = 0
    st.session_state.intake_complete = False
    st.session_state.analysis = None
    st.session_state.last_error = None
    st.session_state.user_coordinates = None
    st.session_state.location_error = None


def add_user_answer(answer: str) -> None:
    """Registra la risposta dell'utente nel contesto inviato a Groq."""
    st.session_state.messages.append({"role": "user", "content": answer})
    st.session_state.answers.append(answer)


def consult_groq(*, is_follow_up: bool = False) -> None:
    """Aggiunge alla chat la domanda o l'analisi restituite dal servizio Groq."""
    local_emergency = emergency_analysis(st.session_state.answers[-1])
    if local_emergency:
        st.session_state.analysis = local_emergency
        st.session_state.intake_complete = True
        st.session_state.last_error = None
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "**Possibile emergenza:** chiama subito il **112** oppure recati al "
                    "Pronto Soccorso più vicino. Non attendere la risposta del servizio online."
                ),
            }
        )
        return

    try:
        result = GroqService().assess(
            profile=st.session_state.profile,
            conversation=st.session_state.messages,
            follow_up_count=st.session_state.follow_up_count,
        )
    except GroqServiceError as error:
        st.session_state.last_error = str(error)
        return

    st.session_state.last_error = None
    if result.question:
        st.session_state.follow_up_count += 1
        st.session_state.messages.append({"role": "assistant", "content": result.question})
        return

    st.session_state.analysis = result.analysis
    st.session_state.intake_complete = True
    destination = result.analysis["destinazione_consigliata"]
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                (
                    f"**Aggiornamento dell'orientamento:** **{destination}**.\n\n"
                    f"{result.analysis['motivazione']}"
                )
                if is_follow_up
                else (
                    "Grazie, ho raccolto le informazioni. In base a quanto riportato, "
                    f"la struttura che potrebbe essere più appropriata è: **{destination}**.\n\n"
                    "È un orientamento informativo, non una diagnosi né una prescrizione."
                )
            ),
        }
    )


def llm_input() -> dict[str, Any]:
    """Restituisce il contratto dati da inviare all'LLM nel prossimo step."""
    return {
        "dati_personali": st.session_state.profile,
        "risposte_utente": st.session_state.answers,
        "conversazione": st.session_state.messages,
        "analisi_llm": st.session_state.analysis,
    }


def scroll_chat_to_bottom() -> None:
    """Porta la viewport all'ultimo messaggio dopo ogni rerun della chat."""
    st.html(
        """
        <script>
          const scrollToLatestMessage = () => {
            const content = document.querySelector('[data-testid="stMainBlockContainer"]');
            if (content) {
              content.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
          };
          window.setTimeout(scrollToLatestMessage, 100);
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def user_coordinates() -> tuple[float, float] | None:
    """Geocodifica l'indirizzo una sola volta durante la conversazione."""
    if st.session_state.user_coordinates:
        return st.session_state.user_coordinates
    if st.session_state.location_error:
        return None
    try:
        st.session_state.user_coordinates = geocode_address(st.session_state.profile["indirizzo"])
    except LocationError as error:
        st.session_state.location_error = str(error)
        return None
    return st.session_state.user_coordinates


def render_case_comunita_results() -> None:
    """Mostra le cinque Case della Comunità più vicine e disponibili."""
    st.subheader("Case della Comunità vicine")
    st.caption("Le distanze sono calcolate in linea d'aria dalla posizione inserita.")
    coordinates = user_coordinates()
    if not coordinates:
        st.warning(st.session_state.location_error)
        return

    try:
        structures = nearest_available_case_comunita(*coordinates)
    except FileNotFoundError as error:
        st.warning(str(error))
        return
    if not structures:
        st.info("Non risultano Case della Comunità disponibili con i dati attuali.")
        return

    for structure in structures:
        _, availability = structure.availability()
        with st.container(border=True):
            st.markdown(f"#### {structure.name}")
            st.write(f"{structure.address}, {structure.comune} · {structure.asl}")
            st.write(f"**Distanza:** {structure.distance_km:.1f} km")
            st.write(f"**Disponibilità:** {availability}")
            if structure.phone:
                st.write(f"**Telefono:** {structure.phone}")
            if structure.official_url:
                st.link_button("Consulta la scheda e gli orari ufficiali", structure.official_url)


def render_farmacie_results() -> None:
    """Mostra le cinque farmacie aperte più vicine alla posizione dell'utente."""
    st.subheader("Farmacie aperte vicine")
    st.caption("Le distanze sono calcolate in linea d'aria dalla posizione inserita.")
    st.warning("Orari simulati per il prototipo: verifica sempre con la farmacia prima di recarti.")
    coordinates = user_coordinates()
    if not coordinates:
        st.warning(st.session_state.location_error)
        return

    try:
        pharmacies = nearest_open_farmacie(*coordinates)
    except FileNotFoundError as error:
        st.warning(str(error))
        return
    if not pharmacies:
        st.info("Non risultano farmacie aperte secondo gli orari simulati del prototipo.")
        return

    for pharmacy in pharmacies:
        with st.container(border=True):
            st.markdown(f"#### {pharmacy.name}")
            st.write(pharmacy.full_address)
            st.write(f"**Distanza:** {pharmacy.distance_km:.1f} km")
            st.write("**Disponibilità:** Aperta ora (orario simulato)")
            st.write(f"**Orario simulato:** {pharmacy.simulated_schedule}")
            if pharmacy.typology:
                st.caption(f"Tipologia: {pharmacy.typology}")


def render_pronto_soccorso_results() -> None:
    """Mostra i cinque PS vicini con dati di affluenza e ordinamento selezionabile."""
    st.subheader("Pronto Soccorso vicini")
    st.caption("I Pronto Soccorso sono operativi 24 ore su 24. Distanze in linea d'aria.")
    coordinates = user_coordinates()
    if not coordinates:
        st.warning(st.session_state.location_error)
        return

    try:
        candidates = nearest_pronto_soccorso(*coordinates)
    except FileNotFoundError as error:
        st.warning(str(error))
        return
    if not candidates:
        st.info("Non risultano Pronto Soccorso con coordinate disponibili.")
        return

    newest_update = max(hospital.updated_at for hospital in candidates)
    st.warning(
        f"Dati di affluenza del file locale: ultimo aggiornamento disponibile {newest_update}. "
        "Non rappresentano una situazione in tempo reale."
    )
    sort_by = st.selectbox("Ordina i 5 Pronto Soccorso selezionati per", list(SORT_OPTIONS))
    for hospital in sort_candidates(candidates, sort_by):
        with st.container(border=True):
            st.markdown(f"#### {hospital.name}")
            st.write(f"{hospital.address} · {hospital.comune} · {hospital.emergency_type}")
            st.write(f"**Distanza:** {hospital.distance_km:.1f} km")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Totale persone presenti", hospital.total_present)
            with col2:
                st.metric("Totale in attesa", hospital.total_waiting)
            st.caption("Capacità/posti disponibili: dato non presente nel dataset.")
            st.markdown(
                "**In attesa:** "
                f"🔴 Rossi: {hospital.red_waiting} · 🟡 Gialli: {hospital.yellow_waiting} · "
                f"🟢 Verdi: {hospital.green_waiting} · ⚪ Bianchi: {hospital.white_waiting} · "
                f"❓ Non assegnati: {hospital.unassigned_waiting}"
            )
            st.write(
                f"In trattamento: **{hospital.total_treatment}** · "
                f"In osservazione breve: **{hospital.total_observation}**"
            )
            st.caption(f"Aggiornamento dati: {hospital.updated_at}")



def render_continuita_assistenziale() -> None:
    st.info(
        "**Hai bisogno di assistenza medica?** Per la continuità assistenziale nel Lazio "
        "chiama il **116117**."
    )


def render_start_form() -> None:
    st.title("Orientamento ai servizi sanitari")
    st.caption("Un supporto informativo: non sostituisce un medico e non effettua diagnosi.")
    st.info("In caso di emergenza o pericolo immediato, chiama il 112.")
    st.subheader("Prima di iniziare")
    st.write("Inserisci solo le informazioni utili: non servono nome, cognome o altri identificativi.")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Età", min_value=0, max_value=130, step=1)
            weight = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, step=0.5)
        with col2:
            sex = st.selectbox("Sesso", ["Preferisco non indicarlo", "Femmina", "Maschio", "Altro"])
            height = st.number_input("Altezza (cm)", min_value=30.0, max_value=250.0, step=0.5)
        st.markdown("##### Posizione")
        st.caption("Servono dati completi per evitare vie omonime in comuni diversi.")
        street, house_number = st.columns([3, 1])
        with street:
            street_name = st.text_input("Via o piazza", placeholder="Es. Via Ostiense")
        with house_number:
            civic_number = st.text_input("Civico", placeholder="159")
        cap, municipality, province = st.columns([1, 2, 1])
        with cap:
            postal_code = st.text_input("CAP", placeholder="00154", max_chars=5)
        with municipality:
            comune = st.text_input("Comune", placeholder="Roma")
        with province:
            provincia = st.text_input("Provincia", value="RM", max_chars=2)
        additional_info = st.text_area(
            "Ulteriori informazioni utili (facoltativo)",
            placeholder="Es. allergie, gravidanza, patologie importanti o farmaci assunti",
        )
        submitted = st.form_submit_button("Inizia", type="primary")

    if submitted:
        fields = (street_name, postal_code, comune, provincia)
        if not all(field.strip() for field in fields):
            st.error("Completa via/piazza, CAP, comune e provincia.")
            return
        if not re.fullmatch(r"\d{5}", postal_code.strip()):
            st.error("Il CAP deve contenere esattamente 5 cifre.")
            return
        if not re.fullmatch(r"[A-Za-z]{2}", provincia.strip()):
            st.error("La provincia deve essere composta da 2 lettere, ad esempio RM.")
            return
        address_parts = [street_name.strip()]
        if civic_number.strip():
            address_parts.append(civic_number.strip())
        full_address = (
            f"{', '.join(address_parts)}, {postal_code.strip()} {comune.strip()} "
            f"({provincia.strip().upper()}), Italia"
        )
        initialize_conversation(
            {
                "eta": int(age), "sesso": sex, "peso_kg": weight,
                "altezza_cm": height, "via_piazza": street_name.strip(),
                "civico": civic_number.strip(), "cap": postal_code.strip(),
                "comune": comune.strip(), "provincia": provincia.strip().upper(),
                "indirizzo": full_address,
                "informazioni_aggiuntive": additional_info.strip(),
            }
        )
        st.rerun()


def render_chat() -> None:
    st.title("Raccontaci cosa sta succedendo")
    st.caption("Le informazioni restano nella sessione corrente e servono solo all'orientamento.")

    with st.sidebar:
        st.subheader("Dati inseriti")
        st.write(f"**Età:** {st.session_state.profile['eta']}")
        st.write(f"**Posizione:** {st.session_state.profile['indirizzo']}")
        if st.button("Nuova conversazione"):
            reset_conversation()
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    scroll_chat_to_bottom()

    if st.session_state.last_error:
        st.error(st.session_state.last_error)
        if st.button("Riprova l'analisi con Groq", type="primary"):
            consult_groq()
            st.rerun()
        return

    if not st.session_state.intake_complete:
        answer = st.chat_input("Scrivi qui la tua risposta")
        if answer and answer.strip():
            add_user_answer(answer.strip())
            consult_groq()
            st.rerun()
        return

    if st.session_state.analysis["livello_urgenza"] == "POSSIBILE_EMERGENZA":
        st.error("Possibile emergenza: chiama il 112 immediatamente.")
    if st.session_state.analysis["destinazione_consigliata"] == "FARMACIA":
        render_continuita_assistenziale()
        render_farmacie_results()
    if st.session_state.analysis["destinazione_consigliata"] == "CASA_COMUNITA":
        render_continuita_assistenziale()
        render_case_comunita_results()
    if st.session_state.analysis["destinazione_consigliata"] == "PRONTO_SOCCORSO":
        render_pronto_soccorso_results()
    payload = llm_input()
    with st.expander("Anteprima tecnica dei dati raccolti"):
        st.json(payload)
    st.download_button(
        "Scarica i dati raccolti (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name="raccolta_orientamento.json",
        mime="application/json",
    )

    st.divider()
    st.subheader("Hai bisogno di chiarimenti?")
    st.caption("Puoi aggiungere un dettaglio o dire se l'orientamento non ti soddisfa.")
    follow_up = st.chat_input("Scrivi un altro messaggio", key="follow_up_chat")
    if follow_up and follow_up.strip():
        add_user_answer(follow_up.strip())
        consult_groq(is_follow_up=True)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Orientamento sanitario", page_icon="🩺", layout="centered")
    if not st.session_state.get("started"):
        render_start_form()
    else:
        render_chat()


if __name__ == "__main__":
    main()
