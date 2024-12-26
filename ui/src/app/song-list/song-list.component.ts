import { Component, inject, Output } from '@angular/core';
import { SongEntry } from '../song-entry';
import { SongComponent } from '../song/song.component';
import { SongsService } from '../songs.service';
import { NgForOf } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';
import { FormsModule, FormGroup, FormControl, ReactiveFormsModule } from '@angular/forms';
import { CurrentSongComponent } from '../current-song/current-song.component';
import { CategoryService } from '../categories.service';
import { WebsocketService } from '../current-song/websocket.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSelectModule } from '@angular/material/select';
import { MatOption } from '@angular/material/core';
@Component({
  selector: 'app-song-list',
  imports: [CurrentSongComponent, SongComponent, NgForOf, FormsModule, ReactiveFormsModule, MatFormFieldModule, 
        MatInputModule, MatSelectModule, MatOption, MatToolbarModule],
  providers: [SongsService, WebsocketService, CategoryService],
  templateUrl: './song-list.component.html',
  styleUrl: './song-list.component.css'
})
export class SongListComponent {
  songs: SongEntry[] = [];
  filteredSongs: SongEntry[] = [];
  songsService: SongsService = inject(SongsService);
  websocket: WebsocketService = inject(WebsocketService);
  currentSong: SongEntry | null = null;
  dialog: MatDialog = inject(MatDialog);
  categories: string[] = [];
  selectedCategory: string = 'All';
  searchText: string = '';
  
  constructor(private categoryService: CategoryService,
  ) {
    this.songs = [];
  }
  
  ngOnInit() {
    this.refreshSongs();
    this.refreshCategories();
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
  refreshCategories(){
    this.categoryService.getCategories().subscribe(data => {
      this.categories = data;
    });
  }
  refreshSongs() {
    this.songsService.getSong().subscribe(data => {
      this.songs = data as SongEntry[];
      this.filterSongs();
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
}
