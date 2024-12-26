import { Component, Input, Output, EventEmitter } from '@angular/core';
import { SongEntry } from '../song-entry';
import { NgIf } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatDivider } from '@angular/material/divider';

@Component({
  selector: 'app-song',
  template: `
    <mat-list-item (click)="onSongClick()">
      <p matLine *ngIf="song.composer"> [{{ song.category }}] {{ song.title }} ({{ song.composer }})</p>
      <p matLine *ngIf="!song.composer"> [{{ song.category }}] {{ song.title }}</p>
      <mat-divider></mat-divider>
    </mat-list-item>
    <mat-divider></mat-divider>
  `,
  styleUrls: ['./song.component.css'],
  imports: [MatListModule, NgIf, MatDivider],
})
export class SongComponent {
  @Input() song!: SongEntry;
  @Output() songClicked = new EventEmitter<SongEntry>();

  onSongClick() {
    console.log('Song clicked:', this.song.title);
    this.songClicked.emit(this.song);
  }
}
