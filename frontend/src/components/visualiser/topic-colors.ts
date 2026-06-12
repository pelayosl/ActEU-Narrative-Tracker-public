// Stable colour assignment for topics, shared across all visualiser charts so a
// topic keeps the same colour everywhere. First three match the mockup (red, ink, grey).
export const TOPIC_COLORS = [
  "#C8102E", // ActEU red
  "#1A1A1A", // ink
  "#6B7280", // grey
  "#2563EB", // blue
  "#059669", // green
  "#D97706", // amber
  "#7C3AED", // violet
  "#DB2777", // pink
];

// A query topic resolved for charting: its submitted identifier, display name, colour.
export interface TopicSeriesMeta {
  value: string; // core label or subtopic topic_id, matches Dashboard `topic` fields
  label: string; // display name
  color: string;
}
