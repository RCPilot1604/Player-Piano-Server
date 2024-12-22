import { Component, Input, OnInit, OnDestroy, inject} from '@angular/core';
import { SongEntry } from '../song-entry';
import { WebsocketService } from './websocket.service';
import { NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { wsdata } from './wsdata';

@Component({
  selector: 'app-current-song',
  standalone: true,
  imports: [NgIf, FormsModule],
  templateUrl: './current-song.component.html',
  styleUrls: ['./current-song.component.css']
})
export class CurrentSongComponent implements OnInit {
  @Input() song: SongEntry | null = null;
  isPlaying = false;
  currentTime = 0;
  duration = 100; // Initialize duration to 0
  volume = 50;
  private websocketService = inject(WebsocketService);
  constructor(private wsService: WebsocketService) {}

  ngOnInit() {
    this.wsService.connect('ws://localhost:3000').subscribe((message) => {
      console.log('Received message:', message.data);
    });
    const message = new MessageEvent('message', { data: JSON.stringify({ action: 'sendMessage', data: 'Hello, World!' }) });
    this.wsService.connect('ws://localhost:3000').next(message);
  }

  // ngOnDestroy() {
  //   this.websocketService.close();
  // }

  // togglePlayPause() {
  //   this.isPlaying = !this.isPlaying;
  //   if (this.isPlaying) {
  //     if (this.song && this.song.midiPath) {
  //       this.websocketService.sendMessage({ event: 'play', data: { trackPath: this.song.midiPath, payload: null} });
  //     } else {
  //       console.error('trackPath is null or undefined');
  //     }
  //   } else {
  //     if (this.song && this.song.midiPath){
  //       this.websocketService.sendMessage({ event: 'pause', data: { trackPath: this.song.midiPath, payload: null} });
  //     } else {
  //       console.error('trackPath is null or undefined');
  //     }
  //   }
  // }

  // seekTo(event: Event) {
  //   const input = event.target as HTMLInputElement;
  //   const seconds = Number(input.value);
  //   if(this.song && this.song.midiPath){
  //     this.websocketService.sendMessage({ event: 'seek', data: { trackPath: this.song.midiPath, payload: seconds} });
  //   } else {
  //     console.error('trackPath is null or undefined');
  //   }
  // }

  // changeVolume(event: Event) {
  //   const input = event.target as HTMLInputElement;
  //   this.volume = Number(input.value);
  //   // Implement volume control if needed
  // }
  
}