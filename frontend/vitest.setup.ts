import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// @testing-library/react's auto-cleanup normally hooks a global afterEach;
// Vitest doesn't expose one unless test.globals is set, so register it
// explicitly — otherwise DOM from one test's render() leaks into the next.
afterEach(() => {
  cleanup();
});
