import axios from "axios";
import type { AgentResponse, ChunkItem, DocumentItem, HealthStatus } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 45000,
});

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await apiClient.get<HealthStatus>("/health");
    return res.data;
  },

  async getDocuments(): Promise<{ documents: DocumentItem[]; total_count: number }> {
    const res = await apiClient.get<{ documents: DocumentItem[]; total_count: number }>("/documents");
    return res.data;
  },

  async getDocumentChunks(documentId: string): Promise<ChunkItem[]> {
    const res = await apiClient.get<ChunkItem[]>(`/documents/${documentId}/chunks`);
    return res.data;
  },

  async uploadDocument(file: File, title?: string): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file);
    const params = title ? { title } : {};
    const res = await apiClient.post<DocumentItem>("/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      params,
    });
    return res.data;
  },

  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`);
  },

  async sendChatMessage(query: string): Promise<AgentResponse> {
    const res = await apiClient.post<AgentResponse>("/chat", { query });
    return res.data;
  },
};
