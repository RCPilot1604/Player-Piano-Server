import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SongListComponent } from './song-list/song-list.component';
import { MatToolbarRow } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { AddSongDialogComponent } from './add-song-dialog/add-song-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { AddCategoryDialogComponent } from './add-category-dialog/add-category-dialog/add-category-dialog.component';
import { WebsocketService } from './services/websocket.service';
import { ScrollableCanvasComponent } from './canvas/canvas.component';
import { TileEvent } from './models/tile-event.model';
import { environment } from '../environments/environment';
import { MatSliderModule } from '@angular/material/slider';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { DEFAULT_NOTE_COLORS } from './models/note-colors.model';
import { KeyboardComponent } from './keyboard/keyboard.component';
import { ViewChild } from '@angular/core';
import { SongEntry }  from './models/song-entry.model';
import { MidiPort } from './models/port-data.model';

interface StatusEvent {
  isPlaying: boolean;
  currentSong: SongEntry | null;
  volume: number;
  instruments: string[];
  tracksToPlay: number[];
}

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SongListComponent, MatToolbarRow, MatIconModule, MatButtonModule, MatMenuModule, ScrollableCanvasComponent, MatSliderModule, MatInputModule, MatSelectModule, FormsModule, KeyboardComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})

export class AppComponent {
  title = 'ui';
  currentTime = 0;
  totalTime = 0;
  playbarTime = 0; // Time for the playbar
  tileData: TileEvent[] = [];
  playbackMultiplier: number = 1; // Speed multiplier for playback
  keyColors: { key: number, colour: string }[] = []; // Array to hold the colour of each of the notes
  currentSong: SongEntry | null = null; // Current song being played
  isPlaying = false; // Whether the player is currently playing
  volume = 100; // Volume level (0-100)
  instruments: string[] = []; // List of instruments available
  tracksToPlay: number[] = []; // Tracks that are currently set to play
  midiPorts: MidiPort[] = []; // List of available ports
  selectedMidiPort: number | null = null; // Currently selected MIDI port
  constructor(public dialog: MatDialog, private socket: WebsocketService) { }

  @ViewChild(SongListComponent) songListComponent!: SongListComponent;
  onMidiPortChange() {
    console.log(`Selected MIDI port: ${this.selectedMidiPort}`);
    this.socket.emit('selectPort', this.selectedMidiPort);
  }
  refreshMidiPorts() {
    console.log('Refreshing MIDI ports');
    this.socket.emit('refreshPorts', '');
  }
  openAddSongDialog(): void {
    const dialogRef = this.dialog.open(AddSongDialogComponent, {
    });
    dialogRef.afterClosed().subscribe(result => {
      this.handleSongAdded();
    });
  }

  openAddCategoryDialog(): void {
    const dialogRef = this.dialog.open(AddCategoryDialogComponent, {
    });
  }
  handleTileStateChanged(event: { noteNumber: number, state: boolean, track: number }): void {
    const { noteNumber, state, track } = event;
    const color = state ? DEFAULT_NOTE_COLORS[track] : ''; // Use default color or transparent if not active
    const existingIndex = this.keyColors.findIndex(k => k.key === noteNumber);

    if (existingIndex !== -1) {
      this.keyColors[existingIndex].colour = color; // Update existing key color
    } else {
      this.keyColors.push({ key: noteNumber, colour: color }); // Add new key color
    }
  }
  handleSongAdded(): void {
    console.log('Song added, refreshing song list');
    this.songListComponent.refreshSongs(); //whenever a song is added, refresh the song list
  }
  handleKeyPressed(keyId: number): void {
    this.socket.emit('keyPressed', keyId);
    console.log(`Key pressed: ${keyId}`);
  }
  ngOnInit() {
    this.socket.fromEvent('player_status').subscribe((status: StatusEvent) => {
      console.log('Received player status:', status);
    });
    this.socket.fromEvent('connected').subscribe(() => {
      console.log('Connected to server');
      this.keyColors = [];
    });
    this.socket.fromEvent('songUpdate').subscribe((data: SongEntry) => {
      this.currentSong = data;
      console.log('Current song updated:', this.currentSong);
    });
    this.socket.fromEvent('getStatus').subscribe((data: { currentTime: number, totalTime: number, playbarTime: number }) => {
      console.log('Received status update:', data);
      this.currentTime = data.currentTime;

    });
    this.socket.fromEvent('timeUpdate').subscribe((data) => {
      this.currentTime = data;
      if (this.totalTime > 0) {
        this.playbarTime = this.currentTime / this.totalTime * 100; // Update playbar time as a percentage
        //console.log(`Playbar time updated: ${this.playbarTime}, currentTime: ${this.currentTime}`);
      }
    });
    this.socket.fromEvent('playerbarUpdate').subscribe((data) => {
      this.playbarTime = data;
      this.currentTime = this.playbarTime * this.totalTime / 100; // Update current time based on playbar time
    });
    this.socket.fromEvent('tileUpdate').subscribe(() => { //tile update represents the successful parsing of a song
      console.log('Received tile update');
      this.keyColors = []; // Clear key colors on tile update
      fetch(`${environment.httpApi}/api/tiles`)
        .then(response => {
          if (response.status === 500) {
            console.error('Server error: 500');
            this.tileData = [];
            return;
          }
          return response.json();
        })
        .then(json => {
          if (json) {
            this.tileData = json;
            this.totalTime = Math.max(...this.tileData.map(tile => tile.end));
            console.log('Total time upated:', this.totalTime);
          }
        });
    });
    this.socket.fromEvent('portsUpdate').subscribe((data: MidiPort[]) => {
      this.midiPorts = data;
      console.log('MIDI ports updated:', this.midiPorts);
    });
    this.refreshMidiPorts();
  }
}
