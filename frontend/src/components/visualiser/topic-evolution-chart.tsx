"use client";

import { useMemo } from "react";
import { TrendingUp } from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TopicTimeSeries } from "@/types/api";
import type { TopicSeriesMeta } from "./topic-colors";

interface TopicEvolutionChartProps {
  data: TopicTimeSeries[];
  topics: TopicSeriesMeta[];
}

// One line per topic: X = day, Y = document count. Series are merged into a single
// row per date, keyed by topic value, so missing days render as gaps.
export function TopicEvolutionChart({ data, topics }: TopicEvolutionChartProps) {
  const rows = useMemo(() => {
    const byDate = new Map<string, Record<string, string | number>>();
    for (const ts of data) {
      for (const point of ts.series) {
        const row = byDate.get(point.date) ?? { date: point.date };
        row[ts.topic] = point.count;
        byDate.set(point.date, row);
      }
    }
    return [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [data]);

  return (
    <section className="rounded-lg border border-border bg-white p-6">
      <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
        <TrendingUp className="h-4 w-4 text-acteu-red" />
        Topic Presence Over Time
      </h2>
      {rows.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No documents matched these parameters.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9CA3AF" minTickGap={24} />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="#9CA3AF"
              label={{ value: "Document Count", angle: -90, position: "insideLeft", style: { fontSize: 12, fill: "#6B7280" } }}
            />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {topics.map((t) => (
              <Line
                key={t.value}
                type="monotone"
                dataKey={t.value}
                name={t.label}
                stroke={t.color}
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
