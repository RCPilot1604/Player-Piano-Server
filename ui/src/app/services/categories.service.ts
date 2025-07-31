import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
export interface Category {
  id: number;
  name: string;
}
@Injectable({
  providedIn: 'root'
})
export class CategoryService {
  private apiUrl = `${environment.httpApi}/api/categories`;

  constructor(private http: HttpClient) { }

  getCategories(): Observable<Category[]> {
    return this.http.get<Category[]>(this.apiUrl);
  }

  addCategory(name: string): Observable<void> {
    return this.http.post<void>(this.apiUrl, { name });
  }
}