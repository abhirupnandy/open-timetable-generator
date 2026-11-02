import { describe, expect, it } from "vitest";

import { errorMessage } from "./api";

describe("errorMessage", () => {
  it("formats FastAPI validation errors", () => {
    const detail = [
      { loc: ["body", "capacity"], msg: "Input should be greater than 0" },
      { loc: ["body"], msg: "Bad payload" },
    ];
    expect(errorMessage(detail, 422)).toBe("capacity: Input should be greater than 0\nBad payload");
  });

  it("passes plain messages through and falls back to the status", () => {
    expect(errorMessage("Room 9 not found", 404)).toBe("Room 9 not found");
    expect(errorMessage(undefined, 500)).toBe("Request failed (500)");
  });
});
