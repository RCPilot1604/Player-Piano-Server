import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SongListComponent } from './song-list/song-list.component';
import { MatToolbarRow } from '@angular/material/toolbar';
import { MatIcon } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { AddSongDialogComponent } from './add-song-dialog/add-song-dialog.component';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SongListComponent, MatToolbarRow, MatIcon, MatButtonModule, MatMenuModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'ui';
  constructor(public dialog: MatDialog) {}

  openAddSongDialog(): void {
    const dialogRef = this.dialog.open(AddSongDialogComponent, {
      width: '500px',
    });
  }
}
