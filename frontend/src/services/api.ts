import {
  Repository,
  GraphResponse,
  ImpactAnalysisResponse,
  AskResponse,
  ConnectionStatus,
  BenchmarkResponse,
  SearchResponse,
} from '../types';

const API_BASE = '/api';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
  
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      signal: controller.signal,
      ...options,
    });
    
    clearTimeout(timeoutId);
    
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new ApiError(
        errorBody.detail || errorBody.error || `HTTP error! status: ${res.status}`,
        res.status,
        errorBody.detail
      );
    }
    
    return res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) throw err;
    if ((err as Error).name === 'AbortError') {
      throw new ApiError('Request timeout', 408);
    }
    throw new ApiError((err as Error).message, 0);
  }
}

export const api = {
  // ── Connection Status ─────────────────────────────────────────────────────
  getHealth: () => request<ConnectionStatus>('/health'),

  // ── Repository Management ─────────────────────────────────────────────────
  listRepositories: () => request<Repository[]>('/repository/list'),
  
  analyzeRepository: (source: string, forceReanalysis = false) =>
    request<Repository>('/repository/analyze', {
      method: 'POST',
      body: JSON.stringify({ source, force_reanalysis: forceReanalysis }),
    }),
    
  getRepositoryStatus: (repositoryId: string) =>
    request<Repository>(`/repository/${repositoryId}/status`),

  // ── Graph Data ────────────────────────────────────────────────────────────
  getGraph: (repositoryId: string) =>
    request<GraphResponse>(`/graph/${repositoryId}`),

  // ── Impact Analysis (Before You Change It) ────────────────────────────────
  analyzeImpact: (
    repositoryId: string,
    entityId: string,
    entityName: string,
    entityType: string
  ) =>
    request<ImpactAnalysisResponse>('/impact-analysis', {
      method: 'POST',
      body: JSON.stringify({
        repository_id: repositoryId,
        entity_id: entityId,
        entity_name: entityName,
        entity_type: entityType,
      }),
    }),

  // ── Grounded Q&A Chat ─────────────────────────────────────────────────────
  askCodeMind: (repositoryId: string, question: string) =>
    request<AskResponse>('/ask', {
      method: 'POST',
      body: JSON.stringify({ repository_id: repositoryId, question }),
    }),

  // ── Benchmarking ──────────────────────────────────────────────────────────
  runBenchmark: (repositoryId: string) =>
    request<BenchmarkResponse>(`/benchmark/${repositoryId}`),

  // ── Search ────────────────────────────────────────────────────────────────
  searchCode: (repositoryId: string, query: string, entityTypes?: string[]) =>
    request<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify({
        repository_id: repositoryId,
        query,
        entity_types: entityTypes,
      }),
    }),
};
