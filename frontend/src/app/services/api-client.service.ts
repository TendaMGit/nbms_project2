import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiClientService {
  constructor(private readonly http: HttpClient) {}

  get<T>(url: string, params?: Record<string, string | number | boolean | undefined>): Observable<T> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params ?? {})) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<T>(`/api/${url}`, { params: httpParams });
  }

  post<T>(url: string, payload: unknown): Observable<T> {
    return this.http.post<T>(`/api/${url}`, payload);
  }

  put<T>(url: string, payload: unknown): Observable<T> {
    return this.http.put<T>(`/api/${url}`, payload);
  }

  delete<T>(url: string, params?: Record<string, string | number | boolean | undefined>): Observable<T> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params ?? {})) {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.delete<T>(`/api/${url}`, { params: httpParams });
  }
}
