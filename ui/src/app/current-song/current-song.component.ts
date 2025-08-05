import { Component, Input, OnInit, OnDestroy } from '@angular/core';
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
export class CurrentSongComponent implements OnInit, OnDestroy{
  @Input() currentTime: number = 0;
  @Input() selectedInstrumentIds: number[] = [];
  @Input() song: SongEntry | null = null;
  isPlaying = false;
  instruments: { id: number, channel: number, name: string }[] = [];
  volume = 100;
  constructor(private socket: WebsocketService) { }
  onInstrumentAction() {
    this.socket.emit('parseMidi', this.selectedInstrumentIds);
  }
  onInstrumentToggle(id: number, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      if (!this.selectedInstrumentIds.includes(id)) {
        this.selectedInstrumentIds.push(id);
      }
    } else {
      this.selectedInstrumentIds = this.selectedInstrumentIds.filter(i => i !== id);
    }
  }
  getValue(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }
  togglePlayPause() {
    this.isPlaying = !this.isPlaying;
    if (this.isPlaying) {
      this.socket.emit('play', "");
    } else {
      this.socket.emit('pause', "");
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
  ngOnInit() {
    this.socket.fromEvent('songUpdate').subscribe((data: SongEntry) => {
      this.song = data;
    });
    this.socket.fromEvent('instrumentsUpdate').subscribe((data: { id: number, channel: number, name: string }[]) => {
      this.instruments = data;
    });
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
  }
  ngOnDestroy(): void {
    this.socket.disconnect();
  }
}