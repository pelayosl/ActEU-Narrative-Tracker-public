"use client";

// TODO: modal with two options — select existing project (dropdown) or create new (text input, non-empty).
// On confirm, set the active project in useProjectStore.
export function ProjectSelectorDialog({ open: _open }: { open: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-white p-6">
      <h2 className="mb-4 text-lg font-semibold text-ink">Select or create a project</h2>
      <p className="text-sm text-muted-foreground">Project selector placeholder.</p>
    </div>
  );
}
