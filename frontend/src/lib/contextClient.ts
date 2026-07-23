import { API_BASE_URL } from "./config";
import { getAuthKey } from "./authKey";

export interface ContextStreamEvent {
  event: "message" | "done" | "error";
  text?: string; // populated for "message"
  raw?: string; // raw data payload for "done" / "error"
}

/**
 * Parse one SSE block (the lines between blank-line delimiters) emitted by the
 * /context/query endpoint. Unlike the graph stream, this endpoint sets the SSE
 * `event:` field explicitly (message | done | error) and `message` payloads are
 * JSON of the shape {"text": "..."}.
 */
function parseBlock(lines: string[]): ContextStreamEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) return null;
  const data = dataLines.join("\n");

  if (event === "message") {
    try {
      return { event: "message", text: JSON.parse(data).text ?? "" };
    } catch {
      return { event: "message", text: data };
    }
  }
  if (event === "done") return { event: "done", raw: data };
  return { event: "error", raw: data };
}

export async function* streamContextQuery(
  prompt: string,
  namespace?: string,
  topK?: number
): AsyncGenerator<ContextStreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/context/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      Authorization: `Bearer ${getAuthKey()}`,
    },
    body: JSON.stringify({
      prompt,
      namespace: namespace?.trim() || null,
      top_k: topK ?? null,
    }),
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(`Query failed: ${errorDetail || response.status}`);
  }
  if (!response.body) {
    throw new Error("No response body returned from server.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEventLines: string[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      if (currentEventLines.length > 0) {
        const event = parseBlock(currentEventLines);
        if (event) yield event;
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.trim() === "") {
        if (currentEventLines.length > 0) {
          const event = parseBlock(currentEventLines);
          if (event) yield event;
          currentEventLines = [];
        }
      } else {
        currentEventLines.push(line);
      }
    }
  }
}
