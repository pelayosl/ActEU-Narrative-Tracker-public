/**
 * Pipeline Step 2: review, edit, merge and reconcile generated topics.
 *
 * @packageDocumentation
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { GitMerge } from "lucide-react";
import { TopicCard } from "./topic-card";
import { MergeDialog } from "./merge-dialog";
import { JobProgress } from "./job-progress";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { useJob } from "@/lib/use-job";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useProjectStore } from "@/stores/project-store";
import type { Topic } from "@/types/api";

/**
 * The generation ids a topic resolves to (its origins, or its own id if raw).
 *
 * @param topic - The topic to resolve.
 * @returns The generation ids backing this topic.
 */
function generationIds(topic: Topic): string[] {
  return topic.origin_topic_ids.length > 0 ? topic.origin_topic_ids : [topic.topic_id];
}

/**
 * Topic-modelling step spanning generation and reconciliation.
 *
 * Streams the BERTopic generation and LLM reconciliation jobs via
 * {@link useJob}, showing a {@link JobProgress} bar while each runs. Between
 * jobs it lists editable {@link TopicCard}s: raw topics can be renamed, deleted
 * or merged (via {@link MergeDialog}); reconciliation can target a selection or
 * all topics, with unselected ones passed through unchanged. Reconciled topics
 * show what they fuse and split back into constituents on delete. From here the
 * user accepts topics (advancing to labelling), skips reconciliation, or cancels.
 * Surfaces informational notices such as the LLM being unavailable.
 */
export function StepTopicModelling() {
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);

  const generated = usePipelineStore((s) => s.generatedTopics);
  const reconciled = usePipelineStore((s) => s.reconciledTopics);
  const preReconcile = usePipelineStore((s) => s.preReconcileTopics);
  const subStep = usePipelineStore((s) => s.topicSubStep);
  const generationJobId = usePipelineStore((s) => s.generationJobId);
  const reconciliationJobId = usePipelineStore((s) => s.reconciliationJobId);

  const setStep = usePipelineStore((s) => s.setStep);
  const setTopicSubStep = usePipelineStore((s) => s.setTopicSubStep);
  const setGeneratedTopics = usePipelineStore((s) => s.setGeneratedTopics);
  const setReconciledTopics = usePipelineStore((s) => s.setReconciledTopics);
  const setGenerationJobId = usePipelineStore((s) => s.setGenerationJobId);
  const setReconciliationJobId = usePipelineStore((s) => s.setReconciliationJobId);
  const updateGeneratedTopic = usePipelineStore((s) => s.updateGeneratedTopic);
  const deleteGeneratedTopic = usePipelineStore((s) => s.deleteGeneratedTopic);
  const mergeGeneratedTopics = usePipelineStore((s) => s.mergeGeneratedTopics);
  const updateReconciledTopic = usePipelineStore((s) => s.updateReconciledTopic);
  const splitReconciledTopic = usePipelineStore((s) => s.splitReconciledTopic);
  const beginReconciliation = usePipelineStore((s) => s.beginReconciliation);
  const cancelReconciliation = usePipelineStore((s) => s.cancelReconciliation);

  const [selected, setSelected] = useState<string[]>([]);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Informational (non-error) message, e.g. when the LLM was unavailable.
  const [notice, setNotice] = useState<string | null>(null);

  const genJob = useJob(subStep === "generating" ? generationJobId : null);
  const recJob = useJob(subStep === "reconciling" ? reconciliationJobId : null);

  // Generation job completion
  useEffect(() => {
    if (subStep !== "generating" || !genJob) return;
    if (genJob.status === "SUCCESS") {
      const topics = (genJob.result.topics as Topic[]) ?? [];
      setGeneratedTopics(topics);
      setGenerationJobId(null);
      setTopicSubStep("generated");
      // Topics still load, but with raw BERTopic labels — inform the user.
      setNotice(
        genJob.result.llm_available === false
          ? "LLM unavailable for producing comprehensible labels, using standard BERTopic labels"
          : null,
      );
    } else if (genJob.status === "FAILURE") {
      setError("Topic generation failed. Please try again from the search step.");
      setGenerationJobId(null);
      setTopicSubStep("generated");
    }
  }, [genJob, subStep, setGeneratedTopics, setGenerationJobId, setTopicSubStep]);

  // Reconciliation job completion
  useEffect(() => {
    if (subStep !== "reconciling" || !recJob) return;
    if (recJob.status === "SUCCESS") {
      if (recJob.result.llm_available === false) {
        // Reconciliation did not run — stay at the editing step so the user can
        // retry or skip; do not advance to the reconciled view.
        setNotice("LLM unavailable: please try again later or skip reconciliation");
        setReconciliationJobId(null);
        setTopicSubStep("generated");
        return;
      }
      const topics = (recJob.result.topics as Topic[]) ?? [];
      setReconciledTopics(topics);
      setReconciliationJobId(null);
      setTopicSubStep("reconciled");
    } else if (recJob.status === "FAILURE") {
      setError("Reconciliation failed. Please try again.");
      setReconciliationJobId(null);
      setTopicSubStep("generated");
    }
  }, [recJob, subStep, setReconciledTopics, setReconciliationJobId, setTopicSubStep]);

  // Map generation ids → the pre-reconciliation card that owns them, for the
  // "Fuses:" label on reconciled cards.
  const topicByGenerationId = useMemo(() => {
    const map = new Map<string, Topic>();
    for (const t of preReconcile) {
      for (const id of generationIds(t)) map.set(id, t);
    }
    return map;
  }, [preReconcile]);

  function fusesLabel(topic: Topic): string | undefined {
    // Only label genuine LLM fusions of 2+ distinct pre-reconciliation cards.
    // A manually merged card carries several generation ids but resolves to a
    // single source card, so it must not show a (self-referential) "Fuses" label.
    const sources = new Set(
      topic.origin_topic_ids.map((id) => topicByGenerationId.get(id)?.topic_id ?? id),
    );
    if (sources.size < 2) return undefined;
    const names = [
      ...new Set(topic.origin_topic_ids.map((id) => topicByGenerationId.get(id)?.name ?? "?")),
    ];
    return names.join(" + ");
  }

  async function handleReconcile() {
    if (!activeProject) return;
    setError(null);
    setNotice(null);
    // No selection → reconcile every topic. A selection → reconcile only those,
    // passing the rest through unchanged so they survive in the final list.
    const hasSelection = selected.length > 0;
    const toReconcile = hasSelection ? generated.filter((t) => selected.includes(t.topic_id)) : generated;
    const passthrough = hasSelection ? generated.filter((t) => !selected.includes(t.topic_id)) : [];
    try {
      const { job_id } = await api.reconcileTopics(
        activeProject.project_id,
        toReconcile,
        session?.accessToken,
        passthrough,
      );
      beginReconciliation(job_id);
    } catch {
      setError("Could not start reconciliation. Please try again.");
    }
  }

  function toggleSelect(topicId: string) {
    setSelected((prev) =>
      prev.includes(topicId) ? prev.filter((id) => id !== topicId) : [...prev, topicId],
    );
  }

  // --- Loading states (2a / start of 2c) ---
  if (subStep === "generating") {
    return (
      <JobProgress
        progress={genJob?.progress ?? 0}
        step={genJob?.result.step as string | undefined}
        fallback="Running BERTopic… this may take a few minutes."
      />
    );
  }
  if (subStep === "reconciling") {
    return (
      <JobProgress
        progress={recJob?.progress ?? 0}
        step={recJob?.result.step as string | undefined}
        fallback="Reconciling topics with the LLM…"
      />
    );
  }

  const isReconciled = subStep === "reconciled";
  const topics = isReconciled ? reconciled : generated;
  const selectedTopics = generated.filter((t) => selected.includes(t.topic_id));

  return (
    <div className="space-y-4">
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

      {notice && (
        <div className="flex items-center justify-between rounded-md border border-amber-500/30 bg-amber-50 p-3 text-sm text-amber-800">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} aria-label="Dismiss" className="font-medium">
            ✕
          </button>
        </div>
      )}

      {!isReconciled && (
        <>
          <div className="rounded-md bg-bg px-3 py-2 text-sm text-ink">
            <strong>{topics.length} topics</strong> generated from BERTopic analysis
          </div>
          <Button
            variant="outline"
            disabled={selected.length < 2}
            onClick={() => setMergeOpen(true)}
          >
            <GitMerge className="mr-1.5 h-4 w-4" />
            Merge Selected ({selected.length})
          </Button>
        </>
      )}

      {topics.length === 0 ? (
        <div className="rounded-md border border-border bg-white p-6 text-center text-sm text-muted-foreground">
          No topics were generated. Try a broader search.
        </div>
      ) : (
        <ul className="space-y-2">
          {topics.map((t, i) => (
            <TopicCard
              key={t.topic_id}
              topic={t}
              index={i + 1}
              reconciled={isReconciled}
              selected={selected.includes(t.topic_id)}
              onToggleSelect={() => toggleSelect(t.topic_id)}
              fusesLabel={isReconciled ? fusesLabel(t) : undefined}
              onEdit={(name, description) =>
                isReconciled
                  ? updateReconciledTopic(t.topic_id, name, description)
                  : updateGeneratedTopic(t.topic_id, name, description)
              }
              onDelete={() =>
                isReconciled
                  ? splitReconciledTopic(t.topic_id)
                  : deleteGeneratedTopic(t.topic_id)
              }
            />
          ))}
        </ul>
      )}

      {isReconciled ? (
        <div className="flex gap-2">
          <Button onClick={() => setStep("label")}>Accept Topics</Button>
          <Button variant="ghost" onClick={cancelReconciliation}>
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {/* A single selected topic has nothing to reconcile against. */}
          <Button disabled={topics.length === 0 || selected.length === 1} onClick={handleReconcile}>
            {selected.length >= 2 ? `Reconcile Selected (${selected.length})` : "Reconcile Topics"}
          </Button>
          <Button variant="outline" disabled={topics.length === 0} onClick={() => setStep("label")}>
            Skip to Labelling →
          </Button>
          <Button variant="ghost" onClick={() => setStep("search")}>
            Cancel
          </Button>
        </div>
      )}

      <MergeDialog
        open={mergeOpen}
        onOpenChange={setMergeOpen}
        topics={selectedTopics}
        onConfirm={(name, description) => {
          mergeGeneratedTopics(selected, name, description);
          setSelected([]);
        }}
      />
    </div>
  );
}
