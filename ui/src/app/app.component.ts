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
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SongListComponent, MatToolbarRow, MatIconModule, MatButtonModule, MatMenuModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'ui';
  currentTime = 0;
  constructor(public dialog: MatDialog, private socket: WebsocketService) {}

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
    });
  }
}
