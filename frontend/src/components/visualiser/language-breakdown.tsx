/**
 * Grouped bar chart comparing topic presence across languages.
 *
 * @packageDocumentation
 */
"use client";

import { useMemo } from "react";
import { Languages } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TopicLanguageBreakdown } from "@/types/api";
import type { TopicSeriesMeta } from "./topic-colors";

/** Props for {@link LanguageBreakdown}. */
interface LanguageBreakdownProps {
  /** Per-topic language counts. */
  data: TopicLanguageBreakdown[];
  /** Topic display metadata (value, label, colour) for legend and bars. */
  topics: TopicSeriesMeta[];
}

/**
 * Grouped horizontal bar chart: one row per language, one bar per topic.
 *
 * Language codes are rendered as display names where possible, and the per-topic
 * counts are pivoted so each language row carries a value per topic.
 *
 * @param props - See {@link LanguageBreakdownProps}.
 */
export function LanguageBreakdown({ data, topics }: LanguageBreakdownProps) {
  const languageLabel = useMemo(() => {
    try {
      const display = new Intl.DisplayNames(["en"], { type: "language" });
      return (code: string) => display.of(code) ?? code;
    } catch {
      return (code: string) => code;
    }
  }, []);

  const rows = useMemo(() => {
    const byLanguage = new Map<string, Record<string, string | number>>();
    for (const tb of data) {
      for (const { language, count } of tb.counts) {
        const row = byLanguage.get(language) ?? { language: languageLabel(language) };
        row[tb.topic] = count;
        byLanguage.set(language, row);
      }
    }
    return [...byLanguage.values()];
  }, [data, languageLabel]);

  return (
    <section className="rounded-lg border border-border bg-white p-6">
      <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
        <Languages className="h-4 w-4 text-acteu-red" />
        Topic Presence by Language
      </h2>
      {rows.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No documents matched these parameters.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 56)}>
          <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9CA3AF" />
            <YAxis
              type="category"
              dataKey="language"
              tick={{ fontSize: 12 }}
              stroke="#9CA3AF"
              width={80}
            />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} cursor={{ fill: "#F5F5F5" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {topics.map((t) => (
              <Bar key={t.value} dataKey={t.value} name={t.label} fill={t.color} radius={[0, 2, 2, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
