"use client";

import { SearchForm } from "./search-form";
import { DocumentCard } from "./document-card";
import { Button } from "@/components/ui/button";
import { usePipelineStore } from "@/stores/pipeline-store";

// TODO: wire SearchForm onSubmit → api.search → setSearchResult.
// Show summary bar, document list, preview panel, then "Generate Topics →".
export function StepSearch() {
  const result = usePipelineStore((s) => s.searchResult);
  const setStep = usePipelineStore((s) => s.setStep);

  return (
    <div className="space-y-6">
      <SearchForm />
      {result && (
        <div className="space-y-4">
          <div className="rounded-md border border-border bg-white p-3 text-sm">
            <strong>{result.total_docs.toLocaleString()}</strong> documents retrieved
          </div>
          <div className="space-y-2">
            {result.retrieved_docs.map((doc) => (
              <DocumentCard key={doc.doc_id} doc={doc} />
            ))}
          </div>
          <Button onClick={() => setStep("topics")}>Generate Topics →</Button>
        </div>
      )}
    </div>
  );
}
