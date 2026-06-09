"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { SearchForm } from "./search-form";
import { DocumentCard } from "./document-card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useProjectStore } from "@/stores/project-store";
import type { SearchQuery } from "@/types/api";

export function StepSearch() {
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);

  const result = usePipelineStore((s) => s.searchResult);
  const setSearchQuery = usePipelineStore((s) => s.setSearchQuery);
  const setSearchResult = usePipelineStore((s) => s.setSearchResult);
  const setStep = usePipelineStore((s) => s.setStep);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  const search = useMutation({
    mutationFn: (query: SearchQuery) =>
      api.search(query, session?.accessToken, activeProject?.project_id),
    onSuccess: (data, query) => {
      setSearchQuery(query);
      setSearchResult(data);
      setSelectedId(data.retrieved_docs[0]?.doc_id ?? null);
    },
  });

  const selectedDoc = result?.retrieved_docs.find((d) => d.doc_id === selectedId) ?? null;

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

          {result.retrieved_docs.length === 0 ? (
            <div className="rounded-md border border-border bg-white p-6 text-center text-sm text-muted-foreground">
              No documents matched your search parameters.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                <p className="text-sm font-medium text-ink">Document Results</p>
                {result.retrieved_docs.map((doc) => (
                  <DocumentCard
                    key={doc.doc_id}
                    doc={doc}
                    selected={doc.doc_id === selectedId}
                    onClick={() => setSelectedId(doc.doc_id)}
                  />
                ))}
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-ink">Document Preview</p>
                {selectedDoc ? (
                  <div className="rounded-md border border-border bg-white p-4">
                    <div className="mb-2 flex items-center gap-2 text-xs">
                      <span className="rounded bg-bg px-2 py-0.5 font-medium uppercase">
                        {selectedDoc.platform}
                      </span>
                      <span className="uppercase text-muted-foreground">{selectedDoc.language}</span>
                      <span className="text-muted-foreground">·</span>
                      <span className="text-muted-foreground">
                        {new Date(selectedDoc.date).toLocaleDateString()}
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

          {result.retrieved_docs.length > 0 && (
            <Button onClick={() => setStep("topics")}>Generate Topics →</Button>
          )}
        </div>
      )}
    </div>
  );
}
