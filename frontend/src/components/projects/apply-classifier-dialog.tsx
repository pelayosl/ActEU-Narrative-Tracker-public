/**
 * Dialog that applies a trained classifier to a fresh query (Phase-2 labelling).
 *
 * @packageDocumentation
 */
"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SearchForm } from "@/components/pipeline/search-form";
import { JobProgress } from "@/components/pipeline/job-progress";
import { LabellingSummary } from "@/components/pipeline/labelling-summary";
import { api, errorMessage } from "@/lib/api-client";
import { useJob } from "@/lib/use-job";
import type { ClassifierMetadata, LabellingResult, Project, SearchQuery } from "@/types/api";

/** Props for {@link ApplyClassifierDialog}. */
interface ApplyClassifierDialogProps {
  /** The project owning the classifier. */
  project: Project;
  /** The classifier to run over the new query. */
  classifier: ClassifierMetadata;
  /** Whether the dialog is visible. */
  open: boolean;
  /** Callback to open/close the dialog. */
  onOpenChange: (open: boolean) => void;
}

/**
 * Run Phase-2 labelling from the Project Library.
 *
 * Shows a compact {@link SearchForm}; on submit it starts an async labelling job
 * for the classifier over the chosen query, streams progress via {@link useJob},
 * and renders a {@link LabellingSummary} once the job succeeds.
 *
 * @param props - See {@link ApplyClassifierDialogProps}.
 */
export function ApplyClassifierDialog({ project, classifier, open, onOpenChange }: ApplyClassifierDialogProps) {
  const { data: session } = useSession();
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<LabellingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const job = useJob(jobId);
  const running = jobId !== null && (!job || (job.status !== "SUCCESS" && job.status !== "FAILURE"));

  useEffect(() => {
    if (!job) return;
    if (job.status === "SUCCESS") {
      setResult(job.result as unknown as LabellingResult);
      setJobId(null);
    } else if (job.status === "FAILURE") {
      setError("Labelling failed. Please try again.");
      setJobId(null);
    }
  }, [job]);

  const topicName = (id: string) =>
    classifier.topics.find((t) => t.topic_id === id)?.name ?? id;

  async function handleRun(query: SearchQuery) {
    setError(null);
    try {
      const { job_id } = await api.labelByQuery(
        project.project_id,
        classifier.classifier_id,
        query,
        session?.accessToken,
      );
      setJobId(job_id);
    } catch (err) {
      setError(errorMessage(err, "Could not start labelling. Please try again."));
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Apply Classifier</DialogTitle>
          <DialogDescription>
            Label a new set of documents with &ldquo;{classifier.name}&rdquo;.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div role="alert" className="mb-3 rounded-md border border-acteu-red/30 bg-acteu-red/5 p-3 text-sm text-acteu-red">
            {error}
          </div>
        )}

        {result ? (
          <LabellingSummary
            title="Labelling Summary"
            bannerLabel="labelled with this classifier"
            result={result}
            topicName={topicName}
          />
        ) : running ? (
          <JobProgress
            progress={job?.progress ?? 0}
            step={job?.result.step as string | undefined}
            fallback="Labelling documents with the classifier…"
          />
        ) : (
          <SearchForm compact submitLabel="Run Labelling" loading={running} onSubmit={handleRun} />
        )}
      </DialogContent>
    </Dialog>
  );
}
