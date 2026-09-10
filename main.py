"""Primo step dell'MVP: raccolta conversazionale dei dati dell'utente.

I dati vivono solo in ``st.session_state`` e sono predisposti per essere
passati successivamente al classificatore LLM.
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from groq_service import GroqService, GroqServiceError
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
        "analysis", "last_error",
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


def add_user_answer(answer: str) -> None:
    """Registra la risposta dell'utente nel contesto inviato a Groq."""
    st.session_state.messages.append({"role": "user", "content": answer})
    st.session_state.answers.append(answer)


def consult_groq() -> None:
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
                "Grazie, ho raccolto le informazioni. In base a quanto riportato, "
                f"la struttura che potrebbe essere più appropriata è: **{destination}**.\n\n"
                "È un orientamento informativo, non una diagnosi né una prescrizione."
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
        address = st.text_input("Indirizzo o posizione", placeholder="Es. Via Ostiense 159, Roma")
        additional_info = st.text_area(
            "Ulteriori informazioni utili (facoltativo)",
            placeholder="Es. allergie, gravidanza, patologie importanti o farmaci assunti",
        )
        submitted = st.form_submit_button("Inizia", type="primary")

    if submitted:
        if not address.strip():
            st.error("Inserisci un indirizzo o una posizione per poter trovare le strutture vicine.")
            return
        initialize_conversation(
            {
                "eta": int(age), "sesso": sex, "peso_kg": weight,
                "altezza_cm": height, "indirizzo": address.strip(),
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

    st.success("Raccolta completata. I dati sono pronti per il passaggio all'LLM.")
    st.subheader("Orientamento ricevuto")
    st.write(st.session_state.analysis["motivazione"])
    if st.session_state.analysis["livello_urgenza"] == "POSSIBILE_EMERGENZA":
        st.error("Possibile emergenza: chiama il 112 immediatamente.")
    payload = llm_input()
    with st.expander("Anteprima tecnica dei dati raccolti"):
        st.json(payload)
    st.download_button(
        "Scarica i dati raccolti (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name="raccolta_orientamento.json",
        mime="application/json",
    )


def main() -> None:
    st.set_page_config(page_title="Orientamento sanitario", page_icon="🩺", layout="centered")
    if not st.session_state.get("started"):
        render_start_form()
    else:
        render_chat()


if __name__ == "__main__":
    main()
