import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../lib/api";
import { humanize } from "../lib/format";
import {
  RESOURCES,
  enumOptions,
  fieldLabel,
  resolveRef,
  type Field,
  type RefData,
  type Resource,
} from "../lib/resources";
import type { Row } from "../lib/types";
import { Dialog } from "./Dialog";
import { useToast } from "./Toasts";

type Raw = Record<string, string | boolean>;

function initialRaw(resource: Resource, row: Row | null): Raw {
  const raw: Raw = {};
  for (const field of resource.fields) {
    const value = row ? row[field.name] : field.default;
    if (field.type === "bool") raw[field.name] = Boolean(value ?? false);
    else raw[field.name] = value === null || value === undefined ? "" : String(value);
  }
  return raw;
}

/** Convert a raw form value to the JSON value the API expects. */
export function toPayloadValue(field: Field, raw: string | boolean): unknown {
  if (field.type === "bool") return Boolean(raw);
  if (raw === "") return field.type === "text" && field.required ? "" : null;
  if (field.type === "int" || field.type === "ref") return Number(raw);
  if (field.type === "nullbool") return raw === "true";
  return raw;
}

interface RecordFormProps {
  resource: Resource;
  row: Row | null;
  refs: RefData;
  onClose: () => void;
}

export function RecordForm({ resource, row, refs, onClose }: RecordFormProps) {
  const editing = row !== null;
  const [raw, setRaw] = useState<Raw>(() => initialRaw(resource, row));
  const [error, setError] = useState("");
  const queryClient = useQueryClient();
  const toast = useToast();

  const values = Object.fromEntries(
    resource.fields.map((field) => [field.name, toPayloadValue(field, raw[field.name])]),
  );

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing ? api.update(resource.path, row.id, payload) : api.create(resource.path, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resource"] });
      toast(editing ? "Saved" : `Added ${resource.singular}`);
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const change = (field: Field, value: string | boolean) => {
    setRaw((current) => {
      const next = { ...current, [field.name]: value };
      for (const dependent of resource.fields.filter((item) => item.dependsOn === field.name)) {
        next[dependent.name] = "";
      }
      return next;
    });
  };

  const submit = () => {
    const editable = resource.fields.filter((field) => !(editing && field.createOnly));
    const missing = editable.filter(
      (field) => field.required && field.type !== "bool" && raw[field.name] === "",
    );
    if (missing.length) {
      setError(`Required: ${missing.map(fieldLabel).join(", ")}`);
      return;
    }
    setError("");
    save.mutate(Object.fromEntries(editable.map((field) => [field.name, values[field.name]])));
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title={editing ? `Edit ${resource.singular}` : `Add ${resource.singular}`}
      onSubmit={submit}
      footer={
        <>
          <button type="button" className="button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="button primary" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      {resource.fields.map((field) => (
        <FieldInput
          key={field.name}
          field={field}
          value={raw[field.name]}
          values={values}
          refs={refs}
          disabled={editing && Boolean(field.createOnly)}
          onChange={(value) => change(field, value)}
        />
      ))}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </Dialog>
  );
}

interface FieldInputProps {
  field: Field;
  value: string | boolean;
  values: Record<string, unknown>;
  refs: RefData;
  disabled: boolean;
  onChange: (value: string | boolean) => void;
}

function FieldInput({ field, value, values, refs, disabled, onChange }: FieldInputProps) {
  const id = `field-${field.name}`;
  const label = `${fieldLabel(field)}${field.required ? " *" : ""}`;
  const hint = field.hint ? <span className="hint">{field.hint}</span> : null;

  if (field.type === "bool") {
    return (
      <div>
        <label className="field check" htmlFor={id}>
          <input
            id={id}
            type="checkbox"
            checked={Boolean(value)}
            disabled={disabled}
            onChange={(event) => onChange(event.target.checked)}
          />
          <span>{fieldLabel(field)}</span>
        </label>
        {hint}
      </div>
    );
  }

  let control;

  if (field.type === "enum" || field.type === "nullbool" || field.type === "ref") {
    let options: [string, string][];
    if (field.type === "enum") {
      options = enumOptions(field).map((option) => [option, humanize(option)]);
    } else if (field.type === "nullbool") {
      options = [
        ["true", "Yes"],
        ["false", "No"],
      ];
    } else {
      const key = resolveRef(field, values);
      options = key
        ? (refs[key] ?? []).map((row) => [String(row.id), RESOURCES[key].display(row, refs)])
        : [];
    }
    control = (
      <select id={id} value={String(value)} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        <option value="">{field.required && field.type !== "nullbool" ? "Select…" : "—"}</option>
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    );
  } else {
    control = (
      <input
        id={id}
        type={field.type === "int" ? "number" : field.type}
        min={field.type === "int" ? 0 : undefined}
        step={field.type === "int" ? 1 : undefined}
        value={String(value)}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      {control}
      {hint}
    </label>
  );
}
