import { Component, Input, Output, EventEmitter } from '@angular/core';
import { SongEntry } from '../song-entry';
import { MatListModule } from '@angular/material/list';

@Component({
  selector: 'app-song',
  template: `
    <mat-list-item (click)="onSongClick()">
      <p matLine> {{ song.title }} ({{ song.composer }})</p>
      <p matLine> {{ song.category }} </p>
    </mat-list-item>
  `,
  styleUrls: ['./song.component.css'],
  imports: [MatListModule],
})
export class SongComponent {
  @Input() song!: SongEntry;
  @Output() songClicked = new EventEmitter<SongEntry>();

  onSongClick() {
    console.log('Song clicked:', this.song.title);
    this.songClicked.emit(this.song);
  }
}
