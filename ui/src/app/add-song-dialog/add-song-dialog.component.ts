import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule} from '@angular/forms';
import { SongsService } from '../songs.service';
import { CategoryService } from '../categories.service';
import { MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NgIf, NgForOf } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatToolbar, MatToolbarRow } from '@angular/material/toolbar';
import { MatDialogContent, MatDialogActions } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatButton } from '@angular/material/button';

@Component({
  selector: 'app-add-song-dialog',
  imports: [ReactiveFormsModule, NgIf, NgForOf, MatDialogContent, MatFormFieldModule, 
    MatInputModule, MatSelectModule, MatSnackBarModule,MatDialogActions,MatButton,MatToolbar,MatToolbarRow],
  template: `
    <div id="dialog-title">
    <h2 mat-dialog-title>Add New Song</h2>
    </div>
    <form [formGroup]="newSongForm" (ngSubmit)="addNewSong()">
    <mat-dialog-content>
      <mat-form-field appearance="fill">
        <mat-label>Title</mat-label>
        <input matInput formControlName="title" id="title" required>
      </mat-form-field>
      <mat-form-field appearance="fill">
        <mat-label>Category</mat-label>
        <mat-select formControlName="category" id="category" (onclick)="refreshCategories()" required>
          <mat-option *ngFor="let category of categories" [value]="category">{{category}}</mat-option>
        </mat-select>
      </mat-form-field>
      <mat-toolbar id="file-upload-toolbar">
      <mat-toolbar-row id="file-upload">
        <input type="file" class="file-input" formControlName="midiFile" (change)="onFileSelected($event)" #fileUpload />
        <div class="file-upload"> {{fileName || "No file uploaded yet."}} </div>
        <button
          mat-button
          color="primary"
          class="upload-button"
          (click)="fileUpload.click()"
        >
          Choose File
        </button>
      </mat-toolbar-row>
      <mat-toolbar-row>
        <div *ngIf="finalError || fileError" class="error-box">{{ finalError }}</div>
      </mat-toolbar-row>
      </mat-toolbar>
    </mat-dialog-content>
    <mat-dialog-actions>
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-button color="primary" type="submit">Save</button>
    </mat-dialog-actions>
    </form>
  `,
  styleUrls: ['./add-song-dialog.component.css']
})
export class AddSongDialogComponent {
  newSongForm = new FormGroup(
    {
      title: new FormControl(''),
      composer: new FormControl(''),
      category: new FormControl(''),
      midiFile: new FormControl(''),
    }
  )

  categories: string[] = [];
  fileName = '';
  formData = new FormData(); 
  selectedFile: File | null = null;
  fileError: string | null = null;
  formError: string | null = null;
  finalError: string | null = null;
  
  @Output() songAdded = new EventEmitter();

  constructor( 
    private songsService: SongsService,
    private categoryService: CategoryService,
    private dialogRef: MatDialogRef<AddSongDialogComponent>,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.refreshCategories();
  }

  refreshCategories(){
    this.categoryService.getCategories().subscribe(data => {
      this.categories = data;
    });
  }
  addNewSong(): void{
    if (this.newSongForm.valid && this.selectedFile) {
      this.finalError = null; // Clear any previous error
      this.formData.append('title', this.newSongForm.value.title ?? '');
      this.formData.append('composer', this.newSongForm.value.composer ?? '');
      this.formData.append('category', this.newSongForm.value.category ?? '');
      this.formData.append('midiPath', this.fileName ?? '');
      this.formData.append('midiFile', this.selectedFile);
      this.songsService.addSong(this.formData).subscribe(() => {
        this.snackBar.open('Song added successfully!', 'Close', {
          duration: 3000,
        });
        this.songAdded.emit();
        this.dialogRef.close();
        this.fileName = ''; //reset the file name after the song is added
      }, error => {
        this.finalError = "Error adding song: " + error;
      });
      //console.table(Object.fromEntries(this.formData));
    } else {
      if(!this.selectedFile) this.finalError = "Please upload a .mid/.midi file.";
      else this.finalError = "Please fill out all fields.";
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file: File = input.files[0];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      if (fileExtension === 'mid' || fileExtension === 'midi') {
        this.fileName = file.name;
        this.selectedFile = file;
        this.finalError = null; // Clear any previous error
      } else {
        this.finalError = 'Invalid file type. Only .mid/.midi files are allowed.';
        this.selectedFile = null;
        input.value = '';
      }
    }
  }
}

