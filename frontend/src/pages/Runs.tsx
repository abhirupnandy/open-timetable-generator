import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Dialog } from "../components/Dialog";
import { Page } from "../components/Layout";
import { RunPanel } from "../components/RunView";
import { RunTable } from "../components/RunTable";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../components/Toasts";
import { api } from "../lib/api";
import type { RunSummary } from "../lib/types";

const FILTERS = [
  ["", "All"],
  ["failed", "Failed"],
  ["succeeded", "Succeeded"],
  ["running", "Running"],
] as const;

export function Runs() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState<string>("");
  const [deleting, setDeleting] = useState<RunSummary | null>(null);

  const runs = useQuery({
    queryKey: ["runs", filter],
    queryFn: () => api.runs(filter || undefined),
    refetchInterval: (query) => (query.state.data?.some((run) => run.status === "running") ? 2000 : false),
  });

  const remove = useMutation({
    mutationFn: (run: RunSummary) => api.deleteRun(run.id),
    onSuccess: (_, run) => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      toast("Run deleted");
      if (run.id === runId) navigate("/runs");
    },
    onError: (error: Error) => toast(error.message, "bad"),
    onSettled: () => setDeleting(null),
  });

  return (
    <Page title="Run history">
      <div className="card">
        <div className="toolbar">
          <div className="segmented" role="group" aria-label="Filter runs">
            {FILTERS.map(([value, label]) => (
              <button
                key={value}
                className={`button small ${filter === value ? "active" : ""}`}
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="spacer" />
          <span className="muted small">Server log: output/logs/app.log</span>
        </div>
        {runs.error ? (
          <ErrorBox error={runs.error} />
        ) : runs.isLoading ? (
          <Loading />
        ) : (
          <RunTable
            runs={runs.data ?? []}
            shownId={runId}
            onShow={(id) => navigate(`/runs/${id}`)}
            onDelete={setDeleting}
          />
        )}
      </div>

      {runId && <RunPanel key={runId} runId={runId} />}

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
            <button type="submit" className="button danger">
              Delete
            </button>
          </>
        }
      >
        <p>Delete run {deleting?.id} and its export files?</p>
      </Dialog>
    </Page>
  );
}
