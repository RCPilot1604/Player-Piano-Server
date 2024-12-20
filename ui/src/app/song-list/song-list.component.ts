import { Component, inject, Output } from '@angular/core';
import { SongEntry } from '../song-entry';
import { SongComponent } from '../song/song.component';
import { SongsService } from '../songs.service';
import { NgForOf } from '@angular/common';
import { CurrentSongComponent } from '../current-song/current-song.component';
import { AddSongDialogComponent } from '../add-song-dialog/add-song-dialog.component';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-song-list',
  imports: [CurrentSongComponent, SongComponent, NgForOf],
  templateUrl: './song-list.component.html',
  styleUrl: './song-list.component.css'
})
export class SongListComponent {
  songs: SongEntry[] = [];
  songsService: SongsService = inject(SongsService);
  currentSong: SongEntry | null = null;
  dialog: MatDialog = inject(MatDialog);
  constructor(
  ) {
    this.songs = [];
  }
  
  ngOnInit() {
    this.songsService.getSong().subscribe(data => {
      console.log(data);
      this.songs = data as SongEntry[];
    });
  }
  
  deleteSong(id: number) {
    this.songsService.deleteSong(id).subscribe((data) => {
      console.log(data);
    });
  }

  onSongClicked(song: SongEntry) {
    this.currentSong = song;
  }

  openAddSongDialog(): void {
    const dialogRef = this.dialog.open(AddSongDialogComponent, {
      width: '300px'
    });
  }
}
