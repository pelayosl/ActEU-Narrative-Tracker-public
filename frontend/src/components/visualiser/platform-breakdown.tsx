"use client";

import { useMemo } from "react";
import { Share2 } from "lucide-react";
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
import type { TopicPlatformBreakdown } from "@/types/api";
import type { TopicSeriesMeta } from "./topic-colors";

interface PlatformBreakdownProps {
  data: TopicPlatformBreakdown[];
  topics: TopicSeriesMeta[];
}

const PLATFORM_LABELS: Record<string, string> = {
  twitter: "Twitter",
  telegram: "Telegram",
  media: "Online Media",
};

// Grouped horizontal bars: one row per platform, one bar per topic. Counts are
// pivoted so each row carries a value per topic.
export function PlatformBreakdown({ data, topics }: PlatformBreakdownProps) {
  const rows = useMemo(() => {
    const byPlatform = new Map<string, Record<string, string | number>>();
    for (const tb of data) {
      for (const { platform, count } of tb.counts) {
        const row = byPlatform.get(platform) ?? { platform: PLATFORM_LABELS[platform] ?? platform };
        row[tb.topic] = count;
        byPlatform.set(platform, row);
      }
    }
    return [...byPlatform.values()];
  }, [data]);

  return (
    <section className="rounded-lg border border-border bg-white p-6">
      <h2 className="mb-4 flex items-center gap-2 font-semibold text-ink">
        <Share2 className="h-4 w-4 text-acteu-red" />
        Topic Presence by Platform
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
              dataKey="platform"
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
