import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, BookOpen, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import type { ChatMessage, ChartDataset } from "../../types";

interface ChatPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (query: string) => void;
  onSelectChart: (chart: ChartDataset) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onSelectChart,
}) => {
  const [input, setInput] = useState("");
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const toggleCitation = (messageId: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const quickPrompts = [
    "Qual canal teve o maior ROAS no relatório?",
    "Comparar investimento e CAC entre Google Ads e Meta Ads",
    "Qual foi o investimento total realizado no período?",
    "Resumo executivo com métricas de desempenho",
  ];

  return (
    <div className="left-chat-panel">
      <div className="chat-messages-container">
        {messages.length === 0 ? (
          <div className="chat-welcome-card">
            <h2 className="welcome-title">Olá, analista de marketing! 👋</h2>
            <p className="welcome-subtitle">
              Eu sou a <strong>Lola</strong>. Posso ler e auditar seus relatórios internos em PDF,
              calcular métricas de ROAS e CAC, e gerar gráficos dinâmicos com grounded facts.
            </p>
            <div className="quick-prompts-grid">
              {quickPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  className="quick-prompt-btn"
                  onClick={() => onSendMessage(prompt)}
                >
                  <Sparkles size={14} color="#00f0ff" />
                  <span>{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`message-bubble-wrapper ${msg.sender}`}>
              <div className={`sender-avatar ${msg.sender}`}>
                {msg.sender === "lola" ? <Bot size={18} /> : <User size={18} />}
              </div>

              <div className="message-content-box">
                <div className={`message-bubble ${msg.sender}`}>
                  <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>

                  {msg.chart && (
                    <div style={{ marginTop: "10px" }}>
                      <button
                        className="quick-prompt-btn"
                        style={{ display: "inline-flex", width: "auto" }}
                        onClick={() => onSelectChart(msg.chart!)}
                      >
                        <Sparkles size={14} color="#00f0ff" />
                        <span>Ver Gráfico: {msg.chart.title}</span>
                      </button>
                    </div>
                  )}

                  {msg.citations && msg.citations.length > 0 && (
                    <div className="citations-wrapper">
                      <button
                        className="citations-toggle-btn"
                        onClick={() => toggleCitation(msg.id)}
                      >
                        <BookOpen size={14} />
                        <span>
                          {msg.citations.length}{" "}
                          {msg.citations.length === 1 ? "fonte citada" : "fontes citadas"}
                        </span>
                        {expandedCitations[msg.id] ? (
                          <ChevronUp size={14} />
                        ) : (
                          <ChevronDown size={14} />
                        )}
                      </button>

                      {expandedCitations[msg.id] && (
                        <div className="citations-list">
                          {msg.citations.map((c, i) => (
                            <div key={i} className="citation-card">
                              <div className="citation-source">
                                📄 {c.document_name} • Pág. {c.page_number}
                                {c.section_title ? ` (${c.section_title})` : ""}
                              </div>
                              <div className="citation-snippet">"{c.snippet}"</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <span className="message-time">{msg.timestamp}</span>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="thinking-box">
            <Bot size={18} />
            <span>Lola está analisando relatórios corporativos e estruturando métricas</span>
            <div className="dots-loader">
              <span>.</span><span>.</span><span>.</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        <form onSubmit={handleSubmit} className="input-form-wrapper">
          <input
            type="text"
            className="chat-input"
            placeholder="Pergunte sobre campanhas, ROAS, CAC, canais ou relatórios..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={!input.trim() || isLoading}
            title="Enviar mensagem"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};
