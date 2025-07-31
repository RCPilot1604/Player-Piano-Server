import { Component, ElementRef, Input, ViewChild, OnInit, OnDestroy, AfterViewInit } from '@angular/core';
import { OnChanges, SimpleChanges } from '@angular/core';
import { MidiEvent } from '../models/midi-event.model';
import { TileEvent } from '../models/tile-event.model';

@Component({
  selector: 'canvas',
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

  private ctx!: CanvasRenderingContext2D;
  private animationId: number = 0;

  playbackMultiplier: number = 1; // Speed multiplier for playback
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

  // Panning state
  private isPanning = false;
  private lastMouseX = 0;
  private lastMouseY = 0;

  // Auto-scroll state
  isAutoScrolling = false;
  private autoScrollSpeed = 2; // pixels per frame

  ngOnInit() {
    // Check for midi data stored in localStorage
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
    this.canvasWidth = this.viewportWidth;
  }

  ngAfterViewInit() {
    this.initCanvas();
    this.drawContent();
  }

  ngOnDestroy() {
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['TileData']) {
      this.drawContent(); // Redraw content when TileData changes
    }
    if (changes['currentTime']) {
      this.scrollTo(this.currentTime);
    }
  }

  private initCanvas() {
    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d')!;

    // Set canvas size to full content size
    canvas.width = this.canvasWidth;
    canvas.height = this.canvasHeight;
  }

  private drawContent() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);

    // Draw piano roll background grid
    this.drawGrid();

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
    const ctx = this.ctx;
    const keyWidth = this.canvasWidth / 88; // 88 piano keys

    // Example falling piano tiles (vertical bars)
    //{ key: 40, startY: 100, length: 200, color: '#4CAF50', velocity: 80 },  // Middle C area
    const tiles = [];
    for (const tile of this.TileData) {
      tiles.push({
        key: tile.note_number,
        startY: Math.round(tile.start / 1000 * this.basePixelsPerSecond * this.playbackMultiplier),
        length: Math.round((tile.end - tile.start) / 1000 * this.basePixelsPerSecond * this.playbackMultiplier),
        color: this.colourPalette[tile.track % this.colourPalette.length],
        velocity: tile.velocity
      });
    }

    tiles.forEach(tile => {
      const x = tile.key * keyWidth;
      const width = keyWidth - 2; // Small gap between keys

      // Create gradient based on velocity (louder = brighter)
      const alpha = tile.velocity / 127;
      const gradient = ctx.createLinearGradient(x, tile.startY, x, tile.startY + tile.length);
      gradient.addColorStop(0, tile.color + Math.floor(alpha * 255).toString(16).padStart(2, '0'));
      gradient.addColorStop(1, tile.color + '40'); // Fade out at bottom

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

  // Scrolling methods
  scrollTo(time: number) {
    const targetY = time / 1000 * this.basePixelsPerSecond * this.playbackMultiplier;
    this.offsetY = Math.min(0, -targetY);
    this.drawContent();
  }

  resetView() {
    this.offsetX = 0;
    this.offsetY = 0;
  }

  // Method to add new falling piano tile
  addFallingTile(keyIndex: number, startY: number, length: number, color: string, velocity: number = 80) {
    const keyWidth = this.canvasWidth / 88;
    const x = keyIndex * keyWidth;
    const width = keyWidth - 2;

    // Create gradient based on velocity
    const alpha = velocity / 127;
    const gradient = this.ctx.createLinearGradient(x, startY, x, startY + length);
    gradient.addColorStop(0, color + Math.floor(alpha * 255).toString(16).padStart(2, '0'));
    gradient.addColorStop(1, color + '40');

    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(x, startY, width, length);

    this.ctx.strokeStyle = '#fff';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(x, startY, width, length);

    // Highlight at top
    this.ctx.fillStyle = '#ffffff80';
    this.ctx.fillRect(x, startY, width, 3);
  }
}
