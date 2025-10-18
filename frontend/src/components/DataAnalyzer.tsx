import { useCallback, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type {
  ExecuteResponse,
  FileFormat,
  GenerateResponse,
  InspectResponse,
} from "@/lib/api";
import { apiExecute, apiGenerate, apiInspect } from "@/lib/api";

type AnalyzerState =
  | { kind: "idle" }
  | { kind: "inspecting" }
  | { kind: "generating"; inspect: InspectResponse }
  | { kind: "executing"; inspect: InspectResponse; script: GenerateResponse; logs: string[] }
  | { kind: "succeeded"; inspect: InspectResponse; script: GenerateResponse; result: ExecuteResponse }
  | { kind: "failed"; error: string };

export function DataAnalyzer() {
  const [filePath, setFilePath] = useState("");
  const [format, setFormat] = useState<FileFormat>("csv");
  const [rows, setRows] = useState(1000);
  const [seed, setSeed] = useState(42);
  const [engine, setEngine] = useState<"pandas" | "polars">("pandas");
  const [viz, setViz] = useState<"plotly" | "seaborn">("plotly");
  const [state, setState] = useState<AnalyzerState>({ kind: "idle" });

  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const scrollLogsToBottom = useCallback(() => logsEndRef.current?.scrollIntoView({ behavior: "smooth" }), []);

  const onInspect = useCallback(async () => {
    try {
      setState({ kind: "inspecting" });
      const inspect = await apiInspect({ path: filePath, format, rows, seed });
      setState({ kind: "generating", inspect });
      const script = await apiGenerate({ inspect, prefs: { engine, viz } });
      const logs: string[] = [];
      setState({ kind: "executing", inspect, script, logs });
      const result = await apiExecute(
        { scriptPath: script.scriptPath, env: { AIDA_INPUT: filePath, AIDA_OUTPUT: "artifacts" } },
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
  }, [engine, filePath, format, rows, seed, viz, scrollLogsToBottom]);

  const disabled = useMemo(() => !filePath || !format || rows <= 0, [filePath, format, rows]);

  return (
    <div className="grid gap-6">
      <Card>
        <CardContent className="pt-6 grid gap-4 text-left">
          <h2 className="text-2xl font-semibold">File Input</h2>
          <div className="grid gap-2">
            <Label htmlFor="file-path">Path</Label>
            <Input
              id="file-path"
              placeholder="/absolute/path/to/data.csv"
              value={filePath}
              onChange={e => setFilePath(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="format">Format</Label>
            <Select id="format" value={format} onChange={e => setFormat(e.target.value as FileFormat)}>
              <option value="csv">csv</option>
              <option value="parquet">parquet</option>
              <option value="json">json</option>
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
              <Select id="engine" value={engine} onChange={e => setEngine(e.target.value as "pandas" | "polars")}> 
                <option value="pandas">pandas</option>
                <option value="polars">polars</option>
              </Select>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="viz">Viz Library</Label>
            <Select id="viz" value={viz} onChange={e => setViz(e.target.value as "plotly" | "seaborn")}> 
              <option value="plotly">plotly</option>
              <option value="seaborn">seaborn</option>
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
              <div className="grid gap-2">
                {(state.result.artifacts ?? []).map((a, i) => (
                  <div key={i} className="text-sm">
                    <span className="font-medium">{a.title ?? a.path}</span>
                    <span className="text-muted-foreground"> — {a.type}</span>
                  </div>
                ))}
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


