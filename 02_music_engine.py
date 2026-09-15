import io
import music21 as m21

# Violin Range Limits (MIDI Pitch Numbers)
VIOLIN_MIN_MIDI = 55  # G3
VIOLIN_MAX_MIDI = 100  # E7


def apply_violin_range_filter(notes_and_rests, strategy="octave_shift"):
    """Filters notes to fit within the standard violin frequency range."""
    filtered_elements = []

    for element in notes_and_rests:
        if isinstance(element, m21.note.Note):
            # Create a copy to prevent in-place mutation side effects
            elem_copy = element

            # Handle Low Notes (Below G3)
            if elem_copy.pitch.midi < VIOLIN_MIN_MIDI:
                if strategy == "octave_shift":
                    while elem_copy.pitch.midi < VIOLIN_MIN_MIDI:
                        elem_copy.pitch.octave += 1
                    filtered_elements.append(elem_copy)
                elif strategy == "drop":
                    continue

            # Handle High Notes (Above E7)
            elif elem_copy.pitch.midi > VIOLIN_MAX_MIDI:
                elem_copy.pitch.midi = VIOLIN_MAX_MIDI
                filtered_elements.append(elem_copy)

            else:
                filtered_elements.append(elem_copy)
        else:
            # Pass rests and other score elements through unchanged
            filtered_elements.append(element)

    return filtered_elements


def find_playable_violin_chord(midi_pitches):
    """Maps pitch arrays to playable violin string configurations (up to 4 voices)."""
    valid_pitches = [
        p for p in midi_pitches if VIOLIN_MIN_MIDI <= p <= VIOLIN_MAX_MIDI
    ]
    if not valid_pitches:
        return None

    valid_pitches.sort()
    chord_shape = {}
    for idx, pitch in enumerate(valid_pitches[:4]):
        chord_shape[f"string_{idx + 1}"] = {
            "pitch": m21.pitch.Pitch(midi=pitch),
            "finger": idx + 1,
        }
    return chord_shape


def calculate_bowing_physics(notes, tempo_bpm=120):
    """Applies basic alternating down-bow (Π) and up-bow (V) annotations."""
    current_bow = "down"
    for element in notes:
        if isinstance(element, (m21.note.Note, m21.chord.Chord)):
            element.lyric = "Π" if current_bow == "down" else "V"
            current_bow = "up" if current_bow == "down" else "down"
    return notes
