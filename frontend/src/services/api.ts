import {
  Repository,
  GraphResponse,
  ImpactAnalysisResponse,
  AskResponse,
  ConnectionStatus,
  BenchmarkResponse,
} from '../types';

const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || errorBody.error || `HTTP error! status: ${res.status}`);
  }
  
  return res.json();
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
};
