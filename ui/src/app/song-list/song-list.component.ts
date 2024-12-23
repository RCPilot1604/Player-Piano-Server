import { Component, inject, Output } from '@angular/core';
import { SongEntry } from '../song-entry';
import { SongComponent } from '../song/song.component';
import { SongsService } from '../songs.service';
import { NgForOf } from '@angular/common';
import { AddSongDialogComponent } from '../add-song-dialog/add-song-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { FormsModule, FormGroup, FormControl, ReactiveFormsModule } from '@angular/forms';
import { CurrentSongComponent } from '../current-song/current-song.component';
import { CategoryService } from '../categories.service';
import { WebsocketService } from '../current-song/websocket.service';
@Component({
  selector: 'app-song-list',
  imports: [CurrentSongComponent, SongComponent, NgForOf, FormsModule, ReactiveFormsModule],
  providers: [SongsService, WebsocketService, CategoryService],
  templateUrl: './song-list.component.html',
  styleUrl: './song-list.component.css'
})
export class SongListComponent {
  songs: SongEntry[] = [];
  songsService: SongsService = inject(SongsService);
  websocket: WebsocketService = inject(WebsocketService);
  currentSong: SongEntry | null = null;
  dialog: MatDialog = inject(MatDialog);
  
  
  newCategoryForm = new FormGroup(
    {
      category: new FormControl(''),
    }
  );

  constructor(private categoryService: CategoryService,
  ) {
    this.songs = [];
  }
  
  ngOnInit() {
    this.refreshSongs();
  }
  
  refreshSongs() {
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
    this.websocket.emit('loadMidi', song.midiPath);
  }

  openAddSongDialog(): void {
    const dialogRef = this.dialog.open(AddSongDialogComponent, {
      width: '300px'
    });

    dialogRef.componentInstance.songAdded.subscribe(() => {
      this.refreshSongs();
    });
  }

  addNewCategory(): void {
    const category = this.newCategoryForm.value.category ?? '';
    this.categoryService.addCategory(category).subscribe(() => {
      this.newCategoryForm.reset();
    });
  }
}
