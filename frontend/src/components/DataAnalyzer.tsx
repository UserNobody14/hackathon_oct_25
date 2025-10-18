import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type {
  ExecuteResponse,
  FileFormat,
  GenerateResponse,
  InspectResponse,
} from "@/lib/api";
import { apiExecute, apiGenerate, apiInspect, apiUpload, artifactUrl } from "@/lib/api";

type AnalyzerState =
  | { kind: "idle" }
  | { kind: "inspecting" }
  | { kind: "generating"; inspect: InspectResponse }
  | { kind: "executing"; inspect: InspectResponse; script: GenerateResponse; logs: string[] }
  | { kind: "succeeded"; inspect: InspectResponse; script: GenerateResponse; result: ExecuteResponse }
  | { kind: "failed"; error: string };

export function DataAnalyzer() {
  const [localFile, setLocalFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [format, setFormat] = useState<FileFormat>("csv");
  const [rows, setRows] = useState(1000);
  const [seed, setSeed] = useState(42);
  const [engine, setEngine] = useState<"pandas" | "polars">("pandas");
  const [viz, setViz] = useState<"plotly" | "seaborn">("plotly");
  const [state, setState] = useState<AnalyzerState>({ kind: "idle" });

  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const scrollLogsToBottom = useCallback(() => logsEndRef.current?.scrollIntoView({ behavior: "smooth" }), []);

  const uploadFromSpecificUrl = useCallback(
    async (u: string) => {
      try {
        if (!u) throw new Error("Please enter a file URL.");
        const response = await fetch(u);
        if (!response.ok) throw new Error(`Failed to fetch URL: ${response.status}`);
        const blob = await response.blob();
        const inferredName = (() => {
          try {
            const urlObj = new URL(u);
            const parts = urlObj.pathname.split("/");
            const last = parts[parts.length - 1] || "data.csv";
            return last.includes(".") ? last : `${last}.csv`;
          } catch {
            return "data.csv";
          }
        })();
        const mime = blob.type || "text/csv";
        const syntheticFile = new File([blob], inferredName, { type: mime });
        const up = await apiUpload(syntheticFile);
        setUploadedPath(up.path);
        setLocalFile(syntheticFile);
        return up.path;
      } catch (e) {
        setState({ kind: "failed", error: (e as Error).message });
        throw e;
      }
    },
    [setUploadedPath, setLocalFile, setState],
  );

  const onInspect = useCallback(async () => {
    try {
      setState({ kind: "inspecting" });
      // Ensure file is uploaded before inspect
      let pathToUse = uploadedPath;
      if (!pathToUse) {
        if (!localFile) throw new Error("Please select a file to upload.");
        const up = await apiUpload(localFile);
        pathToUse = up.path;
        setUploadedPath(pathToUse);
      }
      const inspect = await apiInspect({ path: pathToUse, format, rows, seed });
      setState({ kind: "generating", inspect });
      const script = await apiGenerate({ inspect, prefs: { engine, viz } });
      const logs: string[] = [];
      setState({ kind: "executing", inspect, script, logs });
      const result = await apiExecute(
        { scriptPath: script.scriptPath, env: { AIDA_INPUT: pathToUse, AIDA_OUTPUT: "artifacts" } },
        line => {
          logs.push(line);
          setState(s => (s.kind === "executing" ? { ...s, logs: [...logs] } : s));
          scrollLogsToBottom();
        },
      );
      setState({ kind: "succeeded", inspect, script, result });
    } catch (e) {
      setState({ kind: "failed", error: (e as Error).message });
    }
  }, [engine, uploadedPath, localFile, format, rows, seed, viz, scrollLogsToBottom]);

  const disabled = useMemo(() => (!localFile && !uploadedPath) || !format || rows <= 0, [localFile, uploadedPath, format, rows]);

  return (
    <div className="grid gap-6">
      <Card>
        <CardContent className="pt-6 grid gap-4 text-left">
          <h2 className="text-2xl font-semibold">File Upload</h2>
          <div className="grid gap-2">
            <Label htmlFor="file">Select File</Label>
            <Input
              id="file"
              type="file"
              accept=".csv,.parquet,.json,.jsonl,application/json,text/csv,application/x-parquet"
              data-testid="file-input"
              onChange={e => {
                const f = e.target.files?.[0] ?? null;
                setLocalFile(f);
                setUploadedPath("");
              }}
            />
            {localFile && (
              <div className="text-sm text-muted-foreground">Selected: {localFile.name} ({(localFile.size / 1024).toFixed(1)} KB)</div>
            )}
            {uploadedPath && (
              <div className="text-sm">Uploaded path: <code className="break-all">{uploadedPath}</code></div>
            )}
          </div>

          <div className="grid gap-2">
            <Label htmlFor="fileUrl">Upload from URL</Label>
            <div className="grid md:grid-cols-3 gap-2">
              <Input
                id="fileUrl"
                placeholder="https://example.com/data.csv"
                value={fileUrl}
                onChange={e => setFileUrl(e.target.value)}
              />
              <Button
                variant="secondary"
                onClick={() => uploadFromSpecificUrl(fileUrl)}
                aria-label="Upload from URL"
              >
                Upload URL
              </Button>
              <Button
                variant="outline"
                onClick={() => uploadFromSpecificUrl("/sample.csv")}
                aria-label="Use sample.csv"
              >
                Use sample.csv
              </Button>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="format">Format</Label>
            <Select value={format} onValueChange={v => setFormat(v as FileFormat)}>
              <SelectTrigger id="format">
                <SelectValue placeholder="Select format" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">csv</SelectItem>
                <SelectItem value="parquet">parquet</SelectItem>
                <SelectItem value="json">json</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="rows">Rows</Label>
              <Input id="rows" type="number" value={rows} onChange={e => setRows(Number(e.target.value))} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="seed">Seed</Label>
              <Input id="seed" type="number" value={seed} onChange={e => setSeed(Number(e.target.value))} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="engine">Engine</Label>
              <Select value={engine} onValueChange={v => setEngine(v as "pandas" | "polars")}>
                <SelectTrigger id="engine">
                  <SelectValue placeholder="Select engine" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pandas">pandas</SelectItem>
                  <SelectItem value="polars">polars</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="viz">Viz Library</Label>
            <Select value={viz} onValueChange={v => setViz(v as "plotly" | "seaborn")}>
              <SelectTrigger id="viz">
                <SelectValue placeholder="Select viz lib" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="plotly">plotly</SelectItem>
                <SelectItem value="seaborn">seaborn</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Button aria-label="Analyze" onClick={onInspect} disabled={disabled || state.kind === "inspecting" || state.kind === "generating" || state.kind === "executing"}>
              {state.kind === "inspecting"
                ? "Inspecting..."
                : state.kind === "generating"
                ? "Generating..."
                : state.kind === "executing"
                ? "Executing..."
                : "Analyze"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {state.kind !== "idle" && state.kind !== "failed" && (
        <Card>
          <CardContent className="pt-6 grid gap-6 text-left">
            <h2 className="text-2xl font-semibold">Inspect Panel</h2>
            {"inspect" in state ? (
              <div className="grid gap-2">
                <div className="overflow-auto">
                  <pre className="text-sm bg-muted p-3 rounded-md">
{JSON.stringify((state as any).inspect.schema, null, 2)}
                  </pre>
                </div>
                <div className="overflow-auto">
                  <pre className="text-sm bg-muted p-3 rounded-md">
{JSON.stringify((state as any).inspect.samplePreview.slice(0, 5), null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">Awaiting inspection...</p>
            )}

            <h2 className="text-2xl font-semibold">Script Panel</h2>
            {"script" in state ? (
              <div className="overflow-auto">
                <pre className="text-sm bg-muted p-3 rounded-md whitespace-pre-wrap">
{(state as any).script.scriptText}
                </pre>
              </div>
            ) : (
              <p className="text-muted-foreground">No script yet.</p>
            )}

            <h2 className="text-2xl font-semibold">Run Panel</h2>
            {state.kind === "executing" ? (
              <div className="overflow-auto max-h-64 bg-muted p-3 rounded-md text-sm">
                {(state.logs ?? []).map((l, i) => (
                  <div key={i}>{l}</div>
                ))}
                <div ref={logsEndRef} />
              </div>
            ) : state.kind === "succeeded" ? (
              <div className="text-green-600">Execution completed.</div>
            ) : (
              <p className="text-muted-foreground">Not running.</p>
            )}

            <h2 className="text-2xl font-semibold">Results Panel</h2>
            {state.kind === "succeeded" ? (
              <div className="grid gap-4">
                {(state.result.artifacts ?? []).map((a, i) => {
                  const url = artifactUrl(a.path);
                  const title = a.title ?? a.path;
                  const t = (a.type || "").toLowerCase();
                  const isImage = t.startsWith("image/") || ["png", "jpg", "jpeg", "gif", "webp"].some(ext => a.path.toLowerCase().endsWith(ext));
                  const isHtml = t === "html" || a.path.toLowerCase().endsWith(".html");
                  const isCsv = t === "text/csv" || a.path.toLowerCase().endsWith(".csv");
                  const isJson = t === "application/json" || a.path.toLowerCase().endsWith(".json");
                  return (
                    <div key={i} className="grid gap-2">
                      <div className="text-sm font-medium flex items-center gap-2">
                        <span>{title}</span>
                        <a className="text-blue-600 hover:underline" href={url} target="_blank" rel="noreferrer">Open</a>
                        <span className="text-muted-foreground">{a.type}</span>
                      </div>
                      {isHtml ? (
                        <iframe title={title} src={url} className="w-full h-[480px] border rounded-md" />
                      ) : isImage ? (
                        <img src={url} alt={title} className="max-w-full rounded-md border" />
                      ) : isCsv || isJson ? (
                        <div className="overflow-auto max-h-96 bg-muted p-3 rounded-md text-xs">
                          {/* Lazy fetch and preview of small text files */}
                          <ArtifactTextPreview url={url} />
                        </div>
                      ) : (
                        <div className="text-sm text-muted-foreground">Preview not available. Use Open to view.</div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-muted-foreground">No results yet.</p>
            )}
          </CardContent>
        </Card>
      )}

      {state.kind === "failed" && (
        <Card>
          <CardContent className="pt-6 text-left">
            <div className="text-red-600">{state.error}</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default DataAnalyzer;



function ArtifactTextPreview({ url }: { url: string }) {
  const [content, setContent] = useState<string>("Loading...");
  useEffect(() => {
    let isActive = true;
    const controller = new AbortController();
    const fetchPreview = async () => {
      try {
        const resp = await fetch(url, { signal: controller.signal });
        const text = await resp.text();
        if (!isActive) return;
        // Limit preview to ~200KB to avoid freezing the UI
        const maxChars = 200_000;
        setContent(text.length > maxChars ? text.slice(0, maxChars) + "\n…\n(truncated)" : text);
      } catch (e) {
        if (!isActive) return;
        setContent(String(e));
      }
    };
    fetchPreview();
    return () => {
      isActive = false;
      controller.abort();
    };
  }, [url]);
  return <pre className="whitespace-pre-wrap">{content}</pre>;
}
