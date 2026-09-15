import os
import streamlit as st
import music21 as m21

# Import custom orchestration logic from the embedded music_engine module
from music_engine import (
    apply_violin_range_filter,
    find_playable_violin_chord,
    calculate_bowing_physics
)

# 1. Page Configuration
st.set_page_config(
    page_title="Violin Orchestrator",
    page_icon="🎻",
    layout="centered"
)

# 2. Header & Overview
st.title("Cross-Instrument Music Data Transfer Tool")
st.caption("Browser-Native Automated Orchestrator running via Pyodide / WebAssembly.")

# 3. User Inputs
uploaded_file = st.file_uploader(
    "Drag & Drop Piano MusicXML File Here",
    type=["musicxml", "mxl", "xml"]
)

strategy = st.selectbox(
    "Low Note Strategy:",
    options=["octave_shift", "drop"],
    help="Determines how to handle notes below G3 (Violin open G string)."
)

# 4. Core Processing Pipeline
def process_musicxml(file_bytes, strategy_type):
    progress_bar = st.progress(0)
    status_box = st.empty()

    try:
        # Step A: Parse raw MusicXML bytes into a music21 score structure
        status_box.text("Parsing MusicXML structure in browser memory...")
        progress_bar.progress(20)

        xml_string = file_bytes.decode("utf-8", errors="ignore")
        score = m21.converter.parse(xml_string, format="musicxml")

        all_raw_notes = [
            el for part in score.parts for el in part.flatten().notesAndRests
        ]
        progress_bar.progress(40)

        # Step B: Filter notes based on violin physical limits
        status_box.text("Applying Violin Range Filter...")
        playable_notes = apply_violin_range_filter(
            all_raw_notes, strategy=strategy_type
        )
        progress_bar.progress(60)

        # Step C: Optimize chord fingerings for violin fingerboard geometry
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

        # Step D: Apply physics rules for alternating bowing annotations (Π / V)
        status_box.text("Calculating physics equations for automated bowing...")
        calculate_bowing_physics(playable_notes, tempo_bpm=120)
        progress_bar.progress(90)

        # Step E: Compile output score to file in browser RAM
        status_box.text("Compiling score and generating download...")
        output_filepath = score.write("musicxml")
        
        with open(output_filepath, "rb") as f:
            output_bytes = f.read()

        progress_bar.progress(100)
        status_box.success("Orchestration Complete!")
        return output_bytes

    except Exception as e:
        status_box.error("Execution Error: " + str(e))
        progress_bar.progress(0)
        return None

# 5. Execution & Download Trigger
if uploaded_file is not None:
    if st.button("Generate Violin Score", type="primary", use_container_width=True):
        input_bytes = uploaded_file.read()
        processed_bytes = process_musicxml(input_bytes, strategy)

        if processed_bytes:
            base_name = uploaded_file.name.rsplit(".", 1)[0]
            st.download_button(
                label="Download Violin MusicXML",
                data=processed_bytes,
                file_name=base_name + "_Violin_Orchestrated.musicxml",
                mime="application/xml",
                use_container_width=True
            )

# 6. Footer
st.divider()
st.markdown("If this tool helped your orchestration workflow, consider supporting its development!")
st.markdown("[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/aspengreenwood)")
