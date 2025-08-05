import { Component, ElementRef, Input, ViewChild, OnInit, OnDestroy, AfterViewInit, EventEmitter, Output } from '@angular/core';
import { OnChanges, SimpleChanges } from '@angular/core';
import { MidiEvent } from '../models/midi-event.model';
import { TileEvent } from '../models/tile-event.model';
import { DEFAULT_NOTE_COLORS } from '../models/note-colors.model';
import { environment } from '../../environments/environment';

interface TileToDraw {
  key: number;
  startY: number;
  length: number; // Length of the tile in pixels
  color: string; // Color of the tile
  velocity: number; // Velocity of the note
}

@Component({
  selector: 'tile-canvas',
  imports: [],
  templateUrl: './canvas.component.html',
  styleUrl: './canvas.component.css'
})
export class ScrollableCanvasComponent implements OnInit, AfterViewInit, OnDestroy, OnChanges {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('viewport', { static: true }) viewportRef!: ElementRef<HTMLDivElement>;
  @ViewChild('canvasContainer', { static: true }) containerRef!: ElementRef<HTMLDivElement>;

  @Input() MidiData: MidiEvent[] = [];
  @Input() TileData: TileEvent[] = [];
  @Input() currentTime: number = 0;
  @Input() playbackMultiplier: number = 1; // Speed multiplier for playback

  @Output() tileStateChanged = new EventEmitter<{ noteNumber: number, state: boolean, track: number }>();

  private ctx!: CanvasRenderingContext2D;
  private TilesToDraw: TileToDraw[] = [];
  basePixelsPerSecond: number = 200; // Pixels to scroll per second


  canvasWidth = 0;
  canvasHeight = 0;

  // Viewport dimensions
  viewportWidth = 0;
  viewportHeight = 0;

  // Current scroll position
  offsetX = 0;
  offsetY = 0;
  // Auto-scroll state
  isAutoScrolling = false;
  private autoScrollSpeed = 2; // pixels per frame

  ngOnInit() {
    this.canvasWidth = environment.pianoWidth;
    this.canvasHeight = environment.canvasHeight;
  }

  ngAfterViewInit() {
    this.initCanvas();
    this.drawContent();
    //this.drawTestTiles(); // Draw test tiles for debugging
    //console.log(this.keyPosition()); //print out the key positions
  }

  ngOnDestroy() {
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['TileData'] || changes['currentTime']) {
      this.drawContent(); // Redraw content when TileData changes
    }
  }

  private initCanvas() {
    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d')!;

    // Set canvas size to full content size
    canvas.width = this.canvasWidth;
    canvas.height = this.canvasHeight;
  }
  private hexToRgb(hex: string): { r: number, g: number, b: number } {
    hex = hex.replace('#', '');
    const bigint = parseInt(hex, 16);
    return {
      r: (bigint >> 16) & 255,
      g: (bigint >> 8) & 255,
      b: bigint & 255
    };
  }
  private drawContent() {
    if (!this.ctx) return; // Prevent errors if context is not ready
    const ctx = this.ctx;

    ctx.setTransform(1, 0, 0, -1, 0, this.canvasHeight);
    ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);

    // Draw piano tiles (example)
    if (this.TileData.length > 0) { // Do not draw tiles if there are no tiles
      this.generatePianoTiles();
      this.drawPianoTiles();
    }
  }

  private isBlackKey(keyIndex: number): boolean {
    // Standard piano black key pattern: C C# D D# E F F# G G# A A# B
    const pattern = [0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1]; // 0=white, 1=black
    return pattern[Math.floor(keyIndex) % 12] === 1;
  }
  private keyPosition(): number[] {
    const whiteKeyWidth = environment.whiteKeyWidth;
    const blackKeyWidth = environment.blackKeyWidth;
    let positions: number[] = [];
    for (let i = 0; i < 88; i++) {
      if (i == 0) {
        positions.push(0); // First key starts at 0
      } else {
        const prevKey = i - 1;
        const prevIsBlack = this.isBlackKey(prevKey);
        // 3 cases to consider: 
        // 1. Previous is white, current is white
        // 2. Previous is white, current is black
        // 3. Previous is black current is white
        if (!prevIsBlack) {
          if (!this.isBlackKey(i)) { //1. 
            positions.push(positions[prevKey] + whiteKeyWidth);
          } else { // 2.
            positions.push(positions[prevKey] + whiteKeyWidth - blackKeyWidth / 2);
          }
        } else { // 3
          positions.push(positions[prevKey] + blackKeyWidth / 2); // White key
        }
      }
    }
    // Return the calculated position for the given keyIndex
    return positions;
  }

  private checkTile(tile: TileEvent): boolean { //Check if the tile is valid
    if (tile.note_number == undefined || tile.note_number < environment.lowestNote || tile.note_number >= environment.highestNote) {
      console.warn(`Skipping tile with invalid note number: ${tile.note_number}`);
      return false;
    }
    if (tile.start == undefined || tile.start < 0 || tile.end <= tile.start) {
      console.warn(`Skipping tile with invalid time range: start=${tile.start}, end=${tile.end}`);
      return false;
    }
    if (tile.velocity == undefined || tile.velocity < 0 || tile.velocity > 127) {
      console.warn(`Skipping tile with invalid velocity: ${tile.velocity}`);
      return false;
    }
    if (tile.track == undefined || tile.track < 0) {
      console.warn(`Skipping tile with invalid track: ${tile.track}`);
      return false;
    }
    return true; // Tile is valid
  }

  // It is of utmost importance that we draw all the white tiles first and then the black tiles on top of them.
  private drawTestTiles() {
    const whiteHeight = 100;
    const blackHeight = 50;

    for (let i = 0; i < 88; i++) {
      const isBlack = this.isBlackKey(i);
      if (isBlack) continue; // Skip black keys in this loop
      const color = '#fff';
      const height = whiteHeight; // Black keys are shorter
      const y = 0; // Position black keys higher
      const keyWidth = environment.whiteKeyWidth; // Use appropriate key width
      this.ctx.fillStyle = color;
      this.ctx.fillRect(environment.keyPositions[i], y, keyWidth - 2, height); // Draw key with a small gap
    }
    for (let i = 0; i < 88; i++) {
      const isBlack = this.isBlackKey(i);
      if (!isBlack) continue; // Skip white keys in this loop
      const color = '#000';
      const height = blackHeight; // Black keys are shorter
      const y = 50; // Position black keys higher
      const keyWidth = environment.blackKeyWidth; // Use appropriate key width
      this.ctx.fillStyle = color;
      this.ctx.fillRect(environment.keyPositions[i], y, keyWidth - 2, height); // Draw key with a small gap
    }
  }

  private generatePianoTiles(): void {
    this.TilesToDraw = []; // Clear previous tiles
    for (const tile of this.TileData) {
      const window_ms = this.canvasHeight / (this.basePixelsPerSecond * this.playbackMultiplier) * 1000; // Window size in milliseconds
      var tile_start_position = tile.start - this.currentTime; // Position relative to current time
      var tile_end_position = tile.end - this.currentTime; // Position relative to current time

      if (!this.checkTile(tile)) {
        continue; // Skip invalid tiles
      }

      // Current time is the line onto which the tiles fall
      //  --- (start of tile occurs when tile.start + window_ms < this.currentTime)

      //gap = this.window_ms large

      // ---------------------------------- (end of tile passes the line: tile.end > this.currentTime)
      if (tile_start_position > window_ms) { //the tile is above the active window
        continue;
      }
      if (tile_end_position < 0) { //the tile is below the active window and has been released
        this.tileStateChanged.emit({ noteNumber: tile.note_number, state: false, track: tile.track });
      }
      if (tile_start_position == 0) {
        this.tileStateChanged.emit({ noteNumber: tile.note_number, state: true, track: tile.track });
      }
      if (tile_start_position < 0) { 
        tile_start_position = 0; // Adjust start position if it falls before the current time
      }
      if (tile_end_position > window_ms) {
        tile_end_position = window_ms; // Adjust end position if it exceeds the window size
      }
      const startY = Math.round(tile_start_position / 1000 * this.basePixelsPerSecond * this.playbackMultiplier);
      if (startY < 0 || startY > this.canvasHeight) {
        console.error(`Error: Skipping tile with out-of-bounds startY: ${startY}`);
        continue; // Skip tiles that would be drawn out of bounds
      }

      this.TilesToDraw.push({
        key: tile.note_number,
        startY: startY,
        length: Math.round((tile_end_position - tile_start_position) / 1000 * this.basePixelsPerSecond * this.playbackMultiplier), //negative so that the tile is drawn upwards
        color: DEFAULT_NOTE_COLORS[tile.track % DEFAULT_NOTE_COLORS.length],
        velocity: tile.velocity
      });
    }
    this.TilesToDraw.sort((a, b) => this.isBlackKey(a.key) ? 1 : (this.isBlackKey(b.key) ? -1 : 0)); // Sort tiles so that black keys are drawn on top of white keys
  }

  // It is of utmost importance that we draw all the white tiles first and then the black tiles on top of them.
  private drawPianoTiles() {
    // This function draws the piano tiles based on the currentTime
    const ctx = this.ctx;
    const keyWidth = this.canvasWidth / 88; // 88 piano keys

    //{ key: 40, startY: 100, length: 200, color: '#4CAF50', velocity: 80 },  // Middle C area
    const tiles = this.TilesToDraw;

    // Actually draw the tiles
    tiles.forEach(tile => {
      const noteIndex = tile.key - environment.lowestNote; // Adjust for lowest note
      if (noteIndex < 0 || noteIndex >= 88) {
        console.warn(`Skipping tile with out-of-bounds key: ${tile.key}`);
        return; // Skip tiles that are out of bounds
      }
      const isBlackKey = this.isBlackKey(noteIndex);
      const x = environment.keyPositions[noteIndex];
      const width = (isBlackKey ? environment.blackKeyWidth : environment.whiteKeyWidth) - 2;

      // Create gradient based on velocity (louder = brighter)
      const alpha = Math.max(0.7, tile.velocity / 127); // Ensure minimum visibility
      const rgb = this.hexToRgb(tile.color);

      // If black key, darken the color by reducing brightness
      let r = rgb.r, g = rgb.g, b = rgb.b;
      if (isBlackKey) {
        r = Math.floor(r * 0.5);
        g = Math.floor(g * 0.5);
        b = Math.floor(b * 0.5);
      }

      // Add a strong outline for visibility against dark backgrounds
      ctx.save();
      ctx.shadowColor = 'rgba(255,255,255,0.7)';
      ctx.shadowBlur = 8;

      const gradient = ctx.createLinearGradient(x, tile.startY, x, tile.startY + tile.length);
      gradient.addColorStop(0, `rgba(${r},${g},${b},${alpha})`);
      gradient.addColorStop(1, `rgba(${r},${g},${b},0.35)`);

      // Draw the falling tile (vertical bar)
      ctx.fillStyle = gradient;
      ctx.fillRect(x, tile.startY, width, tile.length);

      ctx.restore();

      // Add a white border for extra contrast
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, tile.startY, width, tile.length);
    });
  }
}
