import { Component, ElementRef, Input, ViewChild, OnInit, OnDestroy, AfterViewInit, EventEmitter, Output } from '@angular/core';
import { OnChanges, SimpleChanges } from '@angular/core';
import { MidiEvent } from '../models/midi-event.model';
import { TileEvent } from '../models/tile-event.model';

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

  private ctx!: CanvasRenderingContext2D;
  private animationId: number = 0;

  basePixelsPerSecond: number = 200; // Pixels to scroll per second

  private colourPalette = [
    "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF",
    "#33FFF6", "#FF8633", "#33FF86", "#8633FF", "#FF3386",
    "#86FF33", "#3386FF", "#FFB533", "#B5FF33", "#33B5FF",
    "#FF33B5", "#B533FF", "#33FFB5", "#FF6F33", "#6FFF33"
  ]
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
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
    this.canvasWidth = this.viewportWidth;
    this.canvasHeight = this.viewportHeight;
  }

  ngAfterViewInit() {
    this.initCanvas();
    this.drawContent();
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

    ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);

    // Draw piano roll background grid
    this.drawGrid();

    this.ctx.fillStyle = 'red';
    this.ctx.fillRect(10, 10, 100, 100);

    // Draw piano tiles (example)
    if (this.TileData.length > 0) { // Do not draw tiles if there are no tiles
      this.drawPianoTiles();
    }
  }

  private drawGrid() {
    const ctx = this.ctx;
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;

    // Horizontal time lines (every beat/measure)
    for (let y = 0; y < this.canvasHeight; y += 100) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvasWidth, y);
      ctx.stroke();
    }

    // Vertical lines for piano keys (88 keys standard piano)
    const keyWidth = this.canvasWidth / 88;
    for (let x = 0; x < this.canvasWidth; x += keyWidth) {
      ctx.strokeStyle = this.isBlackKey(x / keyWidth) ? '#555' : '#333';
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvasHeight);
      ctx.stroke();
    }
  }

  private isBlackKey(keyIndex: number): boolean {
    // Standard piano black key pattern: C C# D D# E F F# G G# A A# B
    const pattern = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]; // 0=white, 1=black
    return pattern[Math.floor(keyIndex) % 12] === 1;
  }

  private drawPianoTiles() { 
    // This function draws the piano tiles based on the currentTime
    const ctx = this.ctx;
    const keyWidth = this.canvasWidth / 88; // 88 piano keys

    // Example falling piano tiles (vertical bars)
    //{ key: 40, startY: 100, length: 200, color: '#4CAF50', velocity: 80 },  // Middle C area
    const tiles = [];
    const window_ms = this.canvasHeight / (this.basePixelsPerSecond * this.playbackMultiplier) * 1000; // Window size in milliseconds
    for (const tile of this.TileData) {
      if (tile.note_number == undefined || tile.note_number < 0 || tile.note_number >= 88) {
        console.warn(`Skipping tile with invalid note number: ${tile.note_number}`);
        continue; // Skip invalid note numbers
      }
      if (tile.start == undefined || tile.start < 0 || tile.end < tile.start) {
        console.warn(`Skipping tile with invalid time range: start=${tile.start}, end=${tile.end}`);
        continue; // Skip tiles with invalid time ranges
      }
      if (tile.velocity == undefined || tile.velocity < 0 || tile.velocity > 127) {
        console.warn(`Skipping tile with invalid velocity: ${tile.velocity}`);
        continue; // Skip tiles with invalid velocity
      }
      if (tile.track == undefined || tile.track < 0) {
        console.warn(`Skipping tile with invalid track: ${tile.track}`);
        continue; // Skip tiles with invalid track
      }
      // Current time is the line onto which the tiles fall
      //  --- (start of tile occurs when tile.start + window_ms < this.currentTime)
      
      //gap = this.window_ms large
    
      // ---------------------------------- (end of tile passes the line: tile.end > this.currentTime)
      if (tile.start + window_ms < this.currentTime || tile.end > this.currentTime) {
        continue; // Skip tiles that are not currently active
      }
      const startY = Math.round((this.currentTime - tile.start) / 1000 * this.basePixelsPerSecond * this.playbackMultiplier);
      if (startY < 0 || startY > this.canvasHeight) {
        console.error(`Error: Skipping tile with out-of-bounds startY: ${startY}`);
        continue; // Skip tiles that would be drawn out of bounds
      }

      tiles.push({
        key: tile.note_number,
        startY: startY,
        length: -Math.round((tile.end - tile.start) / 1000 * this.basePixelsPerSecond * this.playbackMultiplier), //negative so that the tile is drawn upwards
        color: this.colourPalette[tile.track % this.colourPalette.length],
        velocity: tile.velocity
      });
    }

    tiles.forEach(tile => {
      const x = tile.key * keyWidth;
      const width = keyWidth - 2; // Small gap between keys
      //console.log(`Drawing tile at key ${tile.key}, startY ${tile.startY}, length ${tile.length}, color ${tile.color}, velocity ${tile.velocity}`);
      // Create gradient based on velocity (louder = brighter)
      const alpha = tile.velocity / 127;
      const gradient = ctx.createLinearGradient(x, tile.startY, x, tile.startY + tile.length);
      const rgb = this.hexToRgb(tile.color);
      gradient.addColorStop(0, `rgba(${rgb.r},${rgb.g},${rgb.b},${alpha})`);
      // Fade out at bottom using RGB and alpha
      gradient.addColorStop(1, `rgba(${rgb.r},${rgb.g},${rgb.b},0.25)`);

      // Draw the falling tile (vertical bar)
      ctx.fillStyle = gradient;
      ctx.fillRect(x, tile.startY, width, tile.length);

      // Add border for definition
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.strokeRect(x, tile.startY, width, tile.length);

      // Add highlight at top (note attack)
      ctx.fillStyle = '#ffffff80';
      ctx.fillRect(x, tile.startY, width, 3);
    });
  }
}
