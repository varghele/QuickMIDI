import mido
import os
import json
import csv
import sys


def ensure_directories_exist(directories):
    """Create directories if they don't exist"""
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")


def get_time_signature(track):
    """Extract time signature from track"""
    numerator, denominator = 4, 4  # Default 4/4 time signature
    for msg in track:
        if msg.type == 'time_signature':
            numerator = msg.numerator
            denominator = msg.denominator
            return numerator, denominator
    return numerator, denominator


def get_tempo(track):
    """Extract tempo (microseconds per beat) from track"""
    tempo = 500000  # Default tempo (120 BPM)
    for msg in track:
        if msg.type == 'set_tempo':
            tempo = msg.tempo
            return tempo
    return tempo


def ticks_to_musical_time(ticks, ticks_per_beat, numerator, denominator):
    """Convert absolute ticks to bar.beat.tick format"""
    # Calculate how many ticks per bar
    ticks_per_bar = ticks_per_beat * numerator * 4 // denominator

    # Calculate bar, beat, and remaining ticks
    bars = ticks // ticks_per_bar
    remaining_ticks = ticks % ticks_per_bar

    beats = remaining_ticks // ticks_per_beat
    remaining_ticks = remaining_ticks % ticks_per_beat

    # Add 1 to make it 1-based instead of 0-based for musical notation
    return {
        "bar": bars + 1,
        "beat": beats + 1,
        "tick": remaining_ticks
    }


def musical_time_to_ticks(musical_time, ticks_per_beat, numerator, denominator):
    """Convert bar.beat.tick format to absolute ticks"""
    # Calculate how many ticks per bar
    ticks_per_bar = ticks_per_beat * numerator * 4 // denominator

    # Convert to 0-based counting
    bar = musical_time["bar"] - 1
    beat = musical_time["beat"] - 1
    tick = musical_time["tick"]

    # Calculate total ticks
    return (bar * ticks_per_bar) + (beat * ticks_per_beat) + tick


def format_note_name(note_number):
    """Convert MIDI note number to note name (C4, D#5, etc.)"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note_number // 12) - 1
    note = notes[note_number % 12]
    return f"{note}{octave}"


def midi_to_text(input_dir='input_mid', output_dir='input_txt'):
    """Convert MIDI files to editable CSV format with musical time positions"""
    ensure_directories_exist([input_dir, output_dir])

    # Check if there are any MIDI files to process
    midi_files = [f for f in os.listdir(input_dir) if f.endswith('.mid')]
    if not midi_files:
        print(f"No MIDI files found in {input_dir}")
        return

    # Process each MIDI file in the input directory
    for filename in midi_files:
        midi_path = os.path.join(input_dir, filename)

        # Load the MIDI file
        try:
            mid = mido.MidiFile(midi_path)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue

        # Find time signature and tempo from the first track (usually contains meta events)
        numerator, denominator = 4, 4  # Default time signature
        tempo = 500000  # Default tempo (120 BPM)

        if mid.tracks:
            numerator, denominator = get_time_signature(mid.tracks[0])
            tempo = get_tempo(mid.tracks[0])

        # Create JSON file for storing configuration and metadata
        json_filename = os.path.splitext(filename)[0] + '.json'
        json_path = os.path.join(output_dir, json_filename)

        # Save basic MIDI file configuration
        #with open(json_path, 'w') as f:
        #    json.dump({
        #        'filename': filename,
        #        'ticks_per_beat': mid.ticks_per_beat,
        #        'type': mid.type,
        #        'time_signature': {
        #            'numerator': numerator,
        #            'denominator': denominator
        #        },
        #        'tempo': tempo,
        #        'track_count': len(mid.tracks)
        #    }, f, indent=2)

        # Extract MIDI data
        for i, track in enumerate(mid.tracks):
            track_name = f"Track {i}"

            # Find track name if available
            for msg in track:
                if msg.type == 'track_name':
                    track_name = msg.name
                    break

            # Create the CSV for this track
            csv_filename = f"{os.path.splitext(filename)[0]}_track{i}_{track_name.replace(' ', '_')}.csv"
            csv_path = os.path.join(output_dir, csv_filename)

            # Keep track of absolute time position
            absolute_time = 0

            # Prepare data for CSV
            csv_data = []
            note_on_events = {}  # To keep track of note_on events for calculating durations

            for msg in track:
                # Update absolute time
                absolute_time += msg.time

                # Convert to musical position
                musical_pos = ticks_to_musical_time(
                    absolute_time,
                    mid.ticks_per_beat,
                    numerator,
                    denominator
                )

                position_str = f"{musical_pos['bar']}.{musical_pos['beat']}.{musical_pos['tick']}"

                # Process different message types
                if msg.type == 'note_on' and msg.velocity > 0:
                    # Store note_on event to calculate duration when note_off is encountered
                    note_key = (msg.channel, msg.note)
                    note_on_events[note_key] = {
                        'time': absolute_time,
                        'position': position_str,
                        'velocity': msg.velocity
                    }

                elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                    # Note off - calculate duration and add to CSV data
                    note_key = (msg.channel, msg.note)
                    if note_key in note_on_events:
                        note_on = note_on_events[note_key]
                        duration_ticks = absolute_time - note_on['time']

                        # Create readable data row
                        note_name = format_note_name(msg.note)

                        csv_data.append({
                            'Position': note_on['position'],
                            'Bar': musical_pos['bar'],
                            'Beat': musical_pos['beat'],
                            'Tick': note_on_events[note_key]['time'] % mid.ticks_per_beat,
                            'Type': 'Note',
                            'Channel': msg.channel,
                            'Note': msg.note,
                            'Note_Name': note_name,
                            'Velocity': note_on['velocity'],
                            'Duration_Ticks': duration_ticks,
                            'Off_Position': position_str
                        })

                        # Remove from tracking
                        del note_on_events[note_key]

                elif msg.type in ['control_change', 'program_change', 'pitch_bend']:
                    # Controller events
                    csv_data.append({
                        'Position': position_str,
                        'Bar': musical_pos['bar'],
                        'Beat': musical_pos['beat'],
                        'Tick': musical_pos['tick'],
                        'Type': msg.type,
                        'Channel': msg.channel,
                        'Controller': getattr(msg, 'control', ''),
                        'Value': getattr(msg, 'value', getattr(msg, 'program', '')),
                        'Note': '',
                        'Note_Name': '',
                        'Velocity': '',
                        'Duration_Ticks': '',
                        'Off_Position': ''
                    })

                elif msg.is_meta:
                    # Meta events
                    meta_value = ''
                    if hasattr(msg, 'tempo'):
                        meta_value = msg.tempo
                    elif hasattr(msg, 'key'):
                        meta_value = msg.key
                    elif hasattr(msg, 'name'):
                        meta_value = msg.name
                    elif hasattr(msg, 'text'):
                        meta_value = msg.text

                    csv_data.append({
                        'Position': position_str,
                        'Bar': musical_pos['bar'],
                        'Beat': musical_pos['beat'],
                        'Tick': musical_pos['tick'],
                        'Type': f"Meta_{msg.type}",
                        'Channel': '',
                        'Value': meta_value,
                        'Note': '',
                        'Note_Name': '',
                        'Velocity': '',
                        'Duration_Ticks': '',
                        'Off_Position': ''
                    })

            # Sort by position
            csv_data.sort(key=lambda x: (int(x['Bar']), int(x['Beat']), int(x['Tick'])))

            # Write to CSV
            if csv_data:
                fieldnames = ['Position', 'Bar', 'Beat', 'Tick', 'Type', 'Channel',
                              'Note', 'Note_Name', 'Velocity', 'Duration_Ticks',
                              'Off_Position', 'Controller', 'Value']

                with open(csv_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in csv_data:
                        writer.writerow(row)

                print(f"Created CSV for track {i} ({track_name}) in {csv_filename}")

        print(f"Converted {filename} to CSV format with metadata in {json_filename}")


def find_related_files(base_name, directory):
    """Find JSON config and associated CSVs for a MIDI file"""
    # Find JSON config file
    config_file = base_name + '.json'
    config_path = os.path.join(directory, config_file)

    if not os.path.exists(config_path):
        return None, []

    # Find all CSV tracks
    csv_files = [f for f in os.listdir(directory)
                 if f.startswith(base_name) and f.endswith('.csv')]

    return config_path, csv_files


def extract_track_number(csv_filename):
    """Extract track number from CSV filename"""
    parts = csv_filename.split('_track')
    if len(parts) > 1:
        track_num = parts[1].split('_')[0]
        try:
            return int(track_num)
        except ValueError:
            pass
    return 0  # Default track number


def text_to_midi(input_dir='output_txt', output_dir='output_mid'):
    """Convert CSV files back to MIDI format"""
    ensure_directories_exist([input_dir, output_dir])

    # Find all potential MIDI bases (either from JSON files or CSV files)
    all_files = os.listdir(input_dir)
    json_files = [f[:-5] for f in all_files if f.endswith('.json')]
    csv_files = [f for f in all_files if f.endswith('.csv')]

    # Add CSV files without corresponding JSON
    csv_bases = set()
    for csv_file in csv_files:
        parts = csv_file.split('_track')
        if len(parts) > 1:
            base_name = parts[0]
            if base_name not in json_files:
                csv_bases.add(base_name)

    # Process each base name
    processed_files = 0

    # First process files with JSON configs
    for base_name in json_files:
        config_path, track_csvs = find_related_files(base_name, input_dir)

        if not config_path or not track_csvs:
            print(f"Missing files for {base_name}, skipping...")
            continue

        # Load the configuration
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config {os.path.basename(config_path)}: {e}")
            continue

        # Create a new MIDI file
        mid = mido.MidiFile(
            ticks_per_beat=config.get('ticks_per_beat', 480),
            type=config.get('type', 1)
        )

        # Extract time signature and tempo
        numerator = config.get('time_signature', {}).get('numerator', 4)
        denominator = config.get('time_signature', {}).get('denominator', 4)
        tempo = config.get('tempo', 500000)

        # Sort tracks by track number for correct ordering
        track_csvs = sorted(track_csvs, key=extract_track_number)

        # Process each track CSV
        for csv_filename in track_csvs:
            csv_path = os.path.join(input_dir, csv_filename)

            # Extract track name from filename
            track_parts = csv_filename.split('_track')
            if len(track_parts) > 1 and '_' in track_parts[1]:
                track_name = track_parts[1].split('_', 1)[1].replace('_', ' ').replace('.csv', '')
            else:
                track_name = f"Track {extract_track_number(csv_filename)}"

            # Create track
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Add track name meta event
            track.append(mido.MetaMessage('track_name', name=track_name, time=0))

            # Load CSV data
            try:
                with open(csv_path, 'r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    events = list(reader)
            except Exception as e:
                print(f"Error loading CSV {csv_filename}: {e}")
                continue

            # Sort by position (bar, beat, tick)
            events.sort(key=lambda x: (
                int(float(x.get('Bar', 0))),
                int(float(x.get('Beat', 0))),
                int(float(x.get('Tick', 0)))
            ))

            # First, collect all note on/off events
            note_events = []
            meta_events = []
            control_events = []

            for event in events:
                event_type = event.get('Type', '')

                if event_type == 'Note':
                    # Create note_on event
                    try:
                        note = int(float(event.get('Note', 0)))
                        velocity = int(float(event.get('Velocity', 64)))
                        channel = int(float(event.get('Channel', 0)))

                        # Get position
                        bar = int(float(event.get('Bar', 1)))
                        beat = int(float(event.get('Beat', 1)))
                        tick = int(float(event.get('Tick', 0)))

                        # Calculate tick position
                        position = {
                            'bar': bar,
                            'beat': beat,
                            'tick': tick
                        }

                        abs_time = musical_time_to_ticks(
                            position,
                            mid.ticks_per_beat,
                            numerator,
                            denominator
                        )

                        # Add note_on
                        note_events.append({
                            'time': abs_time,
                            'msg': mido.Message('note_on', note=note, velocity=velocity, channel=channel),
                            'absolute_time': abs_time
                        })

                        # Calculate note_off time
                        duration = int(float(event.get('Duration_Ticks', 0)))
                        note_off_time = abs_time + duration

                        # Add note_off
                        note_events.append({
                            'time': note_off_time,
                            'msg': mido.Message('note_off', note=note, velocity=0, channel=channel),
                            'absolute_time': note_off_time
                        })
                    except (ValueError, TypeError) as e:
                        print(f"Error processing note event in {csv_filename}: {e}")
                        continue

                elif event_type.startswith('Meta_'):
                    # Handle meta events
                    meta_type = event_type.replace('Meta_', '')
                    value = event.get('Value', '')

                    try:
                        # Position calculation
                        bar = int(float(event.get('Bar', 1)))
                        beat = int(float(event.get('Beat', 1)))
                        tick = int(float(event.get('Tick', 0)))

                        abs_time = musical_time_to_ticks(
                            {'bar': bar, 'beat': beat, 'tick': tick},
                            mid.ticks_per_beat,
                            numerator,
                            denominator
                        )

                        # Create proper meta event based on type
                        if meta_type == 'set_tempo':
                            try:
                                meta_msg = mido.MetaMessage('set_tempo', tempo=int(float(value)))
                            except (ValueError, TypeError):
                                continue
                        elif meta_type == 'time_signature':
                            # Parse time signature string like "4/4"
                            if '/' in str(value):
                                parts = str(value).split('/')
                                if len(parts) == 2:
                                    try:
                                        num, denom = int(parts[0]), int(parts[1])
                                        meta_msg = mido.MetaMessage('time_signature',
                                                                    numerator=num,
                                                                    denominator=denom)
                                    except (ValueError, TypeError):
                                        continue
                                else:
                                    continue
                            else:
                                continue
                        elif meta_type in ['track_name', 'text', 'lyrics']:
                            meta_msg = mido.MetaMessage(meta_type, text=str(value))
                        elif meta_type == 'end_of_track':
                            meta_msg = mido.MetaMessage('end_of_track')
                        else:
                            # Skip unsupported meta types
                            continue

                        meta_events.append({
                            'time': abs_time,
                            'msg': meta_msg,
                            'absolute_time': abs_time
                        })
                    except (ValueError, TypeError) as e:
                        print(f"Error processing meta event in {csv_filename}: {e}")
                        continue

                elif event_type in ['control_change', 'program_change', 'pitch_bend']:
                    # Handle controller events
                    try:
                        channel = int(float(event.get('Channel', 0)))
                        value = int(float(event.get('Value', 0)))

                        # Position calculation
                        bar = int(float(event.get('Bar', 1)))
                        beat = int(float(event.get('Beat', 1)))
                        tick = int(float(event.get('Tick', 0)))

                        abs_time = musical_time_to_ticks(
                            {'bar': bar, 'beat': beat, 'tick': tick},
                            mid.ticks_per_beat,
                            numerator,
                            denominator
                        )

                        if event_type == 'control_change':
                            controller = int(float(event.get('Controller', 0)))
                            msg = mido.Message('control_change', channel=channel,
                                               control=controller, value=value)
                        elif event_type == 'program_change':
                            msg = mido.Message('program_change', channel=channel, program=value)
                        elif event_type == 'pitch_bend':
                            msg = mido.Message('pitch_bend', channel=channel, pitch=value)
                        else:
                            continue

                        control_events.append({
                            'time': abs_time,
                            'msg': msg,
                            'absolute_time': abs_time
                        })
                    except (ValueError, TypeError) as e:
                        print(f"Error processing control event in {csv_filename}: {e}")
                        continue

            # Combine all events and sort by time
            all_events = note_events + meta_events + control_events
            all_events.sort(key=lambda x: x['time'])

            # Convert absolute times to delta times
            previous_time = 0
            for event in all_events:
                delta_time = event['time'] - previous_time
                event['msg'].time = delta_time
                previous_time = event['time']
                track.append(event['msg'])

            # End of track marker if not already added
            has_eot = any(e['msg'].type == 'end_of_track' for e in all_events)
            if not has_eot:
                track.append(mido.MetaMessage('end_of_track', time=0))

        # Save the MIDI file
        midi_filename = config.get('filename', f"{base_name}.mid")
        midi_path = os.path.join(output_dir, midi_filename)

        try:
            mid.save(midi_path)
            print(f"Converted {os.path.basename(config_path)} and its CSV tracks to {midi_filename}")
            processed_files += 1
        except Exception as e:
            print(f"Error saving {midi_filename}: {e}")

    # Now handle CSV files without JSON configs
    for base_name in csv_bases:
        # Find all related CSVs
        related_csvs = [f for f in csv_files if f.startswith(base_name + '_track')]

        if not related_csvs:
            continue

        # Create default MIDI configuration
        mid = mido.MidiFile(ticks_per_beat=480, type=1)

        # Sort tracks by track number
        related_csvs = sorted(related_csvs, key=extract_track_number)

        # Process each CSV file
        for csv_filename in related_csvs:
            csv_path = os.path.join(input_dir, csv_filename)

            # Extract track name and number
            track_number = extract_track_number(csv_filename)
            track_name_parts = csv_filename.replace('.csv', '').split('_')
            if len(track_name_parts) > 2:
                track_name = '_'.join(track_name_parts[2:]).replace('_', ' ')
            else:
                track_name = f"Track {track_number}"

            # Create track
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Add track name
            track.append(mido.MetaMessage('track_name', name=track_name, time=0))

            # Load CSV data
            try:
                with open(csv_path, 'r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    events = list(reader)
            except Exception as e:
                print(f"Error loading CSV {csv_filename}: {e}")
                continue

            # Default time signature and tempo
            numerator, denominator = 4, 4

            # Extract events (similar to above)
            note_events = []
            control_events = []
            meta_events = []

            for event in events:
                event_type = event.get('Type', '')

                if event_type == 'Note':
                    try:
                        note = int(float(event.get('Note', 0)))
                        velocity = int(float(event.get('Velocity', 64)))
                        channel = int(float(event.get('Channel', 0)))

                        # Get position - parse from Position field if available
                        if 'Position' in event and event['Position']:
                            try:
                                pos_parts = event['Position'].split('.')
                                bar = int(pos_parts[0])
                                beat = int(pos_parts[1])
                                tick = int(pos_parts[2]) if len(pos_parts) > 2 else 0
                            except:
                                # Fallback to separate fields
                                bar = int(float(event.get('Bar', 1)))
                                beat = int(float(event.get('Beat', 1)))
                                tick = int(float(event.get('Tick', 0)))
                        else:
                            bar = int(float(event.get('Bar', 1)))
                            beat = int(float(event.get('Beat', 1)))
                            tick = int(float(event.get('Tick', 0)))

                        position = {'bar': bar, 'beat': beat, 'tick': tick}
                        abs_time = musical_time_to_ticks(
                            position,
                            mid.ticks_per_beat,
                            numerator,
                            denominator
                        )

                        # Add note_on
                        note_events.append({
                            'time': abs_time,
                            'msg': mido.Message('note_on', note=note, velocity=velocity, channel=channel),
                            'absolute_time': abs_time
                        })

                        # Calculate note_off time
                        if 'Duration_Ticks' in event and event['Duration_Ticks']:
                            duration = int(float(event.get('Duration_Ticks', 0)))
                        else:
                            duration = mid.ticks_per_beat  # Default to quarter note

                        note_off_time = abs_time + duration

                        # Add note_off
                        note_events.append({
                            'time': note_off_time,
                            'msg': mido.Message('note_off', note=note, velocity=0, channel=channel),
                            'absolute_time': note_off_time
                        })
                    except Exception as e:
                        print(f"Error processing note in {csv_filename}: {e}")
                        continue

                # Handle other message types like in the previous loop...

            # Combine and sort events
            all_events = note_events + control_events + meta_events
            all_events.sort(key=lambda x: x['time'])

            # Convert to delta times
            previous_time = 0
            for event in all_events:
                delta_time = event['time'] - previous_time
                event['msg'].time = delta_time
                previous_time = event['time']
                track.append(event['msg'])

            # Add end of track
            has_eot = any(e['msg'].type == 'end_of_track' for e in all_events)
            if not has_eot:
                track.append(mido.MetaMessage('end_of_track', time=0))

        # Save MIDI file
        midi_filename = f"{base_name}.mid"
        midi_path = os.path.join(output_dir, midi_filename)

        try:
            mid.save(midi_path)
            print(f"Converted CSV tracks for {base_name} to {midi_filename}")
            processed_files += 1
        except Exception as e:
            print(f"Error saving {midi_filename}: {e}")

    if processed_files == 0:
        print("No files were converted to MIDI. Check that CSV files are in the correct format.")
    else:
        print(f"Successfully converted {processed_files} MIDI files.")


def main():
    """Main function to orchestrate the conversions"""
    # Define directories
    input_mid_dir = 'input_mid'
    input_txt_dir = 'input_txt'
    output_txt_dir = 'output_txt'
    output_mid_dir = 'output_mid'

    # Ensure all directories exist
    ensure_directories_exist([input_mid_dir, input_txt_dir, output_txt_dir, output_mid_dir])

    print("\n=== MIDI to CSV Conversion ===")
    midi_to_text(input_mid_dir, input_txt_dir)

    print("\n=== CSV to MIDI Conversion ===")
    text_to_midi(output_txt_dir, output_mid_dir)

    print("\nAll conversions completed!")


if __name__ == "__main__":
    try:
        print("MIDI <-> CSV Converter")
        print("====================")
        print("This script converts MIDI files to editable CSV format and back.")
        print("- Place MIDI files in 'input_mid' folder to convert to CSV")
        print("- Place edited CSV files in 'output_txt' folder to convert back to MIDI")
        print("- Musical positions are shown in bar.beat.tick format\n")

        main()
    except Exception as e:
        print(f"\nError: {e}")
        print("The program encountered an unexpected error.")
        sys.exit(1)
