import importlib
music_engine = importlib.import_module("02_music_engine")
apply_violin_range_filter = music_engine.apply_violin_range_filter

import io
import music21 as m21
import streamlit as st

from 02_music_engine import (
    apply_violin_range_filter,
    calculate_bowing_physics,
    find_playable_violin_chord,
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Piano-to-Violin Orchestrator",
    page_icon="🎻",
    layout="wide"
)

st.title("🎻 Piano-to-Violin Orchestrator")
st.caption("Browser-Native Cross-Instrument Music Data Transfer Tool running via Pyodide / WebAssembly.")

# --- File Upload Section ---
uploaded_file = st.file_uploader(
    "Upload Piano Score (MusicXML or MIDI)",
    type=["musicxml", "mxl", "xml", "mid", "midi"]
)

# --- Configuration Options ---
strategy = st.selectbox(
    "Low Note Adaptation Strategy:",
    options=["octave_shift", "drop", "truncate", "transpose"],
    help="Determines how to handle notes below G3 (Violin open G string)."
)

# --- Core Processing Function ---
def process_score(file_bytes, filename, strategy_type):
    progress_bar = st.progress(0)
    status_box = st.empty()

    try:
        # Determine format from extension
        ext = filename.rsplit(".", 1)[-1].lower()
        file_format = "midi" if ext in ["mid", "midi"] else "musicxml"

        status_box.text(f"Parsing {file_format.upper()} structure in memory...")
        progress_bar.progress(20)

        # Parse score using music21
        if file_format == "musicxml":
            xml_string = file_bytes.decode("utf-8", errors="ignore")
            score = m21.converter.parse(xml_string, format="musicxml")
        else:
            score = m21.converter.parse(file_bytes, format="midi")

        all_raw_notes = [
            el for part in score.parts for el in part.flatten().notesAndRests
        ]
        progress_bar.progress(40)

        # 1. Apply Violin Range Filtering
        status_box.text("Applying Violin Range Filter...")
        playable_notes = apply_violin_range_filter(
            all_raw_notes, strategy=strategy_type
        )
        progress_bar.progress(60)

        # 2. Optimize Violin Chords
        status_box.text("Solving Fretboard Geometry Matrix...")
        for element in playable_notes:
            if isinstance(element, m21.chord.Chord):
                midi_list = [p.midi for p in element.pitches]
                optimized_shape = find_playable_violin_chord(midi_list)
                if optimized_shape:
                    element.pitches = [
                        val["pitch"] for val in optimized_shape.values()
                    ]
        progress_bar.progress(80)

        # 3. Calculate Bowing Dynamics
        status_box.text("Calculating physics equations for automated bowing...")
        calculate_bowing_physics(playable_notes, tempo_bpm=120)
        progress_bar.progress(90)

        # 4. Generate Output Stream
        status_box.text("Compiling score and preparing download...")
        output_buffer = io.BytesIO()
        
        if file_format == "musicxml":
            score.write("musicxml", fp=output_buffer)
            mime_type = "application/xml"
            out_ext = ".musicxml"
        else:
            score.write("midi", fp=output_buffer)
            mime_type = "audio/midi"
            out_ext = ".mid"

        progress_bar.progress(100)
        status_box.success("Orchestration Complete!")
        
        return output_buffer.getvalue(), mime_type, out_ext

    except Exception as e:
        status_box.error(f"Execution Error: {str(e)}")
        progress_bar.progress(0)
        return None, None, None


# --- Action & Download Logic ---
if uploaded_file is not None:
    st.success(f"File **{uploaded_file.name}** ready for processing.")

    if st.button("Generate Violin Score", type="primary", use_container_width=True):
        input_bytes = uploaded_file.read()
        
        with st.spinner("Adapting piano score for violin..."):
            output_bytes, mime_type, out_ext = process_score(
                input_bytes, uploaded_file.name, strategy
            )

        if output_bytes:
            base_name = uploaded_file.name.rsplit(".", 1)[0]
            st.session_state["processed_bytes"] = output_bytes
            st.session_state["processed_filename"] = f"{base_name}_Violin_Orchestrated{out_ext}"
            st.session_state["mime_type"] = mime_type

# Persistent Download Button UI
if "processed_bytes" in st.session_state:
    st.download_button(
        label="🎵 Download Orchestrated Score",
        data=st.session_state["processed_bytes"],
        file_name=st.session_state["processed_filename"],
        mime=st.session_state["mime_type"],
        use_container_width=True
    )
    

