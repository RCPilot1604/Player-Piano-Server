import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class CategoryService {
  private apiUrl = 'http://192.168.0.226:3000/api/categories';

  constructor(private http: HttpClient) {}

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(this.apiUrl);
  }

  addCategory(name: string): Observable<void> {
    return this.http.post<void>(this.apiUrl, { name });
  }
}