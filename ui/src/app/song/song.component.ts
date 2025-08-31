import { Component, Input, Output, EventEmitter } from '@angular/core';
import { SongEntry } from '../models/song-entry.model';
import { NgIf } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatDivider } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-song',
  template: `
    <mat-list-item (click)="onSongClick()" [class.disabled]="isDisabled">
      <div class="song-item">
      <p matLine *ngIf="song.composer"> [{{ song.category }}] {{ song.title }} ({{ song.composer }})</p>
      <p matLine *ngIf="!song.composer"> [{{ song.category }}] {{ song.title }}</p>
      <button mat-icon-button color="warn" (click)="onDeleteSong($event, song.id)" [disabled]="isDisabled">
        <mat-icon>close</mat-icon>
      </button>
      </div>
      <mat-divider></mat-divider>
    </mat-list-item>
    <mat-divider></mat-divider>
  `,
  styleUrls: ['./song.component.css'],
  imports: [MatListModule, NgIf, MatDivider, MatIconModule, MatButtonModule],
})
export class SongComponent {
  @Input() song!: SongEntry;
  @Input() isDisabled: boolean = false;
  @Output() songClicked = new EventEmitter<SongEntry>();
  @Output() songDeleted = new EventEmitter<number>();

  onSongClick() {
    console.log('Song clicked:', this.song.title);
    this.songClicked.emit(this.song);
  }
  onDeleteSong(event: MouseEvent, id: number) {
    event.stopPropagation();
    console.log('Delete song:', id);
    this.songDeleted.emit(id);
  }
}
