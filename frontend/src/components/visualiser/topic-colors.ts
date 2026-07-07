/**
 * Shared topic colour palette and the chart-series metadata type.
 *
 * @packageDocumentation
 */

/**
 * Stable colour assignment for topics, shared across all visualiser charts so a
 * topic keeps the same colour everywhere. Indexed by the topic's position in the
 * query; the first three match the mockup (red, ink, grey).
 */
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

/** A query topic resolved for charting: submitted identifier, display name, colour. */
export interface TopicSeriesMeta {
  /** Core label or subtopic `topic_id`; matches the Dashboard `topic` fields. */
  value: string;
  /** Human-readable name shown in legends and tooltips. */
  label: string;
  /** Hex colour assigned from {@link TOPIC_COLORS}. */
  color: string;
}
