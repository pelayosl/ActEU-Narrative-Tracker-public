"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";
import { useProjectStore } from "@/stores/project-store";
import { cn } from "@/lib/utils";

type Mode = "select" | "create";

export function ProjectSelectorDialog() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<Mode>("select");
  const [selectedId, setSelectedId] = useState("");
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(token),
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => api.createProject(name, token),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setActiveProject(project);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Failed to create project.");
    },
  });

  const projects = projectsQuery.data ?? [];

  function openExisting() {
    setError(null);
    const project = projects.find((p) => p.project_id === selectedId);
    if (!project) {
      setError("Please choose a project.");
      return;
    }
    setActiveProject(project);
  }

  function submitCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const trimmed = newName.trim();
    if (!trimmed) {
      setError("Project name cannot be empty.");
      return;
    }
    createMutation.mutate(trimmed);
  }

  return (
    <div className="mx-auto max-w-md rounded-lg border border-border bg-white p-6 shadow-sm">
      <div className="mb-1 flex items-center gap-2">
        <FolderOpen className="h-5 w-5 text-acteu-red" />
        <h2 className="text-lg font-semibold text-ink">Select Project</h2>
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        The pipeline runs within a project context. Select an existing project or create a new one.
      </p>

      <div className="mb-4 flex gap-2">
        <ModeButton active={mode === "select"} onClick={() => { setMode("select"); setError(null); }}>
          Select Existing
        </ModeButton>
        <ModeButton active={mode === "create"} onClick={() => { setMode("create"); setError(null); }}>
          + Create New
        </ModeButton>
      </div>

      {mode === "select" ? (
        <div className="space-y-3">
          <Label htmlFor="existing-project">Existing Projects</Label>
          <select
            id="existing-project"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={projectsQuery.isLoading || projects.length === 0}
            className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm text-ink outline-none focus:border-acteu-red focus:ring-1 focus:ring-acteu-red disabled:opacity-50"
          >
            <option value="">
              {projectsQuery.isLoading
                ? "Loading…"
                : projects.length === 0
                  ? "No projects yet — create one"
                  : "Choose a project…"}
            </option>
            {projects.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name}
              </option>
            ))}
          </select>
          {projectsQuery.isError && (
            <p className="text-sm text-acteu-red">Could not load projects.</p>
          )}
          {error && <p className="text-sm text-acteu-red">{error}</p>}
          <Button onClick={openExisting} disabled={!selectedId} className="w-full">
            Open Project
          </Button>
        </div>
      ) : (
        <form onSubmit={submitCreate} className="space-y-3">
          <div>
            <Label htmlFor="new-project-name">Project Name</Label>
            <Input
              id="new-project-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Rubiales narrative study"
              autoFocus
              required
            />
          </div>
          {error && <p className="text-sm text-acteu-red">{error}</p>}
          <Button
            type="submit"
            className="w-full"
            disabled={createMutation.isPending || !newName.trim()}
          >
            {createMutation.isPending ? "Creating…" : "Create Project"}
          </Button>
        </form>
      )}
    </div>
  );
}

function ModeButton({ active, onClick, children }: Readonly<{
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}>) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-acteu-red text-white"
          : "border border-border bg-white text-ink hover:bg-bg",
      )}
    >
      {children}
    </button>
  );
}
