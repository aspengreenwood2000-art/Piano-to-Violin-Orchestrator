import itertools
import music21 as m21
import numpy as np

# Constants defining the physical layout of a standard violin matrix
VIOLIN_MIN_MIDI = 55  # G3 (Open G String)
VIOLIN_MAX_MIDI = 103  # G7 (Practical orchestral limit)
OPEN_STRINGS = [55, 62, 69, 76]  # MIDI pitches for G, D, A, E strings
MAX_FINGER_STRETCH = 5  # Max semitones human fingers can stretch comfortably


# =====================================================================
# FILTER 1: ACOUSTIC RANGE FILTER
# =====================================================================
def apply_violin_range_filter(note_sequence, strategy="octave_shift"):
    """Scans the note timeline and handles notes falling below G3 or above G7.

    Modifies music21 note/chord objects in place.
    """
    filtered_sequence = []

    for element in note_sequence:
        if isinstance(element, m21.note.Rest):
            filtered_sequence.append(element)
            continue

        if isinstance(element, m21.note.Note):
            current_midi = element.pitch.midi

            # Check for under-range violation
            if current_midi < VIOLIN_MIN_MIDI:
                if strategy == "octave_shift":
                    octaves_to_shift = 0
                    while current_midi < VIOLIN_MIN_MIDI:
                        current_midi += 12
                        octaves_to_shift += 1

                    element.pitch = element.pitch.transpose(
                        octaves_to_shift * 12
                    )
                    filtered_sequence.append(element)
                elif strategy == "drop":
                    continue  # Skip appending this note to drop it

            # Check for over-range violation
            elif current_midi > VIOLIN_MAX_MIDI:
                element.pitch = element.pitch.transpose(-12)
                filtered_sequence.append(element)
            else:
                filtered_sequence.append(element)

        elif isinstance(element, m21.chord.Chord):
            valid_chord_pitches = []
            for pitch in element.pitches:
                midi_val = pitch.midi
                while midi_val < VIOLIN_MIN_MIDI:
                    midi_val += 12
                if midi_val <= VIOLIN_MAX_MIDI:
                    valid_chord_pitches.append(m21.pitch.Pitch(midi_val))

            if valid_chord_pitches:
                element.pitches = valid_chord_pitches
                filtered_sequence.append(element)

    return filtered_sequence


# =====================================================================
# FILTER 2: FINGERBOARD GEOMETRY & COMBINATORICS SOLVER
# =====================================================================
def find_playable_violin_chord(target_midi_notes):
    """Maps an array of MIDI notes to physically executable vector coordinates

    on a 4-string non-Euclidean lattice matrix.
    """
    target_midi_notes = sorted(list(set(target_midi_notes)))

    # Violins cannot play more than 4 notes simultaneously
    if len(target_midi_notes) > 4:
        target_midi_notes = [
            target_midi_notes[0],
            target_midi_notes[-2],
            target_midi_notes[-1],
        ]

    valid_configurations = []
    string_combinations = itertools.permutations(
        range(4), len(target_midi_notes)
    )

    for combo in string_combinations:
        configuration = {}
        is_physically_possible = True
        finger_positions = []

        for note_idx, string_idx in enumerate(combo):
            target_note = target_midi_notes[note_idx]
            fret_pos = target_note - OPEN_STRINGS[string_idx]

            # Must sit between open string and first-position extension boundaries
            if fret_pos < 0 or fret_pos > 8:
                is_physically_possible = False
                break

            configuration[f"String_{string_idx}"] = {
                "pitch": target_note,
                "fret": fret_pos,
            }
            if fret_pos > 0:
                finger_positions.append(fret_pos)

        if is_physically_possible:
            if finger_positions:
                stretch_span = max(finger_positions) - min(finger_positions)
                if stretch_span > MAX_FINGER_STRETCH:
                    continue
            valid_configurations.append(configuration)

    if not valid_configurations:
        if len(target_midi_notes) > 2:
            # Recursive fallback down to a playable double-stop
            return find_playable_violin_chord(
                [target_midi_notes[0], target_midi_notes[-1]]
            )
        return None

    return valid_configurations[0]


# =====================================================================
# FILTER 3: CONTINUOUS STICK-SLIP BOWING SIMULATOR
# =====================================================================
def calculate_bowing_physics(note_sequence, tempo_bpm=120):
    """Models physical bow length depletion using deterministic exponential curves,

    automatically drawing slurs, down-bows, and up-bows into the sheet music.
    """
    current_direction = 1  # 1 = Down-bow, -1 = Up-bow
    accumulated_displacement = 0.0
    current_slur_notes = []
    beat_duration_sec = 60.0 / tempo_bpm

    for idx, note_element in enumerate(note_sequence):
        if isinstance(note_element, m21.note.Rest):
            accumulated_displacement = 0.0
            continue

        duration_beats = note_element.duration.quarterLength
        duration_seconds = duration_beats * beat_duration_sec

        # Calculate bow physical depletion velocity profile
        v_initial = (note_element.volume.velocity or 64) / 127.0
        gamma = 0.4
        note_displacement = (v_initial / gamma) * (
            1.0 - np.exp(-gamma * duration_seconds)
        )
        accumulated_displacement += note_displacement

        is_legato = False
        if idx < len(note_sequence) - 1:
            next_element = note_sequence[idx + 1]
            if next_element.offset == (
                note_element.offset + note_element.duration.quarterLength
            ):
                is_legato = True

        current_slur_notes.append(note_element)

        # If bow hair runs out or phrase breaks, write the execution markings
        if accumulated_displacement > 1.0 or not is_legato:
            start_note = current_slur_notes[0]
            if current_direction == 1:
                start_note.expressions.append(m21.expressions.DownBow())
            else:
                start_note.expressions.append(m21.expressions.UpBow())

            if len(current_slur_notes) > 1:
                # Group connected physical segments inside a bowing slur
                new_slur = m21.spanner.Slur(current_slur_notes)

                # Safely attach slur to active site if present, or assign spanner directly
                if note_element.activeSite is not None:
                    note_element.activeSite.insert(0, new_slur)
                elif start_note.activeSite is not None:
                    start_note.activeSite.insert(0, new_slur)

            # Reset physics systems state
            current_direction *= -1
            accumulated_displacement = 0.0
            current_slur_notes = []

    return note_sequence
  
