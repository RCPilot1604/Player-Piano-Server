import { Component,inject } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule} from '@angular/forms';
import { CategoryService } from '../../categories.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogContent, MatDialogActions,MatDialogRef } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatButton } from '@angular/material/button';

@Component({
  selector: 'app-add-category-dialog',
  imports: [ReactiveFormsModule, MatDialogContent, MatFormFieldModule, 
      MatInputModule, MatSelectModule, MatSnackBarModule,MatDialogActions,MatButton],
  template: `
    <div id="dialog-title">
    <h2 mat-dialog-title>Add New Category</h2>
    </div>
    <form [formGroup]="newCategoryForm" (ngSubmit)="addNewCategory()">
    <mat-dialog-content>
      <mat-form-field appearance="fill">
        <mat-label>Category Name</mat-label>
        <input matInput formControlName="category" id="newCategory" required>
      </mat-form-field>
    </mat-dialog-content>
    <mat-dialog-actions>
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-button color="primary" type="submit" [disabled]=!newCategoryForm.valid>Save</button>
    </mat-dialog-actions>
    </form>
  `,
  styleUrl: './add-category-dialog.component.css'
})
export class AddCategoryDialogComponent {
  constructor( private categoryService: CategoryService, private dialogRef: MatDialogRef<AddCategoryDialogComponent>) { }
  private _snackBar = inject(MatSnackBar);
  newCategoryForm = new FormGroup(
    {
      category: new FormControl(''),
    }
  );
  addNewCategory(): void {
    const category = this.newCategoryForm.value.category ?? '';
    this.categoryService.addCategory(category).subscribe(() => {
      this.newCategoryForm.reset();
      this.dialogRef.close();
      let snackBarRef = this._snackBar.open('Category added successfully', 'Close', {
        duration: 3000,
      });
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
