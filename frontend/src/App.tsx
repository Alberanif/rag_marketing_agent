import React, { useState, useEffect } from "react";
import { Header } from "./components/Header/Header";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { DocumentManager } from "./components/Documents/DocumentManager";
import { ChartPanel } from "./components/Visualizer/ChartPanel";
import type { ChartDataset, ChatMessage, DocumentItem, HealthStatus } from "./types";
import { api } from "./services/api";

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);
  const [activeChart, setActiveChart] = useState<ChartDataset | null>(null);

  const fetchHealthAndDocs = async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch (e) {
      console.warn("Backend offline ou inicializando:", e);
    }

    try {
      setIsLoadingDocs(true);
      const docsRes = await api.getDocuments();
      setDocuments(docsRes.documents);
    } catch (e) {
      console.warn("Erro ao buscar documentos:", e);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchHealthAndDocs();
    const interval = setInterval(fetchHealthAndDocs, 20000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (query: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const response = await api.sendChatMessage(query);

      const lolaMsg: ChatMessage = {
        id: `lola-${Date.now()}`,
        sender: "lola",
        text: response.answer_markdown,
        citations: response.citations,
        chart: response.chart,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, lolaMsg]);

      // Atualiza o painel de gráfico se o agente produziu um dataset estruturado
      if (response.chart) {
        setActiveChart(response.chart);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `lola-err-${Date.now()}`,
        sender: "lola",
        text: `Desculpe, ocorreu um erro ao consultar os dados: ${
          err?.response?.data?.detail || err.message
        }. Certifique-se de que a API FastAPI e o container PostgreSQL estão em execução.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Header health={health} />

      <main className="main-split-container">
        {/* Painel Esquerdo: Chat Conversacional com Citações e Pensamento */}
        <ChatPanel
          messages={messages}
          isLoading={isChatLoading}
          onSendMessage={handleSendMessage}
          onSelectChart={(chart) => setActiveChart(chart)}
        />

        {/* Painel Direito: Base de Documentos & Visualizador Recharts */}
        <section className="right-panel">
          <DocumentManager
            documents={documents}
            isLoading={isLoadingDocs}
            onRefresh={fetchHealthAndDocs}
          />

          <ChartPanel currentChart={activeChart} />
        </section>
      </main>
    </div>
  );
};

export default App;
