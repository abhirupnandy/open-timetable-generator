import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Dialog } from "../components/Dialog";
import { Page } from "../components/Layout";
import { useToast } from "../components/Toasts";
import { api } from "../lib/api";
import { humanize } from "../lib/format";
import type { ImportResult } from "../lib/types";

export function ImportData() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [issueFilter, setIssueFilter] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  const summary = useQuery({ queryKey: ["data-summary"], queryFn: api.dataSummary });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["resource"] });
    queryClient.invalidateQueries({ queryKey: ["data-summary"] });
  };

  const upload = useMutation({
    mutationFn: (selected: File) => api.importData(selected),
    onSuccess: (response) => {
      setResult(response);
      if (response.ok) {
        refresh();
        toast("Data imported");
      }
    },
    onError: (error: Error) => {
      setResult({ ok: false, counts: {}, issues: [{ sheet: "(upload)", row: null, column: null, message: error.message }] });
    },
  });

  const clear = useMutation({
    mutationFn: api.clearData,
    onSuccess: () => {
      refresh();
      setConfirmClear(false);
      setResult(null);
      toast("All data cleared");
    },
    onError: (error: Error) => toast(error.message, "bad"),
  });

  const issues = useMemo(() => {
    const needle = issueFilter.trim().toLowerCase();
    const all = result?.issues ?? [];
    return needle
      ? all.filter((issue) => `${issue.sheet} ${issue.column ?? ""} ${issue.message}`.toLowerCase().includes(needle))
      : all;
  }, [result, issueFilter]);

  const choose = (selected: File | undefined) => {
    if (!selected) return;
    setFile(selected);
    setResult(null);
  };

  const total = Object.values(summary.data ?? {}).reduce((sum, value) => sum + value, 0);

  return (
    <Page title="Import data">
      <div className="steps">
        <div className="card step">
          <h2>
            <span className="step-number">1</span> Download the template
          </h2>
          <p className="muted">
            One sheet per kind of record, with instructions, required columns highlighted and dropdowns for fixed
            values. Records refer to each other by code (school code, group code, employee ID).
          </p>
          <div className="toolbar">
            <a className="button primary" href={api.templateUrl} download>
              Blank template
            </a>
            <a className="button" href={api.sampleUrl} download>
              Filled-in example
            </a>
            <a className="button" href={api.exportUrl} download>
              Current data
            </a>
          </div>
          <p className="muted small">
            “Current data” exports what is in the database now, so you can edit it in Excel and re-import.
          </p>
        </div>

        <div className="card step">
          <h2>
            <span className="step-number">2</span> Upload the filled-in workbook
          </h2>
          <div
            className={`dropzone ${dragging ? "dragging" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              choose(event.dataTransfer.files[0]);
            }}
            onClick={() => input.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && input.current?.click()}
          >
            <input
              ref={input}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              hidden
              aria-label="Workbook file"
              onChange={(event) => choose(event.target.files?.[0])}
            />
            {file ? (
              <>
                <b>{file.name}</b> <span className="muted">({Math.ceil(file.size / 1024)} KB)</span>
              </>
            ) : (
              <span className="muted">Drop an .xlsx file here or click to choose one</span>
            )}
          </div>
          <div className="toolbar" style={{ marginTop: 12 }}>
            <button
              className="button primary"
              disabled={!file || upload.isPending}
              onClick={() => file && upload.mutate(file)}
            >
              {upload.isPending ? "Importing…" : "Import"}
            </button>
            <span className="muted small">Importing replaces all existing data. Nothing changes if any row has an error.</span>
          </div>
        </div>
      </div>

      {result?.ok && (
        <div className="card success-card" role="status">
          <h2>Import complete</h2>
          <div className="tiles">
            {Object.entries(result.counts).map(([sheet, count]) => (
              <div key={sheet} className="tile">
                <div className="tile-label">{sheet}</div>
                <div className="tile-value">{count}</div>
              </div>
            ))}
          </div>
          <div className="toolbar">
            <Link className="button primary" to="/generate">
              <span className="step-number inverse">3</span> Generate the timetable
            </Link>
            <Link className="button" to="/data/assignments">
              Review assignments
            </Link>
            <Link className="button" to="/constraints">
              Review constraints
            </Link>
          </div>
        </div>
      )}

      {result && !result.ok && (
        <div className="card error-card" role="alert">
          <div className="card-head">
            <h2>
              Import rejected: {result.issues.length} problem{result.issues.length === 1 ? "" : "s"} found
            </h2>
            <input
              type="search"
              placeholder="Filter problems…"
              aria-label="Filter problems"
              value={issueFilter}
              onChange={(event) => setIssueFilter(event.target.value)}
            />
          </div>
          <p className="muted">Nothing was changed. Fix these cells in the workbook and upload it again.</p>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Sheet</th>
                  <th className="num">Row</th>
                  <th>Column</th>
                  <th>Problem</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((issue, index) => (
                  <tr key={index}>
                    <td>{issue.sheet}</td>
                    <td className="num">{issue.row ?? ""}</td>
                    <td className="mono">{issue.column ?? ""}</td>
                    <td>{issue.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <h2>Data in the database</h2>
          <button className="button danger" disabled={!total} onClick={() => setConfirmClear(true)}>
            Clear all data
          </button>
        </div>
        <div className="tiles">
          {Object.entries(summary.data ?? {}).map(([table, count]) => (
            <div key={table} className="tile">
              <div className="tile-label">{humanize(table)}</div>
              <div className="tile-value">{count}</div>
            </div>
          ))}
        </div>
        <p className="muted small">Individual records can be edited on the Data pages in the sidebar.</p>
      </div>

      <Dialog
        open={confirmClear}
        small
        onClose={() => setConfirmClear(false)}
        onSubmit={() => clear.mutate()}
        footer={
          <>
            <button type="button" className="button" onClick={() => setConfirmClear(false)}>
              Cancel
            </button>
            <button type="submit" className="button danger" disabled={clear.isPending}>
              Delete everything
            </button>
          </>
        }
      >
        <p>Delete all schools, courses, faculty, rooms, subjects, groups, assignments and constraint inputs? Run history is kept.</p>
      </Dialog>
    </Page>
  );
}
