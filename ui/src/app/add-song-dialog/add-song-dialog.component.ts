import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule} from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { Validators } from '@angular/forms';
import { SongsService } from '../songs.service';
import { CategoryService } from '../categories.service';
import { MatDialogRef } from '@angular/material/dialog';
import { MatIcon } from '@angular/material/icon';

@Component({
  selector: 'app-add-song-dialog',
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="dialog-overlay" (click)="onCancel()"></div>
    <div class="dialog">
      <h2>Add New Song</h2>
      <form [formGroup]="newSongForm" (submit)="addNewSong()">
        <label for="title"> Title: </label>
        <input type="text" id="title" formControlName="title" required>
        <label for="composer"> Composer: </label>
        <input type="text" id="composer" formControlName="composer" required>
        <label for="category"> Category: </label>
        <select id="category" formControlName="category" required>
          <!--<option *ngFor="let category of categories" [value]="category">{{ category }}</option> -->
          <option value="Classical"> Classical </option>
        </select>
        <label for="midiFile"> Upload MIDI File: </label>
        <input type="file" class="file-input" (change)="onFileSelected($event)" #fileUpload>
        <div class="file-upload"> {{fileName || "No file uploaded yet."}}
          <button mat-mini-fab color="primary" class="upload-btn" (click)="fileUpload.click()">
            <mat-icon>attach_file</mat-icon>
          </button>
        </div>
        <div class="dialog-actions">
          <button type="button" (click)="onCancel()">Cancel</button>
          <button type="submit">Add</button>
        </div>
      </form>
    </div>
  `,
  styleUrls: ['./add-song-dialog.component.css']
})
export class AddSongDialogComponent {
  newSongForm = new FormGroup(
    {
      title: new FormControl('', Validators.required),
      composer: new FormControl('', Validators.required),
      category: new FormControl('', Validators.required),
      midiPath: new FormControl('', Validators.required),
    }
  )

  categories: string[] = [];
  fileName = '';
  formData = new FormData(); 
  selectedFile: File | null = null;
  
  @Output() songAdded = new EventEmitter();

  constructor(
    private categoryService: CategoryService, 
    private songsService: SongsService,
    private dialogRef: MatDialogRef<AddSongDialogComponent>
  ) {}

  ngOnInit() {
    this.categoryService.getCategories().subscribe(data => {
      this.categories = data;
    });
  }

  addNewSong(): void{
    if (this.newSongForm.valid && this.selectedFile) {
      this.formData.append('title', this.newSongForm.value.title ?? '');
      this.formData.append('composer', this.newSongForm.value.composer ?? '');
      this.formData.append('category', this.newSongForm.value.category ?? '');
      this.formData.append('midiFile', this.selectedFile);
      this.songsService.addSong(this.formData).subscribe(() => {
        this.songAdded.emit();
        this.dialogRef.close();
        this.fileName = ''; //reset the file name after the song is added
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file: File = input.files[0];
      this.fileName = file.name;
      this.selectedFile = file; 
    }
  }
}

