export interface TileEvent {
    note_number: number; // 0-indexed note number
    start: number; // Start time in milliseconds
    end: number; // End time in milliseconds
    velocity: number; // Velocity of the note
    track: number; // Track number
}