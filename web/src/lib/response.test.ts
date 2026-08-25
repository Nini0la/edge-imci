import { describe, expect, it } from "vitest";
import { parseResponse } from "./response";

describe("parseResponse", () => {
  it("preserves urgent response hierarchy", () => {
    const blocks = parseResponse(`URGENT: Act now and do not delay referral.

Immediate management:
- Arrange urgent referral.

ASSESSMENT INCOMPLETE`);

    expect(blocks.map((block) => block.kind)).toEqual([
      "urgent",
      "heading",
      "bullet",
      "status",
    ]);
    expect(blocks[0].text).toContain("Act now");
  });

  it("recognizes standard complete sections", () => {
    const blocks = parseResponse(`Classifications:
- Pneumonia

Management:
- Give oral amoxicillin for 5 days.`);

    expect(blocks).toEqual([
      { kind: "heading", text: "Classifications:" },
      { kind: "bullet", text: "Pneumonia" },
      { kind: "heading", text: "Management:" },
      { kind: "bullet", text: "Give oral amoxicillin for 5 days." },
    ]);
  });

  it("recognizes the scope rejection delimiter", () => {
    expect(parseResponse("OUTSIDE SUPPORTED SCOPE")[0].kind).toBe("status");
  });
});
