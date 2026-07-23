import { GraphStreamEvent } from "./types";
import { API_BASE_URL } from "./config";
import { getAuthKey } from "./authKey";

function parseEvent(lines: string[]): GraphStreamEvent | null {
  let dataStr = "";
  for (const line of lines) {
    if (line.startsWith("data:")) {
      dataStr = line.slice(5).trim();
    }
  }
  if (dataStr) {
    try {
      return JSON.parse(dataStr) as GraphStreamEvent;
    } catch (e) {
      console.error("Failed to parse SSE data:", dataStr, e);
    }
  }
  return null;
}

export async function* streamGraphRun(targetFile: string, logs: string[], projectPath: string, reproCommand: string, namespace: string = ""): AsyncGenerator<GraphStreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/run/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
      "Authorization": `Bearer ${getAuthKey()}`
    },
    body: JSON.stringify({ 
      target_file: targetFile, 
      logs,
      project_path: projectPath,
      reproduction_command: reproCommand,
      namespace: namespace || null
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to start stream: ${response.statusText}`);
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
        const event = parseEvent(currentEventLines);
        if (event) yield event;
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    // The last chunk might be incomplete, so we leave it in the buffer
    buffer = lines.pop() || ""; 

    for (const line of lines) {
      if (line.trim() === "") {
        if (currentEventLines.length > 0) {
          const event = parseEvent(currentEventLines);
          if (event) yield event;
          currentEventLines = [];
        }
      } else {
        currentEventLines.push(line);
      }
    }
  }
}
