import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

// Mock the Next router and next-auth signIn that LoginForm depends on.
const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

const signIn = vi.fn();
vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => signIn(...args),
}));

import { LoginForm } from "./login-form";

afterEach(() => {
  push.mockReset();
  refresh.mockReset();
  signIn.mockReset();
});

describe("LoginForm", () => {
  it("signs in and redirects to the pipeline on success", async () => {
    const user = userEvent.setup();
    signIn.mockResolvedValue({ error: null });
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Password"), "s3cret");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(signIn).toHaveBeenCalledWith("credentials", {
      username: "alice",
      password: "s3cret",
      redirect: false,
    });
    expect(push).toHaveBeenCalledWith("/pipeline");
  });

  it("shows a generic error and does not redirect on bad credentials", async () => {
    const user = userEvent.setup();
    signIn.mockResolvedValue({ error: "CredentialsSignin" });
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
