export interface MidiEvent {
  timestamp: number;
  deltaT: number;
  type: 'note_on' | 'note_off';
  velocity: number;
  isBounceBack: boolean;
  note: number;
  channel: number;
}