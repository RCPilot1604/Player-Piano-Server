import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SongListComponent } from './song-list/song-list.component';
import { MatToolbarRow } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { AddSongDialogComponent } from './add-song-dialog/add-song-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { AddCategoryDialogComponent } from './add-category-dialog/add-category-dialog/add-category-dialog.component';
import { WebsocketService } from './services/websocket.service';
import { ScrollableCanvasComponent } from './canvas/canvas.component';
import { TileEvent } from './models/tile-event.model';
import { environment } from '../environments/environment';
import { MatSliderModule } from '@angular/material/slider';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SongListComponent, MatToolbarRow, MatIconModule, MatButtonModule, MatMenuModule, ScrollableCanvasComponent, MatSliderModule, MatInputModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})

export class AppComponent {
  title = 'ui';
  currentTime = 0;
  totalTime = 0;
  playbarTime = 0; // Time for the playbar
  tileData: TileEvent[] = [];
  playbackMultiplier: number = 1; // Speed multiplier for playback
  constructor(public dialog: MatDialog, private socket: WebsocketService) { }

  openAddSongDialog(): void {
    const dialogRef = this.dialog.open(AddSongDialogComponent, {
    });
  }

  openAddCategoryDialog(): void {
    const dialogRef = this.dialog.open(AddCategoryDialogComponent, {
    });
  }

  ngOnInit() {
    this.socket.fromEvent('timeUpdate').subscribe((data) => {
      this.currentTime = data;
      if (this.totalTime > 0) {
        this.playbarTime = this.currentTime / this.totalTime * 100; // Update playbar time as a percentage
      }
    });
    this.socket.fromEvent('tileUpdate').subscribe(() => {
      console.log('Received tile update');
      fetch(`${environment.httpApi}/api/tiles`)
        .then(response => {
          if (response.status === 500) {
            console.error('Server error: 500');
            this.tileData = [];
            return;
          }
          return response.json();
        })
        .then(json => {
          if (json) {
            this.tileData = json;
            this.totalTime = Math.max(...this.tileData.map(tile => tile.end));
          }
        });
    });

  }
}
