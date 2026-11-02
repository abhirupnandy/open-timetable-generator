import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { Dialog } from "../components/Dialog";
import { Page } from "../components/Layout";
import { RecordForm } from "../components/RecordForm";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../components/Toasts";
import { api } from "../lib/api";
import { humanize } from "../lib/format";
import { useRefs, useResource } from "../lib/hooks";
import {
  ENUMS,
  RESOURCES,
  fieldLabel,
  refKeysFor,
  refLabel,
  resolveRef,
  type RefData,
  type Resource,
  type ResourceKey,
} from "../lib/resources";
import type { Row } from "../lib/types";

/** Plain-text cell value, used for display, filtering and sorting. */
export function cellText(resource: Resource, refs: RefData, row: Row, column: string): string {
  const field = resource.fields.find((item) => item.name === column);
  const value = row[column];
  if (field?.type === "ref") {
    const key = resolveRef(field, row);
    return key ? refLabel(refs, key, value) : "";
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined) return "";
  if (typeof value === "string" && ENUMS[field?.enumName ?? column]) return humanize(value);
  return String(value);
}

export function ResourcePage() {
  const { resource: key } = useParams();
  if (!key || !(key in RESOURCES)) return <Navigate to="/" replace />;
  return <ResourceTable key={key} resource={RESOURCES[key as ResourceKey]} />;
}

function ResourceTable({ resource }: { resource: Resource }) {
  const rows = useResource(resource.key);
  const { refs, isLoading: refsLoading, error: refError } = useRefs(refKeysFor(resource));
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ column: number; desc: boolean } | null>(null);
  const [editing, setEditing] = useState<Row | null | undefined>(undefined);
  const [deleting, setDeleting] = useState<Row | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const remove = useMutation({
    mutationFn: (row: Row) => api.remove(resource.path, row.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resource"] });
      toast(`Deleted ${resource.singular}`);
    },
    onError: (err: Error) => toast(err.message, "bad"),
    onSettled: () => setDeleting(null),
  });

  const visible = useMemo(() => {
    const labelled = (rows.data ?? []).map((row) => ({
      row,
      text: resource.columns.map((column) => cellText(resource, refs, row, column)),
    }));
    const needle = query.trim().toLowerCase();
    let result = needle
      ? labelled.filter((item) => item.text.join(" ").toLowerCase().includes(needle))
      : labelled;
    if (sort) {
      const column = resource.columns[sort.column];
      result = [...result].sort((a, b) => {
        const left = a.row[column];
        const right = b.row[column];
        const order =
          typeof left === "number" && typeof right === "number"
            ? left - right
            : a.text[sort.column].localeCompare(b.text[sort.column], undefined, { numeric: true });
        return sort.desc ? -order : order;
      });
    }
    return result;
  }, [rows.data, refs, query, sort, resource]);

  const toggleSort = (column: number) =>
    setSort((current) => ({ column, desc: current?.column === column ? !current.desc : false }));

  const actions = (
    <button className="button primary" onClick={() => setEditing(null)}>
      Add {resource.singular}
    </button>
  );

  return (
    <Page title={resource.label} actions={actions}>
      {rows.error || refError ? (
        <ErrorBox error={rows.error ?? refError} />
      ) : rows.isLoading || refsLoading ? (
        <Loading />
      ) : (
        <div className="card">
          <div className="toolbar">
            <input
              type="search"
              placeholder={`Filter ${resource.label.toLowerCase()}…`}
              aria-label="Filter"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <span className="spacer" />
            <span className="muted">
              {visible.length} of {rows.data?.length ?? 0}
            </span>
          </div>
          {rows.data?.length ? (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    {resource.columns.map((column, index) => {
                      const field = resource.fields.find((item) => item.name === column);
                      const arrow = sort?.column === index ? (sort.desc ? " ↓" : " ↑") : "";
                      return (
                        <th key={column} className="sortable" onClick={() => toggleSort(index)}>
                          {field ? fieldLabel(field) : column}
                          {arrow}
                        </th>
                      );
                    })}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.map(({ row, text }) => (
                    <tr key={row.id}>
                      {text.map((value, index) => (
                        <td key={resource.columns[index]}>
                          {value === "" ? <span className="muted">—</span> : value}
                        </td>
                      ))}
                      <td className="actions">
                        <button className="button small" onClick={() => setEditing(row)}>
                          Edit
                        </button>{" "}
                        <button className="button small danger" onClick={() => setDeleting(row)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!visible.length && (
                    <tr>
                      <td colSpan={resource.columns.length + 1} className="empty">
                        No matches.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">No {resource.label.toLowerCase()} yet.</div>
          )}
        </div>
      )}

      {editing !== undefined && (
        <RecordForm resource={resource} row={editing} refs={refs} onClose={() => setEditing(undefined)} />
      )}

      <Dialog
        open={deleting !== null}
        small
        onClose={() => setDeleting(null)}
        onSubmit={() => deleting && remove.mutate(deleting)}
        footer={
          <>
            <button type="button" className="button" onClick={() => setDeleting(null)}>
              Cancel
            </button>
            <button type="submit" className="button danger" disabled={remove.isPending}>
              Delete
            </button>
          </>
        }
      >
        <p>
          Delete {resource.singular} “{deleting ? resource.display(deleting, refs) : ""}”?
        </p>
      </Dialog>
    </Page>
  );
}
