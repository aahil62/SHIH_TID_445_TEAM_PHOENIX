import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CopilotChat from "@/components/CopilotChat";

function mockFetchOnce(response: { ok: boolean; status: number; body: unknown }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: async () => response.body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("CopilotChat", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sends the question with the pre-filled txn_id and renders the answer plus tool trace", async () => {
    const fetchMock = mockFetchOnce({
      ok: true,
      status: 200,
      body: {
        answer: "This transaction was flagged for high velocity.",
        tool_calls: [{ tool: "explain_decision", input: { txn_id: "TXN-001" }, output: {} }],
        grounded: true,
      },
    });

    render(<CopilotChat txnId="TXN-001" />);

    fireEvent.change(screen.getByPlaceholderText("Ask about TXN-001…"), {
      target: { value: "Why was this flagged?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("This transaction was flagged for high velocity.")).toBeInTheDocument();
    });

    // Real payload check: the fetch call actually carries the question and
    // the pre-filled txn_id, not something the component just displays.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/copilot/chat");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      question: "Why was this flagged?",
      txn_id: "TXN-001",
    });

    // The tool-call trace must be visible, not hidden — core to how this
    // was designed (never a hallucinated answer with no real backend call
    // behind it).
    expect(screen.getByText(/Copilot checked: explain_decision/)).toBeInTheDocument();
  });

  it("shows the backend's real message when Copilot isn't configured (503)", async () => {
    mockFetchOnce({
      ok: false,
      status: 503,
      body: { detail: "GROQ_API_KEY is not set." },
    });

    render(<CopilotChat txnId="TXN-002" />);
    fireEvent.change(screen.getByPlaceholderText("Ask about TXN-002…"), {
      target: { value: "Why was this flagged?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText(/Copilot isn't set up yet/)).toBeInTheDocument();
    });
    expect(screen.getByText(/GROQ_API_KEY is not set\./)).toBeInTheDocument();
  });

  it("shows the backend's real message when the live LLM call fails (502)", async () => {
    mockFetchOnce({
      ok: false,
      status: 502,
      body: { detail: "Copilot's LLM call failed: simulated network failure" },
    });

    render(<CopilotChat txnId="TXN-005" />);
    fireEvent.change(screen.getByPlaceholderText("Ask about TXN-005…"), {
      target: { value: "Why was this flagged?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText(/Copilot couldn't answer/)).toBeInTheDocument();
    });
    expect(screen.getByText(/simulated network failure/)).toBeInTheDocument();
  });

  it("shows a loading state while the request is in flight", async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<CopilotChat txnId="TXN-003" />);
    fireEvent.change(screen.getByPlaceholderText("Ask about TXN-003…"), {
      target: { value: "Why was this flagged?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText(/Copilot is thinking/)).toBeInTheDocument();

    resolveFetch({
      ok: true,
      status: 200,
      json: async () => ({ answer: "Done.", tool_calls: [], grounded: true }),
    });
    await waitFor(() => expect(screen.getByText("Done.")).toBeInTheDocument());
  });

  it("clicking a suggestion sends it immediately without typing", async () => {
    const fetchMock = mockFetchOnce({
      ok: true,
      status: 200,
      body: { answer: "Answer.", tool_calls: [], grounded: true },
    });

    render(<CopilotChat txnId="TXN-004" />);
    fireEvent.click(screen.getByText("Why was this flagged?"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.question).toBe("Why was this flagged?");
    expect(body.txn_id).toBe("TXN-004");
  });
});
