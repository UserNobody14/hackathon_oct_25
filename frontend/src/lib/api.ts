// API client and types for frontend-backend contract

export type FileFormat = "csv" | "parquet" | "json";

export type InspectRequest = {
  path: string;
  format: FileFormat;
  rows: number;
  seed: number;
};

export type InspectResponse = {
  schema: Record<string, string>;
  samplePreview: Array<Record<string, unknown>>;
  stats: Record<string, unknown>;
};

export type GenerationPreferences = {
  viz: "plotly" | "seaborn";
  engine: "pandas" | "polars";
};

export type GenerateRequest = {
  inspect: InspectResponse;
  prefs: GenerationPreferences;
};

export type GenerateResponse = {
  scriptPath: string;
  scriptText: string;
};

export type ExecuteRequest = {
  scriptPath: string;
  env: {
    AIDA_INPUT: string;
    AIDA_OUTPUT: string;
  };
};

export type ExecuteResponse = {
  artifacts: Array<{ type: string; path: string; title?: string }>;
};

export const API_BASE = "http://localhost:8099";

export function artifactUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return new URL(normalized, API_BASE).toString();
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const url = new URL(path, API_BASE).toString();
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
}

export async function apiInspect(req: InspectRequest): Promise<InspectResponse> {
  return await http<InspectResponse>("/api/inspect", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function apiGenerate(req: GenerateRequest): Promise<GenerateResponse> {
  return await http<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function apiExecute(
  req: ExecuteRequest,
  onLog?: (line: string) => void,
): Promise<ExecuteResponse> {
  // Attempt to stream logs if server supports text/event-stream; fallback to JSON.
  const url = new URL("/api/execute", API_BASE).toString();
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  const contentType = resp.headers.get("content-type") ?? "";
  if (resp.ok && contentType.includes("text/event-stream") && onLog) {
    const reader = resp.body?.getReader();
    const decoder = new TextDecoder();
    if (reader) {
      // Read stream lines and forward to callback
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split(/\r?\n/)) {
          if (line.trim()) onLog(line);
        }
      }
    }
    // After streaming logs, server should finish with JSON; try to parse remaining content
    // Fallback: refetch artifacts endpoint if provided in future.
  }

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as ExecuteResponse;
}

// Multipart file upload
export type UploadResponse = {
  path: string;
  originalName?: string | null;
  size?: number | null;
  mimeType?: string | null;
};

export async function apiUpload(file: File): Promise<UploadResponse> {
  const url = new URL("/api/upload", API_BASE).toString();
  const form = new FormData();
  form.append("file", file, file.name);
  const resp = await fetch(url, {
    method: "POST",
    body: form,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as UploadResponse;
}


