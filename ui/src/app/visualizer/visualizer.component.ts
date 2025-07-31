import { Component, OnInit, OnDestroy, ViewChild, ElementRef, Input } from '@angular/core';
import { WebsocketService } from '../services/websocket.service';
import { Subscription } from 'rxjs';
import { MidiEvent } from '../models/midi-event.model';

interface Note {
  note: number;
  startTime: number;
  endTime: number;
  velocity: number;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  isActive: boolean;
}

@Component({
  selector: 'midi-falling-tiles',
  imports: [],
  templateUrl: './visualizer.component.html',
  styleUrls: ['./visualizer.component.css']
})
export class MidiFallingTilesComponent implements OnInit, OnDestroy {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;
  @Input() midiData: MidiEvent[] = [];
  @Input() currentTime: number = 0;
  private ctx!: CanvasRenderingContext2D;
  private animationFrameId: number = 0;
  private notes: Note[] = [];
  private activeNotes = new Set<number>();
  
  // Subscriptions
  private subscriptions: Subscription[] = [];
  
  // Component state
  isConnected = false;
  
  // Canvas properties
  canvasWidth = 1200;
  canvasHeight = 800;
  
  // Piano roll properties
  private readonly PIANO_HEIGHT = 100;
  private readonly NOTE_WIDTH = 14;
  private readonly WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11];
  private readonly BLACK_KEYS = [1, 3, 6, 8, 10];
  private readonly OCTAVES = 8;
  private readonly LOWEST_NOTE = 21;
  private readonly HIGHEST_NOTE = 108;
  
  // Animation properties
  private readonly PIXELS_PER_SECOND = 150;
  private readonly LOOKAHEAD_TIME = 8000;

  constructor(
    private socketService: WebsocketService
  ) {}

  ngOnInit() {
    this.initCanvas();
    this.processNotes();
    this.startAnimation();
  }

  ngOnDestroy() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }
    
    // Unsubscribe from all subscriptions
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  private initCanvas() {
    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d')!;
    
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    
    this.canvasWidth = rect.width;
    this.canvasHeight = rect.height;
  }

  private processNotes() {
    const noteMap = new Map<number, { startTime: number, velocity: number }>();
    const processedNotes: Note[] = [];
    
    this.midiData.forEach(event => {
      const note = event.note || this.simulateNoteFromEvent(event);
      
      if (event.type === 'note_on' && event.velocity > 0) {
        noteMap.set(note, {
          startTime: event.timestamp,
          velocity: event.velocity
        });
      } else if (event.type === 'note_off' || (event.type === 'note_on' && event.velocity === 0)) {
        const noteStart = noteMap.get(note);
        if (noteStart) {
          const processedNote: Note = {
            note: note,
            startTime: noteStart.startTime,
            endTime: event.timestamp,
            velocity: noteStart.velocity,
            x: this.getNoteX(note),
            y: 0,
            width: this.getNoteWidth(note),
            height: 0,
            color: this.getNoteColor(note, noteStart.velocity),
            isActive: false
          };
          processedNotes.push(processedNote);
          noteMap.delete(note);
        }
      }
    });
    
    this.notes = processedNotes;
  }

  private simulateNoteFromEvent(event: MidiEvent): number {
    const baseNote = 60;
    const noteIndex = Math.floor(event.timestamp / 169.4915) % 12;
    return baseNote + noteIndex;
  }

  private getNoteX(note: number): number {
    const octave = Math.floor((note - this.LOWEST_NOTE) / 12);
    const noteInOctave = (note - this.LOWEST_NOTE) % 12;
    
    if (this.WHITE_KEYS.includes(noteInOctave)) {
      const whiteKeyIndex = this.WHITE_KEYS.indexOf(noteInOctave);
      return octave * (this.NOTE_WIDTH * 7) + whiteKeyIndex * this.NOTE_WIDTH;
    } else {
      const blackKeyPositions = [0.5, 1.5, 3.5, 4.5, 5.5];
      const blackKeyIndex = this.BLACK_KEYS.indexOf(noteInOctave);
      return octave * (this.NOTE_WIDTH * 7) + blackKeyPositions[blackKeyIndex] * this.NOTE_WIDTH;
    }
  }

  private getNoteWidth(note: number): number {
    const noteInOctave = (note - this.LOWEST_NOTE) % 12;
    return this.WHITE_KEYS.includes(noteInOctave) ? this.NOTE_WIDTH : this.NOTE_WIDTH * 0.6;
  }

  private getNoteColor(note: number, velocity: number): string {
    const noteInOctave = (note - this.LOWEST_NOTE) % 12;
    const intensity = Math.floor((velocity / 127) * 255);
    
    if (this.WHITE_KEYS.includes(noteInOctave)) {
      return `rgba(${intensity}, ${intensity}, 255, 0.8)`;
    } else {
      return `rgba(255, ${intensity}, ${intensity}, 0.8)`;
    }
  }

  private startAnimation() {
    const animate = () => {
      this.draw();
      this.animationFrameId = requestAnimationFrame(animate);
    };
    animate();
  }

  private draw() {
    this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
    this.drawNotes();
    this.drawActiveNoteHighlights();
  }

  private drawNotes() {
    const pianoY = this.canvasHeight - this.PIANO_HEIGHT;
    
    this.notes.forEach(note => {
      const noteStartY = pianoY - ((note.startTime - this.currentTime) / 1000) * this.PIXELS_PER_SECOND;
      const noteEndY = pianoY - ((note.endTime - this.currentTime) / 1000) * this.PIXELS_PER_SECOND;
      
      if (noteEndY > -50 && noteStartY < this.canvasHeight + 50) {
        const noteHeight = Math.max(noteStartY - noteEndY, 2);
        
        // Check if note is currently active
        const isCurrentlyActive = this.currentTime >= note.startTime && this.currentTime <= note.endTime;
        let color = note.color;
        
        if (isCurrentlyActive || this.activeNotes.has(note.note)) {
          color = color.replace('0.8)', '1.0)');
          // Add glow effect for active notes
          this.ctx.shadowColor = color;
          this.ctx.shadowBlur = 15;
        } else {
          this.ctx.shadowBlur = 0;
        }
        
        // Create gradient for note
        const gradient = this.ctx.createLinearGradient(note.x, noteEndY, note.x + note.width, noteEndY);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, color.replace('0.8)', '0.6)'));
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(note.x, noteEndY, note.width, noteHeight);
        
        // Add border
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(note.x, noteEndY, note.width, noteHeight);
        
        this.ctx.shadowBlur = 0;
      }
    });
  }

  // Removed: drawTimeLine (progress bar/timeline)

  private drawActiveNoteHighlights() {
    this.activeNotes.forEach(note => {
      const x = this.getNoteX(note);
      const width = this.getNoteWidth(note);
      const pianoY = this.canvasHeight - this.PIANO_HEIGHT;
      
      // Draw a bright line above the piano key
      this.ctx.strokeStyle = '#ffff00';
      this.ctx.lineWidth = 4;
      this.ctx.shadowColor = '#ffff00';
      this.ctx.shadowBlur = 8;
      this.ctx.beginPath();
      this.ctx.moveTo(x, pianoY - 5);
      this.ctx.lineTo(x + width, pianoY - 5);
      this.ctx.stroke();
      this.ctx.shadowBlur = 0;
    });
  }

  formatTime(timeMs: number): string {
    const seconds = Math.floor(timeMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
}