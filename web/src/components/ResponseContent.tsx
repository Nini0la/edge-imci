import { AlertTriangle } from "lucide-react";
import { parseResponse } from "../lib/response";

interface ResponseContentProps {
  response: string;
}

export function ResponseContent({ response }: ResponseContentProps) {
  return (
    <div className="response-content">
      {parseResponse(response).map((block, index) => {
        if (block.kind === "urgent") {
          const [lead, ...rest] = block.text.split(" ");
          return (
            <div className="response-urgent" key={`${block.kind}-${index}`}>
              <AlertTriangle aria-hidden="true" size={22} strokeWidth={2.2} />
              <p>
                <strong>{lead}</strong> {rest.join(" ")}
              </p>
            </div>
          );
        }
        if (block.kind === "status") {
          return (
            <p className="response-status" key={`${block.kind}-${index}`}>
              {block.text}
            </p>
          );
        }
        if (block.kind === "heading") {
          return (
            <h3 className="response-heading" key={`${block.kind}-${index}`}>
              {block.text}
            </h3>
          );
        }
        if (block.kind === "bullet") {
          return (
            <div className="response-bullet" key={`${block.kind}-${index}`}>
              <span className="response-check" aria-hidden="true">
                <span />
              </span>
              <p>{block.text}</p>
            </div>
          );
        }
        return (
          <p className="response-paragraph" key={`${block.kind}-${index}`}>
            {block.text}
          </p>
        );
      })}
    </div>
  );
}
