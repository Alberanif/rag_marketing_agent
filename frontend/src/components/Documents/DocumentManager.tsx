import React, { useState, useRef } from "react";
import { Upload, FileText, Trash2, Eye, X, CheckCircle2, Loader2 } from "lucide-react";
import type { ChunkItem, DocumentItem } from "../../types";
import { api } from "../../services/api";

interface DocumentManagerProps {
  documents: DocumentItem[];
  isLoading: boolean;
  onRefresh: () => void;
}

export const DocumentManager: React.FC<DocumentManagerProps> = ({
  documents,
  isLoading,
  onRefresh,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [selectedDocChunks, setSelectedDocChunks] = useState<{
    doc: DocumentItem;
    chunks: ChunkItem[];
  } | null>(null);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Por favor, selecione um arquivo no formato PDF.");
      return;
    }

    try {
      setIsUploading(true);
      await api.uploadDocument(file);
      setUploadSuccess(`"${file.name}" ingerido com sucesso!`);
      setTimeout(() => setUploadSuccess(null), 4000);
      onRefresh();
    } catch (err: any) {
      alert(`Erro no upload: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string, docName: string) => {
    if (!confirm(`Deseja realmente excluir o documento "${docName}" e todos os seus vetores?`)) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      if (selectedDocChunks?.doc.id === docId) {
        setSelectedDocChunks(null);
      }
      onRefresh();
    } catch (err: any) {
      alert(`Erro ao excluir: ${err.message}`);
    }
  };

  const handleViewChunks = async (doc: DocumentItem) => {
    try {
      setIsLoadingChunks(true);
      const chunks = await api.getDocumentChunks(doc.id);
      setSelectedDocChunks({ doc, chunks });
    } catch (err: any) {
      alert("Erro ao carregar chunks do documento.");
    } finally {
      setIsLoadingChunks(false);
    }
  };

  return (
    <div className="panel-section-card">
      <div className="section-header">
        <h3 className="section-title">
          <FileText size={18} color="#818cf8" />
          Base de Conhecimento (PDFs)
        </h3>
        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "6px" }}>
          {isLoading && <Loader2 size={14} color="#00f0ff" />}
          {documents.length} {documents.length === 1 ? "relatório ativo" : "relatórios ativos"}
        </span>
      </div>

      {/* Dropzone */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept="application/pdf"
        style={{ display: "none" }}
      />
      <div
        className={`upload-dropzone ${isDragging ? "active" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={24} color={isDragging ? "#00f0ff" : "#94a3b8"} />
        <span className="upload-text">
          {isUploading
            ? "Processando tabelas, extraindo títulos e gerando embeddings..."
            : "Arraste relatórios em PDF aqui ou clique para selecionar"}
        </span>
        <span className="upload-subtext">
          PyMuPDF Table Extraction • Semantic Chunker 600t • Vector 1536d
        </span>
      </div>

      {uploadSuccess && (
        <div style={{ marginTop: "10px", color: "var(--accent-emerald)", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "6px" }}>
          <CheckCircle2 size={16} />
          {uploadSuccess}
        </div>
      )}

      {/* Documents List */}
      <div className="documents-list">
        {documents.map((doc) => (
          <div key={doc.id} className="document-item-row">
            <div className="doc-info">
              <FileText size={16} color="#00f0ff" />
              <div>
                <div className="doc-title">{doc.title}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {doc.filename}
                </div>
              </div>
            </div>

            <div className="doc-actions">
              <span className="doc-meta-badge">
                {doc.total_pages} {doc.total_pages === 1 ? "pág" : "págs"} • {doc.total_chunks} chunks
              </span>
              <button
                className="icon-action-btn"
                onClick={() => handleViewChunks(doc)}
                title="Visualizar Chunks & Embeddings"
                disabled={isLoadingChunks}
              >
                {isLoadingChunks ? <Loader2 size={16} /> : <Eye size={16} />}
              </button>
              <button
                className="icon-action-btn"
                onClick={() => handleDelete(doc.id, doc.title)}
                title="Excluir Relatório"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal / Inspector de Chunks */}
      {selectedDocChunks && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.8)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-medium)",
              borderRadius: "var(--radius-lg)",
              maxWidth: "750px",
              width: "100%",
              maxHeight: "85vh",
              display: "flex",
              flexDirection: "column",
              padding: "24px",
              boxShadow: "var(--shadow-glow)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
                borderBottom: "1px solid var(--border-subtle)",
                paddingBottom: "12px",
              }}
            >
              <div>
                <h3 style={{ fontFamily: "var(--font-display)", color: "#fff", fontSize: "1.1rem" }}>
                  Chunks Indexados: {selectedDocChunks.doc.title}
                </h3>
                <span style={{ fontSize: "0.8rem", color: "var(--accent-cyan)" }}>
                  {selectedDocChunks.chunks.length} chunks armazenados no pgvector
                </span>
              </div>
              <button
                className="icon-action-btn"
                onClick={() => setSelectedDocChunks(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
              {selectedDocChunks.chunks.map((chk) => (
                <div
                  key={chk.id}
                  style={{
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    padding: "12px",
                    fontSize: "0.84rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "6px",
                      color: "var(--text-secondary)",
                      fontWeight: 600,
                    }}
                  >
                    <span>Chunk #{chk.chunk_index} • Pág {chk.page_number}</span>
                    <span style={{ color: "var(--accent-cyan)" }}>{chk.section_title || "Geral"}</span>
                  </div>
                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      fontFamily: "inherit",
                      color: "var(--text-primary)",
                      lineHeight: "1.5",
                      fontSize: "0.8rem",
                      background: "rgba(0,0,0,0.2)",
                      padding: "8px",
                      borderRadius: "4px",
                    }}
                  >
                    {chk.content}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
