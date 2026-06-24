import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TopicCard } from "./topic-card";
import type { Topic } from "@/types/api";

const topic: Topic = {
  topic_id: "t-1",
  name: "Immigration",
  description: "Policies and debate",
  origin_topic_ids: [],
};

function renderCard(overrides = {}) {
  const onEdit = vi.fn();
  const onDelete = vi.fn();
  render(
    <TopicCard topic={topic} index={1} reconciled={false} onEdit={onEdit} onDelete={onDelete} {...overrides} />,
  );
  return { onEdit, onDelete };
}

describe("TopicCard", () => {
  it("renders the topic name and description", () => {
    renderCard();
    expect(screen.getByText("Immigration")).toBeInTheDocument();
    expect(screen.getByText("Policies and debate")).toBeInTheDocument();
  });

  it("edits the topic and calls onEdit with trimmed values", async () => {
    const user = userEvent.setup();
    const { onEdit } = renderCard();

    await user.click(screen.getByLabelText("Edit topic"));
    const nameInput = screen.getByLabelText("Topic name");
    await user.clear(nameInput);
    await user.type(nameInput, "  Migration  ");
    await user.click(screen.getByLabelText("Confirm edit"));

    expect(onEdit).toHaveBeenCalledWith("Migration", "Policies and debate");
  });

  it("disables confirm when a field is emptied", async () => {
    const user = userEvent.setup();
    const { onEdit } = renderCard();

    await user.click(screen.getByLabelText("Edit topic"));
    await user.clear(screen.getByLabelText("Topic description"));
    await user.click(screen.getByLabelText("Confirm edit"));

    expect(onEdit).not.toHaveBeenCalled();
  });

  it("requires confirmation before deleting", async () => {
    const user = userEvent.setup();
    const { onDelete } = renderCard();

    await user.click(screen.getByLabelText("Delete topic"));
    // dialog open — onDelete not fired yet
    expect(onDelete).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("shows a select checkbox only for non-reconciled topics", () => {
    const { rerender } = render(
      <TopicCard topic={topic} index={1} reconciled={false} onEdit={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByLabelText(/Select topic/)).toBeInTheDocument();

    rerender(
      <TopicCard topic={topic} index={1} reconciled onEdit={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.queryByLabelText(/Select topic/)).not.toBeInTheDocument();
  });
});
