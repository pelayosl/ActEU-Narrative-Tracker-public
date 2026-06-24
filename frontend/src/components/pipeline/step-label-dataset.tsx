"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { JobProgress } from "./job-progress";
import { LabellingSummary } from "./labelling-summary";
import { SearchForm } from "./search-form";
import { api } from "@/lib/api-client";
import { useJob } from "@/lib/use-job";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useProjectStore } from "@/stores/project-store";
import { buildVisualiserPrefill, useVisualiserStore } from "@/stores/visualiser-store";
import type { ClassifierMetadata, LabellingResult, SearchQuery, Topic } from "@/types/api";

export function StepLabelDataset() {
  const router = useRouter();
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);

  const searchResult = usePipelineStore((s) => s.searchResult);
  const searchQuery = usePipelineStore((s) => s.searchQuery);
  const generatedTopics = usePipelineStore((s) => s.generatedTopics);
  const reconciledTopics = usePipelineStore((s) => s.reconciledTopics);
  const trainedClassifier = usePipelineStore((s) => s.trainedClassifier);
  const setTrainedClassifier = usePipelineStore((s) => s.setTrainedClassifier);
  const phase1Result = usePipelineStore((s) => s.phase1Result);
  const phase2Result = usePipelineStore((s) => s.phase2Result);
  const setPhase1Result = usePipelineStore((s) => s.setPhase1Result);
  const setPhase2Result = usePipelineStore((s) => s.setPhase2Result);
  const resumedDocCount = usePipelineStore((s) => s.resumedDocCount);
  const setStep = usePipelineStore((s) => s.setStep);
  const setPrefill = useVisualiserStore((s) => s.setPrefill);

  // Train on the reconciled topics if reconciliation ran, otherwise the raw list.
  const topics: Topic[] = reconciledTopics.length > 0 ? reconciledTopics : generatedTopics;
  // On a resumed pipeline the original searchResult is gone — fall back to the
  // document count derived from the topic_mapping.
  const docCount = searchResult?.retrieved_docs.length ?? resumedDocCount ?? 0;

  const [selected, setSelected] = useState<string[]>(() => topics.map((t) => t.topic_id));
  const [name, setName] = useState("");
  const [trainingJobId, setTrainingJobId] = useState<string | null>(null);
  const [phase2JobId, setPhase2JobId] = useState<string | null>(null);
  const [showPhase2Form, setShowPhase2Form] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trainingJob = useJob(trainingJobId);
  const phase2Job = useJob(phase2JobId);

  const trained = trainedClassifier !== null;
  const phase1Done = phase1Result !== null;

  // Resolve topic_id → name for the summary tables (topic_summary is keyed by id).
  const topicName = (id: string) =>
    trainedClassifier?.topics.find((t) => t.topic_id === id)?.name ?? id;

  // Keep showing the progress bar from dispatch until the classifier is stored
  // (or the job fails), so the form never flashes back between SUCCESS and store.
  const isTraining = trainingJobId !== null && !trained && trainingJob?.status !== "FAILURE";
  const phase2Running =
    phase2JobId !== null && (!phase2Job || (phase2Job.status !== "SUCCESS" && phase2Job.status !== "FAILURE"));

  // Training job completion
  useEffect(() => {
    if (!trainingJob) return;
    if (trainingJob.status === "SUCCESS") {
      setTrainedClassifier(trainingJob.result as unknown as ClassifierMetadata);
      setTrainingJobId(null);
    } else if (trainingJob.status === "FAILURE") {
      setError("Classifier training failed. Please try again.");
      setTrainingJobId(null);
    }
  }, [trainingJob, setTrainedClassifier]);

  // Phase 2 job completion
  useEffect(() => {
    if (!phase2Job) return;
    if (phase2Job.status === "SUCCESS") {
      setPhase2Result(phase2Job.result as unknown as LabellingResult);
      setPhase2JobId(null);
      setShowPhase2Form(false);
    } else if (phase2Job.status === "FAILURE") {
      setError("Custom query labelling failed. Please try again.");
      setPhase2JobId(null);
    }
  }, [phase2Job, setPhase2Result]);

  // Phase 1 — synchronous request
  const phase1 = useMutation({
    mutationFn: () =>
      api.applyPipelineLabels(
        activeProject!.project_id,
        trainedClassifier!.classifier_id,
        session?.accessToken,
      ),
    onSuccess: (res) => setPhase1Result(res),
    onError: () => setError("Labelling the retrieved documents failed. Please try again."),
  });

  function toggleTopic(topicId: string) {
    setSelected((prev) =>
      prev.includes(topicId) ? prev.filter((id) => id !== topicId) : [...prev, topicId],
    );
  }

  async function handleTrain() {
    if (!activeProject || !canTrain) return;
    setError(null);
    const selectedTopics = topics.filter((t) => selected.includes(t.topic_id));
    try {
      const { job_id } = await api.trainClassifier(
        activeProject.project_id,
        name.trim(),
        selectedTopics,
        session?.accessToken,
      );
      setTrainingJobId(job_id);
    } catch {
      setError("Could not start training. Please try again.");
    }
  }

  async function handlePhase2(query: SearchQuery) {
    if (!activeProject || !trainedClassifier) return;
    setError(null);
    try {
      const { job_id } = await api.labelByQuery(
        activeProject.project_id,
        trainedClassifier.classifier_id,
        query,
        session?.accessToken,
      );
      setPhase2JobId(job_id);
    } catch {
      setError("Could not start custom query labelling. Please try again.");
    }
  }

  const canTrain = selected.length > 0 && name.trim().length > 0 && !isTraining;

  return (
    <div className="space-y-6">
      {error && (
        <div
          role="alert"
          className="flex items-center justify-between rounded-md border border-acteu-red/30 bg-acteu-red/5 p-3 text-sm text-acteu-red"
        >
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss" className="font-medium">
            ✕
          </button>
        </div>
      )}

      {/* 3a — Train Classifier */}
      <section className="rounded-lg border border-border bg-white p-6">
        <h2 className="mb-1 text-lg font-semibold text-ink">Train Classifier</h2>

        {isTraining ? (
          <JobProgress
            progress={trainingJob?.progress ?? 0}
            step={trainingJob?.result.step as string | undefined}
            fallback="Training FastText classifier…"
          />
        ) : trained ? (
          <div className="mt-2 flex items-center gap-2 rounded-md border border-green-600/30 bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
            <CheckCircle2 className="h-4 w-4" />
            Classifier &ldquo;{trainedClassifier!.name}&rdquo; trained successfully.
          </div>
        ) : (
          <div className="space-y-5">
            <p className="text-sm text-muted-foreground">
              Ready to train on <strong>{docCount.toLocaleString()}</strong> document
              {docCount === 1 ? "" : "s"} with <strong>{selected.length}</strong> topic
              {selected.length === 1 ? "" : "s"}.
            </p>

            <fieldset className="space-y-2">
              <legend className="mb-1 text-sm font-medium text-ink">Topics to include</legend>
              {topics.length === 0 ? (
                <p className="text-sm text-muted-foreground">No topics available to train on.</p>
              ) : (
                <ul className="space-y-1">
                  {topics.map((t) => (
                    <li key={t.topic_id} className="flex items-start gap-2">
                      <input
                        id={`train-${t.topic_id}`}
                        type="checkbox"
                        className="mt-1 accent-acteu-red"
                        checked={selected.includes(t.topic_id)}
                        onChange={() => toggleTopic(t.topic_id)}
                      />
                      <label htmlFor={`train-${t.topic_id}`} className="text-sm text-ink">
                        <span className="font-medium">{t.name}</span>
                        <span className="block text-xs text-muted-foreground">{t.description}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </fieldset>

            <div className="max-w-sm space-y-1">
              <Label htmlFor="classifier-name">
                Classifier name <span className="text-acteu-red">*</span>
              </Label>
              <Input
                id="classifier-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Gender Issues — Spain 2023"
              />
            </div>

            <Button onClick={handleTrain} disabled={!canTrain}>
              Train Classifier
            </Button>
          </div>
        )}
      </section>

      {/* 3b — Label Documents */}
      {trained && !phase1Done && (
        <>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col rounded-lg border border-border bg-white p-6">
              <h3 className="mb-2 font-semibold text-ink">Label Retrieved Documents</h3>
              <p className="mb-4 flex-1 text-sm text-muted-foreground">
                Apply topics to the {docCount.toLocaleString()} documents from your current search.
              </p>
              {phase1.isPending ? (
                <JobProgress progress={0} fallback="Applying labels to retrieved documents…" />
              ) : (
                <Button onClick={() => phase1.mutate()}>Label</Button>
              )}
            </div>

            {/* Phase 2 is locked until Phase 1 completes. */}
            <div className="flex flex-col rounded-lg border border-border bg-white p-6 opacity-60" aria-disabled>
              <h3 className="mb-2 font-semibold text-ink">Label Custom Query</h3>
              <p className="mb-4 flex-1 text-sm text-muted-foreground">
                Define a new query to label a broader set of documents.
              </p>
              <Button variant="outline" disabled>
                Define Query
              </Button>
            </div>
          </section>

          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Lock className="h-3.5 w-3.5" />
            Label the retrieved documents first to unlock custom-query labelling.
          </p>
        </>
      )}

      {!trained && (
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Lock className="h-3.5 w-3.5" />
          Train a classifier above to enable labelling.
        </p>
      )}

      {/* Phase 1 results + Phase 2 (custom query) + pipeline completion */}
      {phase1Done && (
        <>
          <LabellingSummary
            title="Labelling Summary — Original Query"
            bannerLabel="labelled from original query"
            result={phase1Result}
            topicName={topicName}
          />

          <section className="rounded-lg border border-border bg-white p-6">
            <h3 className="mb-1 font-semibold text-ink">Label Additional Documents</h3>
            <p className="mb-4 text-sm text-muted-foreground">
              Optionally define a new query to label additional documents with the trained classifier.
            </p>

            {phase2Running ? (
              <JobProgress
                progress={phase2Job?.progress ?? 0}
                step={phase2Job?.result.step as string | undefined}
                fallback="Labelling documents with the classifier…"
              />
            ) : showPhase2Form ? (
              <SearchForm
                compact
                submitLabel="Run Labelling"
                loading={phase2Running}
                onSubmit={handlePhase2}
              />
            ) : (
              <Button variant="outline" onClick={() => setShowPhase2Form(true)}>
                Define New Query
              </Button>
            )}
          </section>

          {phase2Result && (
            <LabellingSummary
              title="Labelling Summary — Custom Query"
              bannerLabel="labelled from custom query"
              result={phase2Result}
              topicName={topicName}
            />
          )}

          <section className="rounded-lg border border-acteu-red/30 bg-acteu-red/5 p-6">
            <h3 className="mb-1 font-semibold text-ink">Pipeline Complete</h3>
            <p className="mb-4 text-sm text-muted-foreground">
              Ready to explore your results? Head to the Visualiser to analyse topic evolution,
              compare languages and platforms, and discover key entities.
            </p>
            <Button
              onClick={() => {
                setPrefill(buildVisualiserPrefill(searchQuery, trainedClassifier));
                router.push("/visualiser");
              }}
            >
              Go to Visualiser <ArrowRight className="ml-1.5 h-4 w-4" />
            </Button>
          </section>
        </>
      )}

      {/* Exit the pipeline back to the search form. Like the cancel buttons on the
          earlier steps, but lands on search rather than the previous step. The
          pending pipeline still resumes here on re-entry (until phase 1 labelling). */}
      <div>
        <Button variant="primary" size="lg" onClick={() => setStep("search")}>
          Exit the pipeline
        </Button>
      </div>
    </div>
  );
}
