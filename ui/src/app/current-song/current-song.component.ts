import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, OnChanges, SimpleChanges } from '@angular/core';
import { SongEntry } from '../models/song-entry.model';
import { NgIf, NgFor } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatSliderModule } from '@angular/material/slider';
import { MatIcon } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { WebsocketService } from '../services/websocket.service';
@Component({
  selector: 'app-current-song',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, MatSliderModule, MatIcon, MatButtonModule],
  templateUrl: './current-song.component.html',
  styleUrls: ['./current-song.component.css']
})
export class CurrentSongComponent implements OnInit, OnDestroy, OnChanges {
  @Input() currentTime: number = 0;
  @Input() song: SongEntry | null = null;
  @Output() playStateChange = new EventEmitter<boolean>();
  selectedInstrumentIds: number[] = [];
  isPlaying = false;
  
  instruments: { id: number, channel: number, name: string }[] = [];
  volume = 100;
  constructor(private socket: WebsocketService) { }
  onParse() {
    const inputs = document.querySelectorAll<HTMLInputElement>('input.track-selection');
    inputs.forEach(input => {
      if (input.checked) {
        console.log(`Instrument ${input.value} selected`);
        const id = Number(input.value);
        if (!this.selectedInstrumentIds.includes(id)) {
          this.selectedInstrumentIds.push(id);
        }
      } else {
        this.selectedInstrumentIds = this.selectedInstrumentIds.filter(i => i !== Number(input.value));
      }
    });
    console.log('Parsing MIDI with selected instruments:', this.selectedInstrumentIds);
    this.socket.emit('parseMidi', this.selectedInstrumentIds);
  }
  onInstrumentToggle(id: number, event: Event) {
    const instrumentId = typeof id === 'string' ? Number(id) : id;
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      if (!this.selectedInstrumentIds.includes(instrumentId)) {
        this.selectedInstrumentIds.push(instrumentId);
      }
    } else {
      this.selectedInstrumentIds = this.selectedInstrumentIds.filter(i => i !== instrumentId);
    }
  }
  getValue(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }
  togglePlayPause() {
    this.isPlaying = !this.isPlaying;
    if (this.isPlaying) {
      this.socket.emit('play', "");
      this.playStateChange.emit(true);
    } else {
      this.socket.emit('pause', "");
      this.playStateChange.emit(false);
    }
  }
  incrementVolume() {
    this.volume = Math.min(100, this.volume + 1);
    this.updateVolume();
  }
  decrementVolume() {
    this.volume = Math.max(0, this.volume - 1);
    this.updateVolume();
  }
  updateVolume() {
    this.socket.emit('volume', this.volume);
  }
  seekTo() {
    this.socket.emit('seek', this.currentTime);
    console.log('Seek to:', this.currentTime);
  }
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['currentTime']) {
      const time = changes['currentTime'].currentValue;
      if (time == 0) {
        this.isPlaying = false;
        this.playStateChange.emit(false);
      }
    }
  }
  ngOnInit() {
    this.socket.fromEvent('playUpdate').subscribe((data) => {
      this.isPlaying = Boolean(data);
    });
    this.socket.fromEvent('volumeUpdate').subscribe((data) => {
      this.volume = data;
    });
    this.socket.fromEvent('setInstruments').subscribe((data: { id: number, channel: number, name: string }[]) => {
      console.log('Received instruments:', data);
      this.instruments = data;
    });
    this.socket.fromEvent('setTracksToPlay').subscribe((data: number[]) => {
      this.selectedInstrumentIds = [...data];
      console.log('Received tracks to play:', this.selectedInstrumentIds);
    });
  }
  ngOnDestroy(): void {
    this.socket.disconnect();
  }
}