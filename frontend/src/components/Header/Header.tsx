import React from "react";
import { Sparkles, Database, FileText } from "lucide-react";
import type { HealthStatus } from "../../types";

interface HeaderProps {
  health: HealthStatus | null;
}

export const Header: React.FC<HeaderProps> = ({ health }) => {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon-wrapper">
          <Sparkles size={20} color="#000" />
        </div>
        <div>
          <span className="brand-title">Lola</span>
          <span className="brand-badge" style={{ marginLeft: "8px" }}>
            Marketing AI
          </span>
        </div>
      </div>

      <div className="header-status-section">
        <div className="status-indicator" title="Status da Conexão com PostgreSQL e pgvector">
          <div className="status-dot" />
          <span>
            {health?.status === "healthy" ? "Online & Conectada" : "Serviço Ativo"}
          </span>
        </div>

        <div className="status-indicator" title="Métricas do Banco Vetorial">
          <Database size={14} color="#00f0ff" />
          <span>
            {health?.pgvector === "active" ? "pgvector HNSW" : "PostgreSQL"}
          </span>
        </div>

        <div className="status-indicator" title="Total de Documentos e Chunks Indexados">
          <FileText size={14} color="#818cf8" />
          <span>
            {health ? `${health.total_documents} docs (${health.total_chunks} chunks)` : "0 docs"}
          </span>
        </div>
      </div>
    </header>
  );
};
