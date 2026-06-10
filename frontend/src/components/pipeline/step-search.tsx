"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { SearchForm } from "./search-form";
import { DocumentCard } from "./document-card";
import { PlatformBadge } from "./platform-badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useProjectStore } from "@/stores/project-store";
import type { SearchQuery } from "@/types/api";

const PAGE_SIZE = 10;

// Windowed page list: always first + last + current ±1, with "…" markers for larger gaps.
// A gap of exactly one page is filled with the number rather than an ellipsis.
// `page`/`total` are 1-indexed here. Returns numbers and ellipsis sentinels.
function getPageItems(page: number, total: number): (number | "ellipsis-left" | "ellipsis-right")[] {
  const shown = new Set<number>([1, total]);
  for (let i = page - 1; i <= page + 1; i++) {
    if (i >= 1 && i <= total) shown.add(i);
  }
  const sorted = [...shown].sort((a, b) => a - b);

  const items: (number | "ellipsis-left" | "ellipsis-right")[] = [];
  sorted.forEach((value, i) => {
    if (i > 0) {
      const prev = sorted[i - 1];
      if (value - prev === 2) {
        items.push(prev + 1);
      } else if (value - prev > 2) {
        items.push(value > page ? "ellipsis-right" : "ellipsis-left");
      }
    }
    items.push(value);
  });
  return items;
}

export function StepSearch() {
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);

  const result = usePipelineStore((s) => s.searchResult);
  const setSearchQuery = usePipelineStore((s) => s.setSearchQuery);
  const setSearchResult = usePipelineStore((s) => s.setSearchResult);
  const setStep = usePipelineStore((s) => s.setStep);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const search = useMutation({
    mutationFn: (query: SearchQuery) =>
      api.search(query, session?.accessToken, activeProject?.project_id),
    onSuccess: (data, query) => {
      setSearchQuery(query);
      setSearchResult(data);
      setPage(0);
      setSelectedId(data.retrieved_docs[0]?.doc_id ?? null);
    },
  });

  const docs = result?.retrieved_docs ?? [];
  const totalPages = Math.ceil(docs.length / PAGE_SIZE);
  const pageDocs = docs.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const selectedDoc = docs.find((d) => d.doc_id === selectedId) ?? null;

  function goToPage(next: number) {
    setPage(next);
    setSelectedId(docs[next * PAGE_SIZE]?.doc_id ?? null);
  }

  return (
    <div className="space-y-6">
      <SearchForm onSubmit={search.mutate} loading={search.isPending} />

      {search.isError && (
        <div className="rounded-md border border-acteu-red/30 bg-acteu-red/5 p-3 text-sm text-acteu-red">
          Search failed. Please try again.
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="rounded-md border border-border bg-white p-3 text-sm">
            <strong>{result.total_docs.toLocaleString()}</strong> documents retrieved
          </div>

          {docs.length === 0 ? (
            <div className="rounded-md border border-border bg-white p-6 text-center text-sm text-muted-foreground">
              No documents matched your search parameters.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-ink">Document Results</p>
                  {totalPages > 1 && (
                    <span className="text-xs text-muted-foreground">
                      Page {page + 1} of {totalPages}
                    </span>
                  )}
                </div>

                {pageDocs.map((doc) => (
                  <DocumentCard
                    key={doc.doc_id}
                    doc={doc}
                    selected={doc.doc_id === selectedId}
                    onClick={() => setSelectedId(doc.doc_id)}
                  />
                ))}

                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => goToPage(page - 1)}
                      disabled={page === 0}
                      className="rounded-md border border-border p-1.5 text-ink transition-colors hover:bg-bg disabled:cursor-not-allowed disabled:opacity-40"
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>

                    {getPageItems(page + 1, totalPages).map((item) =>
                      typeof item === "number" ? (
                        <button
                          key={item}
                          type="button"
                          onClick={() => goToPage(item - 1)}
                          className={`min-w-[2rem] rounded-md border px-2 py-1 text-xs font-medium transition-colors ${
                            item - 1 === page
                              ? "border-acteu-red bg-acteu-red text-white"
                              : "border-border bg-white text-ink hover:bg-bg"
                          }`}
                        >
                          {item}
                        </button>
                      ) : (
                        <span key={item} className="px-1 text-xs text-muted-foreground">
                          …
                        </span>
                      ),
                    )}

                    <button
                      type="button"
                      onClick={() => goToPage(page + 1)}
                      disabled={page === totalPages - 1}
                      className="rounded-md border border-border p-1.5 text-ink transition-colors hover:bg-bg disabled:cursor-not-allowed disabled:opacity-40"
                      aria-label="Next page"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-ink">Document Preview</p>
                {selectedDoc ? (
                  <div className="rounded-md border border-border bg-white p-4">
                    <div className="mb-2 flex items-center gap-2 text-xs">
                      <PlatformBadge platform={selectedDoc.platform} />
                      <span className="uppercase text-muted-foreground">{selectedDoc.language}</span>
                      <span className="text-muted-foreground">·</span>
                      <span className="text-muted-foreground">
                        {selectedDoc.date
                          ? new Date(selectedDoc.date).toLocaleDateString()
                          : "Unknown date"}
                      </span>
                    </div>
                    <h3 className="font-semibold text-ink">{selectedDoc.headline}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{selectedDoc.excerpt}</p>
                  </div>
                ) : (
                  <div className="rounded-md border border-border bg-white p-4 text-sm text-muted-foreground">
                    Select a document to preview it.
                  </div>
                )}
              </div>
            </div>
          )}

          {docs.length > 0 && (
            <Button onClick={() => setStep("topics")}>Generate Topics →</Button>
          )}
        </div>
      )}
    </div>
  );
}
