"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Download, Play, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApplyClassifierDialog } from "./apply-classifier-dialog";
import { api, errorMessage } from "@/lib/api-client";
import { useProjectStore } from "@/stores/project-store";
import type { ClassifierMetadata, Project } from "@/types/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function ProjectList() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const queryClient = useQueryClient();
  const activeProject = useProjectStore((s) => s.activeProject);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteProjectTarget, setDeleteProjectTarget] = useState<Project | null>(null);
  const [deleteClassifierTarget, setDeleteClassifierTarget] = useState<
    { project: Project; classifier: ClassifierMetadata } | null
  >(null);
  const [applyTarget, setApplyTarget] = useState<
    { project: Project; classifier: ClassifierMetadata } | null
  >(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(token),
    enabled: !!token,
  });

  const deleteProject = useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId, token),
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      // If the deleted project was the active one, drop it so the Pipeline and
      // Visualiser force a fresh project selection.
      if (activeProject?.project_id === projectId) setActiveProject(null);
    },
    onError: (err) => setError(errorMessage(err, "Could not delete the project. Please try again.")),
    onSettled: () => setDeleteProjectTarget(null),
  });

  const deleteClassifier = useMutation({
    mutationFn: (vars: { projectId: string; classifierId: string }) =>
      api.deleteClassifier(vars.projectId, vars.classifierId, token),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      // The search form's topic facets are server-driven and per-project; refetch them
      // so the deleted classifier's subtopics disappear without a page refresh.
      queryClient.invalidateQueries({ queryKey: ["project-topics", vars.projectId] });
      // Keep the active project's snapshot in sync so the Visualiser topic picker
      // (which still reads activeProject.classifiers) drops it immediately too.
      if (activeProject?.project_id === vars.projectId) {
        setActiveProject({
          ...activeProject,
          classifiers: activeProject.classifiers.filter(
            (c) => c.classifier_id !== vars.classifierId,
          ),
        });
      }
    },
    onError: (err) => setError(errorMessage(err, "Could not delete the classifier. Please try again.")),
    onSettled: () => setDeleteClassifierTarget(null),
  });

  async function handleDownload(project: Project, classifier: ClassifierMetadata) {
    setError(null);
    setDownloadingId(classifier.classifier_id);
    try {
      const blob = await api.downloadClassifier(project.project_id, classifier.classifier_id, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${classifier.name}.bin`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorMessage(err, "Could not download the classifier. Please try again."));
    } finally {
      setDownloadingId(null);
    }
  }

  const projects = projectsQuery.data ?? [];

  if (projectsQuery.isLoading) {
    return <div className="rounded-lg border border-border bg-white p-6 text-sm text-muted-foreground">Loading projects…</div>;
  }
  if (projectsQuery.isError) {
    return <div className="rounded-lg border border-acteu-red/30 bg-acteu-red/5 p-6 text-sm text-acteu-red">{errorMessage(projectsQuery.error, "Could not load projects.")}</div>;
  }
  if (projects.length === 0) {
    return <div className="rounded-lg border border-border bg-white p-6 text-sm text-muted-foreground">No projects yet. Start a pipeline to create one.</div>;
  }

  return (
    <div className="space-y-4">
      {error && (
        <div role="alert" className="flex items-center justify-between rounded-md border border-acteu-red/30 bg-acteu-red/5 p-3 text-sm text-acteu-red">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss" className="font-medium">✕</button>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-white">
        {/* Header */}
        <div className="grid grid-cols-[1fr_140px_120px_44px] gap-3 border-b border-border px-4 py-2 text-xs font-medium uppercase text-muted-foreground">
          <span>Project</span>
          <span>Created</span>
          <span>Classifiers</span>
          <span className="sr-only">Actions</span>
        </div>

        <ul>
          {projects.map((project) => {
            const expanded = expandedId === project.project_id;
            return (
              <li key={project.project_id} className="border-b border-border last:border-0">
                <div className="grid grid-cols-[1fr_140px_120px_44px] items-center gap-3 px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expanded ? null : project.project_id)}
                    className="flex items-center gap-2 text-left font-medium text-ink"
                    aria-expanded={expanded}
                  >
                    {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    {project.name}
                  </button>
                  <span className="text-sm text-muted-foreground">{formatDate(project.created_at)}</span>
                  <span className="text-sm text-muted-foreground">{project.classifiers.length}</span>
                  <button
                    onClick={() => setDeleteProjectTarget(project)}
                    aria-label={`Delete project ${project.name}`}
                    className="text-muted-foreground hover:text-acteu-red"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                {expanded && (
                  <div className="bg-bg px-4 pb-4 pt-1">
                    {project.classifiers.length === 0 ? (
                      <p className="px-2 py-3 text-sm text-muted-foreground">
                        No classifiers trained in this project yet.
                      </p>
                    ) : (
                      <div className="overflow-hidden rounded-md border border-border bg-white">
                        <div className="grid grid-cols-[1fr_1.4fr_120px_120px] gap-3 border-b border-border px-3 py-2 text-xs font-medium uppercase text-muted-foreground">
                          <span>Name</span>
                          <span>Topics</span>
                          <span>Created</span>
                          <span className="text-right">Actions</span>
                        </div>
                        <ul>
                          {project.classifiers.map((classifier) => (
                            <li
                              key={classifier.classifier_id}
                              className="grid grid-cols-[1fr_1.4fr_120px_120px] items-center gap-3 border-b border-border px-3 py-2 last:border-0"
                            >
                              <span className="text-sm font-medium text-ink">{classifier.name}</span>
                              <div className="flex flex-wrap gap-1">
                                {classifier.topics.map((t) => (
                                  <span key={t.topic_id} className="rounded bg-bg px-1.5 py-0.5 text-xs text-ink">
                                    {t.name}
                                  </span>
                                ))}
                              </div>
                              <span className="text-sm text-muted-foreground">{formatDate(classifier.created_at)}</span>
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={() => setApplyTarget({ project, classifier })}
                                  aria-label={`Apply classifier ${classifier.name}`}
                                  title="Apply classifier"
                                  className="text-muted-foreground hover:text-acteu-red"
                                >
                                  <Play className="h-4 w-4" />
                                </button>
                                <button
                                  onClick={() => handleDownload(project, classifier)}
                                  disabled={downloadingId === classifier.classifier_id}
                                  aria-label={`Download classifier ${classifier.name}`}
                                  title="Download .bin"
                                  className="text-muted-foreground hover:text-ink disabled:opacity-40"
                                >
                                  <Download className="h-4 w-4" />
                                </button>
                                <button
                                  onClick={() => setDeleteClassifierTarget({ project, classifier })}
                                  aria-label={`Delete classifier ${classifier.name}`}
                                  title="Delete classifier"
                                  className="text-muted-foreground hover:text-acteu-red"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {/* Delete project confirmation */}
      <Dialog open={deleteProjectTarget !== null} onOpenChange={(o) => !o && setDeleteProjectTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete project</DialogTitle>
            <DialogDescription>
              Deleting this project will permanently remove all classifiers and document labels associated with it.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDeleteProjectTarget(null)}>Cancel</Button>
            <Button
              onClick={() => deleteProjectTarget && deleteProject.mutate(deleteProjectTarget.project_id)}
              disabled={deleteProject.isPending}
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete classifier confirmation */}
      <Dialog open={deleteClassifierTarget !== null} onOpenChange={(o) => !o && setDeleteClassifierTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete classifier</DialogTitle>
            <DialogDescription>
              This permanently removes the classifier, its model file, and every document label it produced.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDeleteClassifierTarget(null)}>Cancel</Button>
            <Button
              onClick={() =>
                deleteClassifierTarget &&
                deleteClassifier.mutate({
                  projectId: deleteClassifierTarget.project.project_id,
                  classifierId: deleteClassifierTarget.classifier.classifier_id,
                })
              }
              disabled={deleteClassifier.isPending}
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Apply classifier (Phase 2 labelling) */}
      {applyTarget && (
        <ApplyClassifierDialog
          key={applyTarget.classifier.classifier_id}
          project={applyTarget.project}
          classifier={applyTarget.classifier}
          open
          onOpenChange={(o) => !o && setApplyTarget(null)}
        />
      )}
    </div>
  );
}
