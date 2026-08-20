// Frontend TypeScript type definitions

export interface Repository {
  repository_id: string;
  repository_name: string;
  repository_url: string;
  status: 'cloning' | 'parsing' | 'building_graph' | 'ingesting' | 'ready' | 'error';
  statistics?: {
    files: number;
    functions: number;
    classes: number;
    apis: number;
    tests: number;
    relationships: number;
  };
  error?: string;
  progress?: number;
  message?: string;
}

export interface AnalysisStatusResponse {
  repository_id: string;
  repository_name: string;
  repository_url: string;
  status: string;
  progress: number;
  message: string;
  statistics?: Record<string, number>;
  error?: string;
}

export interface GraphNode {
  id: string;
  type: string;
  name: string;
  file: string;
  line: number;
  label: string;
  connection_count: number;
  metadata: {
    docstring?: string;
    parameters?: string[];
    return_type?: string;
    decorators?: string[];
    is_async?: boolean;
    base_classes?: string[];
    [key: string]: any;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  context: string;
}

export interface GraphResponse {
  repository_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: {
    files: number;
    functions: number;
    classes: number;
    apis: number;
    tests: number;
    relationships: number;
  };
}

export interface ImpactedEntity {
  id: string;
  name: string;
  type: string;
  file: string;
  line: number;
  relationship: string;
  impact_level: 'direct' | 'transitive';
  confidence: number;
}

export interface DependencyPathItem {
  source: string;
  predicate: string;
  target: string;
  context: string;
}

export interface ImpactAnalysisResponse {
  repository_id: string;
  entity_id: string;
  entity_name: string;
  entity_type: string;
  callers: ImpactedEntity[];
  tests: ImpactedEntity[];
  apis: ImpactedEntity[];
  files: ImpactedEntity[];
  classes: ImpactedEntity[];
  dependency_paths: DependencyPathItem[][];
  total_impacted: number;
  blast_radius: 'none' | 'low' | 'medium' | 'high' | 'critical';
  ai_summary?: string;
  graph_source: string;
  hydradb_query_paths: number;
}

export interface EvidenceItem {
  chunk_id?: string;
  text: string;
  entity_name?: string;
  entity_type?: string;
  file?: string;
  relevance_score: number;
  relationship_path?: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  evidence: EvidenceItem[];
  dependency_paths: DependencyPathItem[][];
  hydradb_chunks: number;
  hydradb_graph_paths: number;
}

export interface ConnectionStatus {
  connected: boolean;
  message: string;
  databases_count?: number;
}

// Benchmark Interfaces
export interface QueryBenchmark {
  question: string;
  baseline: {
    latency_ms: number;
    chunks_retrieved: number;
    relations_found: number;
    completeness_score: number;
  };
  codemind: {
    latency_ms: number;
    chunks_retrieved: number;
    relations_found: number;
    paths_count: number;
    completeness_score: number;
  };
}

export interface BenchmarkResponse {
  database: string;
  queries_executed: number;
  averages: {
    baseline_latency_ms: number;
    codemind_latency_ms: number;
    latency_increase_pct: number;
  };
  metrics: {
    total_relations_retrieved: number;
    grounded_paths_available: number;
    graph_retrieval_benefit: string;
  };
  queries: QueryBenchmark[];
}
