"use client";

import { Button } from "@/components/ui/button";

// TODO: fields — keywords (csv), date range, countries multi-select, platforms multi-select,
// topics multi-select, subtopics (dynamic from topics). Validate date_from <= date_to.
// Accept `compact` prop for reuse inside Apply Classifier dialog and Label Custom Query.
export function SearchForm({ compact: _compact = false }: { compact?: boolean } = {}) {
  return (
    <form className="rounded-lg border border-border bg-white p-6">
      <p className="text-sm text-muted-foreground">Search form placeholder.</p>
      <Button type="submit" className="mt-4">Search</Button>
    </form>
  );
}
