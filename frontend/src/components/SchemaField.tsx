import { useEffect, useState } from "react";

import { emptyValue, kindOf, label, parseNumberList, pathKey, resolve, type Path } from "../lib/schema";
import type { JsonSchema } from "../lib/types";

export interface FieldProps {
  schema: JsonSchema;
  root: JsonSchema;
  value: unknown;
  path: Path;
  onChange: (path: Path, value: unknown) => void;
  errors: Record<string, string>;
  name?: string;
  compact?: boolean;
}

function ErrorText({ errors, path }: { errors: Record<string, string>; path: Path }) {
  const message = errors[pathKey(path)];
  return message ? <span className="field-error">{message}</span> : null;
}

/** Renders any config value from its JSON schema. */
export function SchemaField(props: FieldProps) {
  const { schema: node, root, value, path, onChange, errors, name, compact } = props;
  const { schema, nullable } = resolve(node, root);
  const kind = kindOf(schema);
  const id = `cfg-${pathKey(path)}`;
  const title = name ?? label(path[path.length - 1] ?? "");
  const invalid = Boolean(errors[pathKey(path)]);

  if (kind === "object") {
    return (
      <fieldset className={`schema-object ${compact ? "compact" : ""}`}>
        {!compact && name !== "" && <legend>{title}</legend>}
        <div className="schema-grid">
          {Object.entries(schema.properties ?? {}).map(([key, child]) => (
            <SchemaField
              key={key}
              schema={child}
              root={root}
              value={(value as Record<string, unknown> | null)?.[key]}
              path={[...path, key]}
              onChange={onChange}
              errors={errors}
            />
          ))}
        </div>
        <ErrorText errors={errors} path={path} />
      </fieldset>
    );
  }

  if (kind === "array") {
    const items = resolve(schema.items ?? {}, root).schema;
    const itemKind = kindOf(items);
    if (itemKind === "object") {
      return <ObjectArray {...props} itemSchema={items} title={title} />;
    }
    return (
      <div className="field">
        <span>{title}</span>
        {itemKind === "enum" ? (
          <EnumSet {...props} options={items.enum as string[]} nullable={nullable} id={id} />
        ) : (
          <NumberList value={value} nullable={nullable} id={id} onChange={(next) => onChange(path, next)} invalid={invalid} />
        )}
        <ErrorText errors={errors} path={path} />
      </div>
    );
  }

  if (kind === "boolean") {
    return (
      <label className="field check" htmlFor={id}>
        <input id={id} type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(path, event.target.checked)} />
        <span>{title}</span>
        <ErrorText errors={errors} path={path} />
      </label>
    );
  }

  let control;
  if (kind === "enum") {
    control = (
      <select
        id={id}
        aria-label={compact ? title : undefined}
        aria-invalid={invalid}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(event) => onChange(path, event.target.value === "" ? null : event.target.value)}
      >
        {nullable && <option value="">— not set —</option>}
        {(schema.enum as string[]).map((option) => (
          <option key={option} value={option}>
            {label(option)}
          </option>
        ))}
      </select>
    );
  } else if (kind === "integer" || kind === "number") {
    control = (
      <input
        id={id}
        type="number"
        aria-label={compact ? title : undefined}
        aria-invalid={invalid}
        step={kind === "integer" ? 1 : "any"}
        min={schema.minimum}
        placeholder={nullable ? "not set" : undefined}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(event) => {
          const raw = event.target.value;
          onChange(path, raw === "" ? (nullable ? null : raw) : Number(raw));
        }}
      />
    );
  } else {
    control = (
      <input
        id={id}
        type="text"
        aria-label={compact ? title : undefined}
        aria-invalid={invalid}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(event) => onChange(path, event.target.value)}
      />
    );
  }

  return (
    <label className={`field ${compact ? "compact" : ""}`} htmlFor={id}>
      {!compact && <span>{title}</span>}
      {control}
      <ErrorText errors={errors} path={path} />
    </label>
  );
}

function EnumSet({
  value,
  path,
  onChange,
  options,
  nullable,
  id,
}: FieldProps & { options: string[]; nullable: boolean; id: string }) {
  const selected = Array.isArray(value) ? (value as string[]) : [];
  const unset = value === null || value === undefined;
  const toggle = (option: string, on: boolean) => {
    const next = on ? [...selected, option] : selected.filter((item) => item !== option);
    // Keep the schema's order.
    onChange(path, options.filter((item) => next.includes(item)));
  };
  return (
    <div className="check-group" id={id}>
      {nullable && (
        <label className="check">
          <input type="checkbox" checked={unset} onChange={(event) => onChange(path, event.target.checked ? null : [])} />
          <span className="muted">any</span>
        </label>
      )}
      {options.map((option) => (
        <label key={option} className="check">
          <input
            type="checkbox"
            checked={selected.includes(option)}
            disabled={nullable && unset}
            onChange={(event) => toggle(option, event.target.checked)}
          />
          <span>{label(option)}</span>
        </label>
      ))}
    </div>
  );
}

function NumberList({
  value,
  nullable,
  id,
  onChange,
  invalid,
}: {
  value: unknown;
  nullable: boolean;
  id: string;
  onChange: (value: unknown) => void;
  invalid: boolean;
}) {
  const format = (current: unknown) => (Array.isArray(current) ? current.join(", ") : "");
  const [text, setText] = useState(format(value));
  const [bad, setBad] = useState(false);

  useEffect(() => setText(format(value)), [value]);

  return (
    <input
      id={id}
      type="text"
      aria-invalid={invalid || bad}
      placeholder={nullable ? "not set" : "e.g. 1, 2, 3"}
      value={text}
      onChange={(event) => {
        setText(event.target.value);
        const parsed = parseNumberList(event.target.value);
        setBad(parsed === null);
        if (parsed !== null) onChange(nullable && event.target.value.trim() === "" ? null : parsed);
      }}
    />
  );
}

function ObjectArray({
  value,
  path,
  onChange,
  errors,
  root,
  itemSchema,
  title,
}: FieldProps & { itemSchema: JsonSchema; title: string }) {
  const rows = Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  const columns = Object.entries(itemSchema.properties ?? {});

  return (
    <div className="field object-array">
      <span>{title}</span>
      <div className="table-wrap">
        <table className="data compact-table">
          <thead>
            <tr>
              {columns.map(([key]) => (
                <th key={key}>{label(key)}</th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                {columns.map(([key, child]) => (
                  <td key={key}>
                    <SchemaField
                      schema={child}
                      root={root}
                      value={row[key]}
                      path={[...path, index, key]}
                      onChange={onChange}
                      errors={errors}
                      compact
                      name={label(key)}
                    />
                  </td>
                ))}
                <td className="actions">
                  <button
                    type="button"
                    className="button small danger"
                    aria-label={`Remove ${title} row ${index + 1}`}
                    onClick={() => onChange(path, rows.filter((_, other) => other !== index))}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={columns.length + 1} className="empty">
                  None
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div>
        <button
          type="button"
          className="button small"
          onClick={() => {
            const fresh = emptyValue(itemSchema, root) as Record<string, unknown>;
            if ("number" in fresh) fresh.number = rows.length + 1;
            onChange(path, [...rows, fresh]);
          }}
        >
          Add {title.toLowerCase().replace(/s$/, "")}
        </button>
      </div>
      <ErrorText errors={errors} path={path} />
    </div>
  );
}
