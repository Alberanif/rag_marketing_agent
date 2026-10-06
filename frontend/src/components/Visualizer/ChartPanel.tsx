import React, { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { BarChart3, LineChart as LineIcon, AreaChart as AreaIcon, PieChart as PieIcon } from "lucide-react";
import type { ChartDataset } from "../../types";

interface ChartPanelProps {
  currentChart: ChartDataset | null;
}

const COLORS = ["#00f0ff", "#818cf8", "#10b981", "#f43f5e", "#f59e0b", "#c084fc"];

// Gráfico padrão de demonstração caso nenhuma pergunta tenha sido feita ainda
const DEFAULT_DEMO_CHART: ChartDataset = {
  title: "Performance por Canal de Marketing (Q3 2026)",
  chart_type: "bar",
  x_axis_key: "canal",
  data_keys: ["roas", "cac"],
  series_labels: {
    roas: "ROAS (Retorno Médio)",
    cac: "CAC (Custo por Aquisição R$)",
  },
  data: [
    { canal: "Google Ads", roas: 5.2, cac: 38.0 },
    { canal: "Meta Ads", roas: 4.5, cac: 44.0 },
    { canal: "TikTok Ads", roas: 3.8, cac: 52.0 },
  ],
};

export const ChartPanel: React.FC<ChartPanelProps> = ({ currentChart }) => {
  const chart = currentChart || DEFAULT_DEMO_CHART;
  const [selectedType, setSelectedType] = useState<"bar" | "line" | "area" | "pie">(
    chart.chart_type || "bar"
  );

  // Atualiza tipo quando novo gráfico for recebido
  React.useEffect(() => {
    if (currentChart?.chart_type) {
      setSelectedType(currentChart.chart_type);
    }
  }, [currentChart]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-chart-tooltip">
          <div className="tooltip-title">{label}</div>
          {payload.map((item: any, idx: number) => {
            const key = item.dataKey;
            const friendlyName = chart.series_labels?.[key] || key;
            return (
              <div key={idx} className="tooltip-item">
                <span style={{ color: item.color }}>● {friendlyName}:</span>
                <span className="tooltip-val">
                  {typeof item.value === "number" ? item.value.toLocaleString("pt-BR") : item.value}
                </span>
              </div>
            );
          })}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container-box">
      <div className="chart-header">
        <div>
          <h3 className="section-title">
            <BarChart3 size={18} color="#00f0ff" />
            {chart.title}
          </h3>
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Renderizado dinamicamente via Pydantic Schema + Recharts
          </span>
        </div>

        <div className="chart-type-selector">
          <button
            className={`type-toggle-btn ${selectedType === "bar" ? "active" : ""}`}
            onClick={() => setSelectedType("bar")}
            title="Gráfico de Barras"
          >
            <BarChart3 size={14} />
          </button>
          <button
            className={`type-toggle-btn ${selectedType === "line" ? "active" : ""}`}
            onClick={() => setSelectedType("line")}
            title="Gráfico de Linha"
          >
            <LineIcon size={14} />
          </button>
          <button
            className={`type-toggle-btn ${selectedType === "area" ? "active" : ""}`}
            onClick={() => setSelectedType("area")}
            title="Gráfico de Área"
          >
            <AreaIcon size={14} />
          </button>
          <button
            className={`type-toggle-btn ${selectedType === "pie" ? "active" : ""}`}
            onClick={() => setSelectedType("pie")}
            title="Gráfico de Pizza"
          >
            <PieIcon size={14} />
          </button>
        </div>
      </div>

      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          {selectedType === "bar" ? (
            <BarChart data={chart.data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey={chart.x_axis_key}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 12 }}
              />
              <YAxis stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: "12px", fontSize: "12px" }}
                formatter={(val) => chart.series_labels?.[val] || val}
              />
              {chart.data_keys.map((key, idx) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={COLORS[idx % COLORS.length]}
                  radius={[6, 6, 0, 0]}
                />
              ))}
            </BarChart>
          ) : selectedType === "line" ? (
            <LineChart data={chart.data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey={chart.x_axis_key}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 12 }}
              />
              <YAxis stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: "12px", fontSize: "12px" }}
                formatter={(val) => chart.series_labels?.[val] || val}
              />
              {chart.data_keys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={3}
                  dot={{ r: 5, fill: COLORS[idx % COLORS.length] }}
                />
              ))}
            </LineChart>
          ) : selectedType === "area" ? (
            <AreaChart data={chart.data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey={chart.x_axis_key}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 12 }}
              />
              <YAxis stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: "12px", fontSize: "12px" }}
                formatter={(val) => chart.series_labels?.[val] || val}
              />
              {chart.data_keys.map((key, idx) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  fill={COLORS[idx % COLORS.length]}
                  fillOpacity={0.25}
                />
              ))}
            </AreaChart>
          ) : (
            <PieChart>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: "12px", fontSize: "12px" }}
                formatter={(val) => chart.series_labels?.[val] || val}
              />
              <Pie
                data={chart.data}
                dataKey={chart.data_keys[0]}
                nameKey={chart.x_axis_key}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={95}
                paddingAngle={4}
              >
                {chart.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};
