import { Component, inject, Input } from '@angular/core';
import { SongEntry } from '../song-entry';
import { SongComponent } from '../song/song.component';
import { SongsService } from '../services/songs.service';
import { NgForOf } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';
import { FormsModule, FormGroup, FormControl, ReactiveFormsModule } from '@angular/forms';
import { CurrentSongComponent } from '../current-song/current-song.component';
import { Category, CategoryService } from '../services/categories.service';
import { WebsocketService } from '../services/websocket.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSelectModule } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
import { MatList } from '@angular/material/list';
import { MatDividerModule } from '@angular/material/divider';
import { ConfirmDialogComponent, ConfirmDialogData } from '../confirmation-dialog/confirmation-dialog';
@Component({
  selector: 'app-song-list',
  imports: [CurrentSongComponent, SongComponent, NgForOf, FormsModule, ReactiveFormsModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatOption, MatToolbarModule, MatList, MatDividerModule, ConfirmDialogComponent],
  providers: [SongsService, CategoryService],
  templateUrl: './song-list.component.html',
  styleUrl: './song-list.component.css'
})
export class SongListComponent {
  @Input() currentTime: number = 0;
  songs: SongEntry[] = [];
  filteredSongs: SongEntry[] = [];
  songsService: SongsService = inject(SongsService);
  currentSong: SongEntry | null = null;
  dialog: MatDialog = inject(MatDialog);
  categories: Category[] = [];
  selectedCategory: string = 'All';
  searchText: string = '';
  constructor(private categoryService: CategoryService,
    private websocket: WebsocketService) {
    this.songs = [];
  }

  ngOnInit() {
    this.refreshSongs();
    this.refreshCategories();
    this.websocket.fromEvent('loadMidiUpdate').subscribe((data) => {
      this.currentSong = data;
    });
  }

  filterSongs() {
    console.log(this.searchText);
    if (this.selectedCategory == 'All') {
      this.filteredSongs = this.songs;
    } else {
      this.filteredSongs = this.songs.filter(song => song.category == this.selectedCategory);
    }
    if (this.searchText == '') {
      this.filteredSongs = this.filteredSongs;
    } else {
      this.filteredSongs = this.filteredSongs.filter(song => song.title.toLowerCase().includes(this.searchText.toLowerCase()));
    }
  }
  refreshCategories() {
    this.categoryService.getCategories().subscribe((data: Category[]) => {
      this.categories = data;
    });
    console.log("Categories refreshed:", this.categories);
  }
  refreshSongs() {
    this.songsService.getSong().subscribe(data => {
      this.songs = data as SongEntry[];
      this.filterSongs();
    });
  }
  onSongDeleted(id: number) {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Delete Song?',
        message: 'Are you sure you want to delete this song?',
        confirmText: 'Delete',
        cancelText: 'Cancel'
      } as ConfirmDialogData
    });
    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.songsService.deleteSong(id).subscribe({
          next: () => {
            this.refreshSongs();
          },
          error: (err) => {
            this.dialog.open(ConfirmDialogComponent, {
              data: {
                title: 'Error',
                message: `Failed to delete song. Server responded with status ${err.status || 'unknown'}.`,
                confirmText: 'OK',
                cancelText: ''
              } as ConfirmDialogData
            });
          }
        });
      }
    });
  }

  onSongClicked(song: SongEntry) {
    this.currentSong = song;
    this.websocket.emit('loadMidi', song);
  }
}
