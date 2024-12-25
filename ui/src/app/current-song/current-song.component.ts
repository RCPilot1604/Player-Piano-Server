import { Component, Input, OnInit, OnDestroy, inject} from '@angular/core';
import { SongEntry } from '../song-entry';
import { NgIf } from '@angular/common';
import { WebsocketService } from './websocket.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-current-song',
  standalone: true,
  imports: [NgIf, FormsModule],
  providers: [WebsocketService],
  templateUrl: './current-song.component.html',
  styleUrls: ['./current-song.component.css']
})
export class CurrentSongComponent implements OnInit, OnDestroy {
  @Input() song: SongEntry | null = null;
  isPlaying = false;
  currentTime = 0;
  duration = 100; // Initialize duration to 0
  volume = 100;
  socket: WebsocketService = inject(WebsocketService);
  constructor() { }
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
  setVolume(volume: string) {
    this.volume = Number(volume);
    this.socket.emit('volume', volume);
  }
  seekTo() {
    this.socket.emit('seek', this.currentTime);
  }
  ngOnInit() {
    this.socket.fromEvent('connected').subscribe(() => {
      console.log('Connected to server');
    });
    this.socket.fromEvent('connect_error').subscribe((err) => {
      console.log('Error connecting to server: ', err);
    });
    this.socket.fromEvent('timeUpdate').subscribe((data) => {
      this.currentTime = data;
    });
  }
  ngOnDestroy(): void {
    this.socket.disconnect();
  }
}