import mido
import json
from typing import List
from midi_events import MidiEvent, ConvertedEvent

"""
This module provides functionality for parsing MIDI files using the mido library.
It defines the MidiParser class, which can:
- Load MIDI files and extract instrument (program) information.
- Parse MIDI tracks into lists of MidiEvent objects, filtered by channels.
- Convert MIDI ticks to milliseconds for accurate timing.
- Export parsed MIDI events to JSON for further processing or playback.

Midi events are read from the midi bytefile and converted into the following data structure to faciliate sanitation: 

EventList {
    "first_note_number" : {
        Event: {
            "tick": int,  # The tick at which the event occurs
            "time_ms": float,  # The time in milliseconds when the event occurs
            "type": str,  # The type of MIDI event (e.g., 'note_on', 'note_off')
            "velocity": int  # The velocity of the note (0-127)
        }
        ...
    }
    ...
    "last_note_number" : {
        Event: {
        ...
        }
    }
}

By grouping events together by note number, we can efficiently make decisions regarding the feasibility of scheduling events on a note-by-note basis.
After we have sanitized the events by running them through our algorithm, we then convert them back into a list of MidiEvent objects for playback:

EventList [
    MidiEvent(deltaT=..., note=..., velocity=...),
    MidiEvent(deltaT=..., note=..., velocity=...),
    ...
    MidiEvent(deltaT=..., note=..., velocity=...)
]
"""

class MidiParser:
    def __init__(self, midi_file: str, settings):
        self.mid = mido.MidiFile(midi_file)
        self.midi_file = midi_file
        self.ticks_per_beat = self.mid.ticks_per_beat
        self.tempo = 500000  # Default tempo (120 BPM)
        self.settings = settings

    def _load_midi(self):
        """Load MIDI file and update the checkboxes for showing the instruments to be selected"""
        self.mid = mido.MidiFile(self.midi_file)
        programs_path = './tmp/tracks.json'
        programs = {}
        for track_idx, track in enumerate(self.mid.tracks):
            for msg in track:
                channel = int(getattr(msg, 'channel', 0))
                if msg.type == 'program_change':
                    # Update mapping of program (instrument name) : channel to ./tmp/instrument_names.json
                    print(f"Program Change Meta Event - Track: {track_idx}, Channel: {channel}, Program: {msg.program}")
                    program = msg.program
                    try:
                        # Append new instrument name
                        programs[channel] = program
                        print(f"Adding program {program} for channel {channel}")
                    except Exception as e:
                        print(f"Error writing to ./instruments.json: {e}")
                elif msg.type == 'set_tempo':
                    # Update tempo if set_tempo message is found
                    self.tempo = msg.tempo
                    print(f"Set Tempo Meta Event - Track: {track_idx}, Tempo: {self.tempo}")
        with open(programs_path, 'w') as f:
            json.dump(programs, f, indent=2)
        print(f"Ticks per beat: {self.ticks_per_beat}, Tempo: {self.tempo}")

    # This function employs the sanitation algorithm that was initially implemented on the ESP32 to check and modify midi commands that were impossible
    def _sanitize_events(self, events: List[List[MidiEvent]]) -> List[List[MidiEvent]]:
        # The general idea is simple: we will iterate through all the notes, within each note iterate through all the events and apply a consistent set of rules 
        # List to hold sanitized events
        sanitized_events = [[] for _ in range(88)] # sanitized events
        note_idx = 0
        for note_number in events:
            isFirstEvent = True
            for event in note_number:
                if isFirstEvent: # If this is the first event for this note, we can just add it to the sanitized events
                    sanitized_events[note_idx].append(event)
                    isFirstEvent = False
                    continue
                lastEvent = sanitized_events[note_idx][-1]
                assert lastEvent is not None, "Last event should not be None when processing subsequent events"
                isLastOn = lastEvent.type == 'note_on' and lastEvent.velocity > 0
                isLastBB = lastEvent.isBounceBack
                isOn = event.type == 'note_on' and event.velocity > 0
                deltaT = event.time_ms - lastEvent.time_ms
                if isLastOn: # If the last event was to turn the note on
                    if isOn: # And now the new command is to turn the note on again
                        assert not isLastBB, "Last event should not be a bounce back when processing a note on event"
                        if deltaT >= self.settings.settings['activation_duration'] + self.settings.settings['deactivation_duration']: # There is sufficient time to schedule a traditional note on and note off
                            noteOffEvent = MidiEvent(
                                tick=lastEvent.tick + self._milliseconds_to_ticks(self.settings.settings['activation_duration']),
                                time_ms=lastEvent.time_ms + self.settings.settings['activation_duration'],
                                type='note_off',
                                velocity=0,
                                track=lastEvent.track,
                                isBounceBack=False
                            )
                            sanitized_events[note_idx].append(noteOffEvent) # Schedule a note off event
                            sanitized_events[note_idx].append(event) # Schedule the event normally
                        elif deltaT >= self.settings.settings['bounce_back_duration']: # If there is time to schedule a bounceback
                            lastEvent.isBounceBack = True # Change the last event to a bounce back event
                            lastEvent.type = 'note_off' # Change the type of the last event to note off
                            sanitized_events[note_idx][-1] = lastEvent # Update the last event to be a bounce back event
                            sanitized_events[note_idx].append(event) # Schedule the event normally
                        else: # There is no time to schedule a bounceback, so we can just ignore this event
                            continue
                    else: # If the last event was to turn the note on, and now the new command is to turn the note off
                        if deltaT < self.settings.settings['bounce_back_duration']:
                            del sanitized_events[note_idx][-1] #delete the activation event because there will be no time
                        else:
                            lastEvent.isBounceBack = True
                            lastEvent.type = 'note_off' # Change the type of the last event to note off
                            sanitized_events[note_idx][-1] = lastEvent # Update the last event to be a bounce back event
                else: # If the last event was to turn the note off
                    if isOn: # And now the new command is to turn the note on
                        if isLastBB: # If the last event was a bounce back event
                            if deltaT < self.settings.settings['bounce_back_duration']: # If the time between the last event and this event is less than the bounce back duration, we can ignore this event
                                continue # Do nothing because a bounce back will not finish in time
                            else:
                                sanitized_events[note_idx].append(event) # Schedule the note to turn on after the bounceback
                        else: # If the last event was not a bounce back event
                            if deltaT < self.settings.settings['deactivation_duration']:
                                lastEvent.isBounceBack = True
                                lastEvent.type = 'note_off' # Change the type of the last event to note off
                                sanitized_events[note_idx][-1] = lastEvent # Update the last event to be a bounce back event
                                # We signify a bounceback using an unused control change event. In this case we use 0xB0 0x6E 0x_ _ (Control Change, Channel 1, Controller 110 [0x6E], Note number __ )
                                # For now we simply modify the isBounceBack attribute of the last event to True. 
                                # We implement the CC event in our player
                            sanitized_events[note_idx].append(event)
                    else: # If the last event was to turn the note off, and now the new command is to turn the note off
                        continue # Do nothing because the note is already off
            note_idx += 1
        return sanitized_events
    # When parse to events is called we would already know the channels that we want to play
    def _generate_tile_data(self, events: List[List[MidiEvent]]) -> List[List[MidiEvent]]:
        """
        Generate tile data for the MIDI events
        The structure of tile_data is as follows:
        tile_data = {
            'Tile': {
                'note_number': note_index,  # The note number (0-88)
                'start': start_time_ms,
                'end': end_time_ms
                'velocity': velocity,
                'track': track_idx,  # Track index for the event
            }
        }
        """
        # This function is used to generate the tile data for the MIDI events.
        midi_tile_data = [] # Initialize a list of lists for each note
        note_index = 0
        for note_events in events: 
            onLastTime = -1 
            for event in note_events: 
                if event.isBounceBack:
                    midi_tile_data.append({
                        'note_number': note_index,
                        'start': event.time_ms,
                        'end': event.time_ms + self.settings.settings['bounce_back_duration'],
                        'velocity': event.velocity,
                        'track': event.track
                    })
                    onLastTime = -1 # Reset onLastTime for bounce back events
                    continue
                if event.type == 'note_on' and event.velocity > 0:
                    if onLastTime != -1:
                        print(f"Error: Note on after note on at {onLastTime} ms for note {note_index}. This is not allowed in MIDI.")
                    onLastTime = event.time_ms
                elif event.type == 'note_off':
                    if onLastTime == -1:
                        print(f"Error: Note off without note on at {event.time_ms} ms for note {note_index}. This is not allowed in MIDI.")
                    else:
                        midi_tile_data.append({
                            'note_number': note_index,
                            'start': onLastTime,
                            'end': event.time_ms,
                            'velocity': event.velocity,
                            'track': event.track
                        })
                        onLastTime = -1
            note_index += 1
        with open(self.settings.settings['midi_tile_data_file_path'], 'w') as f:
            json.dump(midi_tile_data, f, indent=2)
        return 
        return events
    def _parse_to_events(self, tracks_to_play) -> List[List[MidiEvent]]: #We pass in an array of programs (instruments) to play
        """Parse MIDI file into lists of MidiEvent objects per track"""
        print(tracks_to_play)
        all_notes_all_events = [[] for _ in range(self.settings.settings["highest_note"] - self.settings.settings["lowest_note"] + 1)]  # Initialize a list of lists for each note
        for track_idx, track in enumerate(self.mid.tracks):
            # Skip tracks not in the list of tracks to play
            current_tick = 0
            current_tempo = self.tempo
            for msg in track:
                current_tick += msg.time # In all cases we need to increment the current tick by the time of the message, even if we are ignoring the message
                channel = getattr(msg, 'channel', 0)
                if channel not in tracks_to_play: # If the channel is not to be played, skip from here onwards
                    continue
                ms = self._ticks_to_milliseconds(current_tick, current_tempo)
                print(f"Processing message: {msg} at tick {current_tick}, time {ms} ms, channel {channel}, track {track_idx}")
                if not msg.is_meta:
                    # Handle note events
                    note_number = getattr(msg, 'note', None)
                    velocity = getattr(msg, 'velocity', None)
                    event = MidiEvent(
                        tick=current_tick,
                        time_ms=ms,
                        type=msg.type,
                        velocity=velocity,
                        isBounceBack=False,
                        track=track_idx
                    )
                    try:
                        all_notes_all_events[note_number - self.settings.settings["lowest_note"]].append(event) if note_number is not None else None
                    except IndexError as e:
                        print(f"Error when writing to index {note_number - self.settings.settings['lowest_note']}: {e}")
                # Handle tempo changes for timing calculations
                else:
                    if msg.type == 'set_tempo':
                        current_tempo = msg.tempo
                        self.tempo = current_tempo  # Update global tempo

        # For each of the arrays within all_notes_all_events, sort each array in ascending order by time_ms
        for note_events in all_notes_all_events:
            note_events.sort(key=lambda x: x.time_ms)
        return all_notes_all_events
    
    def _milliseconds_to_ticks(self, milliseconds: float, tempo: int = None) -> int:
        """Convert milliseconds to MIDI ticks"""
        if tempo is None:
            tempo = self.tempo
        
        # Calculate time per tick in seconds
        seconds_per_beat = tempo / 1_000_000  # Tempo is in microseconds per beat
        seconds_per_tick = seconds_per_beat / self.ticks_per_beat
        return int(milliseconds / (seconds_per_tick * 1000))
    def _ticks_to_milliseconds(self, ticks: int, tempo: int = None) -> float:
        """Convert MIDI ticks to milliseconds"""
        if tempo is None:
            tempo = self.tempo
        # Calculate time per tick in seconds
        seconds_per_beat = tempo / 1_000_000  # Tempo is in microseconds per beat
        seconds_per_tick = seconds_per_beat / self.ticks_per_beat
        
        return ticks * seconds_per_tick * 1000  # Convert to milliseconds
    def _calculate_duration(self, events: List[MidiEvent]) -> float:
        """Calculate total duration of MIDI file in seconds"""
        if not events:
            return 0.0
        last_event = max(events, key=lambda x: x.timestamp)
        return last_event.timestamp  # Convert to seconds
    
    def _convert_events(self, events: List[List[MidiEvent]]) -> List[MidiEvent]:
        """Convert sanitized events back to a flat list of MidiEvent objects"""
        # We achieve this by iterating over the first elements in the list represent each note and finding the event that happens first. 
        # Then we append that event to our converted events lists and then remove that event from the list of events for that note.
        converted_events = []
        previous_time = 0.0
        while True: # break out of the loop only when an entire pass through the loop does not add any events
            earliest_time = float('inf')
            earliest_event = None
            earliest_event_idx = -1
            for note_events in events:
                current_event = note_events[0] if note_events else None
                if not current_event: # if there are no events for this note, skip
                    continue
                else:
                    if current_event.time_ms < earliest_time:
                        earliest_time = current_event.time_ms
                        earliest_event = current_event
                        earliest_event_idx = events.index(note_events)
            if earliest_event:
                converted_event = ConvertedEvent(
                    timestamp=earliest_event.time_ms,
                    deltaT=earliest_time - previous_time,
                    note=earliest_event_idx+self.settings.settings['lowest_note'],
                    type=earliest_event.type,
                    velocity=earliest_event.velocity,
                    isBounceBack=earliest_event.isBounceBack
                )
                converted_events.append(converted_event)
                events[earliest_event_idx].pop(0)
                previous_time = earliest_time
            if not earliest_event:  # If no earliest event was found, break the loop
                break
        return converted_events
    def _export_to_json_2D(self, events: List[List[MidiEvent]], filepath) -> bool:
        """Export parsed MIDI data to JSON file"""
        try:
            # Convert each event to a dict
            serializable_events = [
                [{"note": note_idx, "data": e.to_dict()} for e in note_events]
                for note_idx, note_events in enumerate(events)
            ]
            with open(filepath, 'w') as f:
                json.dump(serializable_events, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
            
    def _export_to_json_flatlist(self, events: list) -> bool:
        """Export parsed MIDI data to JSON file"""
        try:
            # Convert each event to a dict
            serializable_events = [e.to_dict() for e in events]
            with open(self.settings.settings['midi_json_file_path'], 'w') as f:
                json.dump(serializable_events, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
