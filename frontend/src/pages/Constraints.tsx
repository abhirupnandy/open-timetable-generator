import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "../components/Badge";
import { Dialog } from "../components/Dialog";
import { Page } from "../components/Layout";
import { SchemaField } from "../components/SchemaField";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../components/Toasts";
import { ApiError, api } from "../lib/api";
import { CONSTRAINT_INFO } from "../lib/constraintInfo";
import { useConfig } from "../lib/hooks";
import { label, pathKey, resolve, setIn, type Path } from "../lib/schema";
import type { JsonSchema, TimetableConfig } from "../lib/types";

const TABS = [
  ["calendar", "Calendar"],
  ["solver", "Solver"],
  ["hard", "Optional hard"],
  ["constraints", "Flexible"],
  ["soft", "Soft"],
] as const;

type Tab = (typeof TABS)[number][0];
const PRIMARY = ["enabled", "mode", "weight"];

interface ErrorItem {
  path: string;
  message: string;
}

function parseErrors(error: unknown): ErrorItem[] {
  if (error instanceof ApiError && Array.isArray(error.detail)) {
    return (error.detail as { loc?: (string | number)[]; msg: string }[]).map((item) => ({
      path: (item.loc ?? []).filter((part) => part !== "body").join("."),
      message: item.msg.replace(/^Value error, /, ""),
    }));
  }
  return [{ path: "", message: error instanceof Error ? error.message : String(error) }];
}

export function Constraints() {
  const config = useConfig();
  const schema = useQuery({ queryKey: ["config-schema"], queryFn: api.configSchema, staleTime: Infinity });
  const queryClient = useQueryClient();
  const toast = useToast();
  const [draft, setDraft] = useState<TimetableConfig | null>(null);
  const [tab, setTab] = useState<Tab>("soft");
  const [errors, setErrors] = useState<ErrorItem[]>([]);
  const [confirmReset, setConfirmReset] = useState(false);

  useEffect(() => {
    if (config.data && draft === null) setDraft(structuredClone(config.data.config));
  }, [config.data, draft]);

  const saved = config.data?.config;
  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(saved), [draft, saved]);

  const onSaved = (response: Awaited<ReturnType<typeof api.saveConfig>>, message: string) => {
    queryClient.setQueryData(["config"], response);
    setDraft(structuredClone(response.config));
    setErrors([]);
    toast(message);
  };

  const save = useMutation({
    mutationFn: (value: TimetableConfig) => api.saveConfig(value),
    onSuccess: (response) => onSaved(response, "Constraints saved; they apply to the next run"),
    onError: (error) => {
      const items = parseErrors(error);
      setErrors(items);
      const first = items.find((item) => item.path)?.path.split(".")[0];
      if (first && TABS.some(([key]) => key === first)) setTab(first as Tab);
      toast(`Not saved: ${items.length} problem(s)`, "bad");
    },
  });

  const reset = useMutation({
    mutationFn: api.resetConfig,
    onSuccess: (response) => {
      setConfirmReset(false);
      onSaved(response, "Constraints reset to defaults");
    },
    onError: (error: Error) => toast(error.message, "bad"),
  });

  if (config.error || schema.error) {
    return <Page title="Constraints"><ErrorBox error={config.error ?? schema.error} /></Page>;
  }
  if (!draft || !schema.data) return <Page title="Constraints"><Loading /></Page>;

  const root = schema.data;
  const errorMap = Object.fromEntries(errors.filter((item) => item.path).map((item) => [item.path, item.message]));
  const change = (path: Path, value: unknown) => {
    setDraft((current) => setIn(current, path, value));
    const key = pathKey(path);
    if (errorMap[key]) setErrors((items) => items.filter((item) => item.path !== key));
  };
  const sectionSchema = resolve(root.properties![tab], root).schema;
  const errorsIn = (section: string) => errors.filter((item) => item.path === section || item.path.startsWith(`${section}.`)).length;

  const actions = (
    <>
      <button className="button" onClick={() => setConfirmReset(true)}>
        Reset to defaults
      </button>
      <button className="button primary" disabled={!dirty || save.isPending} onClick={() => save.mutate(draft)}>
        {save.isPending ? "Saving…" : "Save"}
      </button>
    </>
  );

  return (
    <Page title="Constraints" actions={actions}>
      <div className="card">
        <p className="muted" style={{ margin: 0 }}>
          Changes are saved to <span className="mono">config/timetable.toml</span> and apply to the next run. Always
          on (not configurable): each session placed once; no faculty, student or room overlap; session fits in the
          day; room type, capacity and online/in-person rules.
        </p>
      </div>

      {errors.length > 0 && (
        <div className="card error-card" role="alert">
          <h2>Not saved: fix these problems</h2>
          <ul>
            {errors.map((item, index) => (
              <li key={index}>
                {item.path && <span className="mono">{item.path}</span>} {item.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="tabs" role="tablist">
        {TABS.map(([key, text]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            className={`tab ${tab === key ? "active" : ""}`}
            onClick={() => setTab(key)}
          >
            {text}
            {errorsIn(key) > 0 && <span className="badge bad">{errorsIn(key)}</span>}
          </button>
        ))}
      </div>

      {tab === "calendar" || tab === "solver" ? (
        <div className="card">
          <SchemaField
            schema={sectionSchema}
            root={root}
            value={draft[tab]}
            path={[tab]}
            onChange={change}
            errors={errorMap}
            name=""
          />
        </div>
      ) : (
        <div className="constraint-list">
          {Object.entries(sectionSchema.properties ?? {}).map(([key, child]) => (
            <ConstraintCard
              key={key}
              name={key}
              schema={resolve(child, root).schema}
              root={root}
              value={(draft[tab] as Record<string, Record<string, unknown>>)[key]}
              path={[tab, key]}
              onChange={change}
              errors={errorMap}
            />
          ))}
        </div>
      )}

      {dirty && (
        <div className="save-bar" role="status">
          <span>Unsaved changes</span>
          <button className="button" onClick={() => { setDraft(structuredClone(saved!)); setErrors([]); }}>
            Discard
          </button>
          <button className="button primary" disabled={save.isPending} onClick={() => save.mutate(draft)}>
            Save
          </button>
        </div>
      )}

      <Dialog
        open={confirmReset}
        small
        onClose={() => setConfirmReset(false)}
        onSubmit={() => reset.mutate()}
        footer={
          <>
            <button type="button" className="button" onClick={() => setConfirmReset(false)}>
              Cancel
            </button>
            <button type="submit" className="button danger">
              Reset
            </button>
          </>
        }
      >
        <p>Replace the whole configuration (calendar, solver and every constraint) with the built-in defaults?</p>
      </Dialog>
    </Page>
  );
}

interface CardProps {
  name: string;
  schema: JsonSchema;
  root: JsonSchema;
  value: Record<string, unknown>;
  path: Path;
  onChange: (path: Path, value: unknown) => void;
  errors: Record<string, string>;
}

function ConstraintCard({ name, schema, root, value, path, onChange, errors }: CardProps) {
  const properties = schema.properties ?? {};
  const off = value.enabled === false || value.mode === "off";
  const params = Object.entries(properties).filter(([key]) => !PRIMARY.includes(key));
  const weightUsed = "weight" in properties && (value.mode === undefined || value.mode === "soft");

  return (
    <div className={`card constraint ${off ? "is-off" : ""}`}>
      <div className="constraint-head">
        <div className="constraint-title">
          <h3>{name}</h3>
          <p className="muted small">{CONSTRAINT_INFO[name] ?? ""}</p>
        </div>
        <div className="constraint-primary">
          {"enabled" in properties && (
            <label className="switch">
              <input
                type="checkbox"
                aria-label={`${name} enabled`}
                checked={Boolean(value.enabled)}
                onChange={(event) => onChange([...path, "enabled"], event.target.checked)}
              />
              <span>{value.enabled ? <Badge kind="ok">on</Badge> : <Badge kind="">off</Badge>}</span>
            </label>
          )}
          {"mode" in properties && (
            <SchemaField schema={properties.mode} root={root} value={value.mode} path={[...path, "mode"]} onChange={onChange} errors={errors} name="Mode" />
          )}
          {"weight" in properties && (
            <div className={weightUsed ? "" : "dimmed"}>
              <SchemaField schema={properties.weight} root={root} value={value.weight} path={[...path, "weight"]} onChange={onChange} errors={errors} name="Weight" />
            </div>
          )}
        </div>
      </div>
      {params.length > 0 && !off && (
        <div className="constraint-params">
          {params.map(([key, child]) => (
            <SchemaField
              key={key}
              schema={child}
              root={root}
              value={value[key]}
              path={[...path, key]}
              onChange={onChange}
              errors={errors}
              name={label(key)}
            />
          ))}
        </div>
      )}
      {errors[pathKey(path)] && <span className="field-error">{errors[pathKey(path)]}</span>}
    </div>
  );
}
