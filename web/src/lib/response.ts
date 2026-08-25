export type ResponseBlock = {
  kind: "urgent" | "status" | "heading" | "bullet" | "paragraph";
  text: string;
};

const STATUS_LINES = new Set(["ASSESSMENT INCOMPLETE", "OUTSIDE SUPPORTED SCOPE"]);

export function parseResponse(response: string): ResponseBlock[] {
  return response
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      if (line.startsWith("URGENT:")) return { kind: "urgent", text: line };
      if (STATUS_LINES.has(line)) return { kind: "status", text: line };
      if (line.startsWith("- ")) return { kind: "bullet", text: line.slice(2) };
      if (line.endsWith(":")) return { kind: "heading", text: line };
      return { kind: "paragraph", text: line };
    });
}
