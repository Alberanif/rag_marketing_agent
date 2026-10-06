export interface Citation {
  document_id: string;
  document_name: string;
  page_number: number;
  section_title?: string | null;
  snippet: string;
}

export interface ChartDataset {
  title: string;
  chart_type: "bar" | "line" | "area" | "pie";
  x_axis_key: string;
  data_keys: string[];
  series_labels?: Record<string, string> | null;
  data: Record<string, any>[];
}

export interface AgentResponse {
  answer_markdown: string;
  citations: Citation[];
  chart?: ChartDataset | null;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "lola";
  text: string;
  citations?: Citation[];
  chart?: ChartDataset | null;
  timestamp: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  total_pages: number;
  total_chunks: number;
  metadata: Record<string, any>;
  created_at: string;
}

export interface ChunkItem {
  id: string;
  chunk_index: number;
  page_number: number;
  section_title?: string | null;
  content: string;
  metadata: Record<string, any>;
}

export interface HealthStatus {
  status: string;
  database: string;
  pgvector: string;
  total_documents: number;
  total_chunks: number;
}
