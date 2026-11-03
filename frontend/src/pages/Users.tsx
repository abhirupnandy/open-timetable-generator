import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge } from "../components/Badge";
import { Dialog } from "../components/Dialog";
import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../components/Toasts";
import { api } from "../lib/api";
import { ROLE_LABELS, useAuth } from "../lib/auth";
import { designationLabel, formatDateTime } from "../lib/format";
import { useResource } from "../lib/hooks";
import type { CreatedAccount, CurrentUser, Role } from "../lib/types";

const ROLES: Role[] = ["ADMIN", "COORDINATOR", "FACULTY"];

interface Draft {
  id?: number;
  username: string;
  full_name: string;
  password: string;
  role: Role;
  faculty_employee_id: string;
  is_active: boolean;
}

const EMPTY: Draft = {
  username: "",
  full_name: "",
  password: "",
  role: "COORDINATOR",
  faculty_employee_id: "",
  is_active: true,
};

function downloadCsv(accounts: CreatedAccount[]) {
  const quote = (value: string) => `"${value.replace(/"/g, '""')}"`;
  const lines = [
    "username,name,email,password",
    ...accounts.map((item) => [item.username, item.full_name, item.email, item.password].map(quote).join(",")),
  ];
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "faculty_accounts.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function Users() {
  const { user: me } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const users = useQuery({ queryKey: ["users"], queryFn: api.users });
  const faculty = useResource("faculty");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [formError, setFormError] = useState("");
  const [deleting, setDeleting] = useState<CurrentUser | null>(null);
  const [created, setCreated] = useState<CreatedAccount[] | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["users"] });

  const save = useMutation({
    mutationFn: (value: Draft) => {
      const body: Record<string, unknown> = {
        username: value.username,
        full_name: value.full_name,
        role: value.role,
        faculty_employee_id: value.role === "FACULTY" ? value.faculty_employee_id || null : null,
        is_active: value.is_active,
      };
      if (value.password) body.password = value.password;
      return value.id ? api.updateUser(value.id, body) : api.createUser(body);
    },
    onSuccess: () => {
      refresh();
      toast(draft?.id ? "Account updated" : "Account created");
      setDraft(null);
    },
    onError: (error: Error) => setFormError(error.message),
  });

  const remove = useMutation({
    mutationFn: (user: CurrentUser) => api.deleteUser(user.id),
    onSuccess: () => {
      refresh();
      toast("Account deleted");
    },
    onError: (error: Error) => toast(error.message, "bad"),
    onSettled: () => setDeleting(null),
  });

  const bulk = useMutation({
    mutationFn: api.createFacultyAccounts,
    onSuccess: (result) => {
      refresh();
      setCreated(result.created);
    },
    onError: (error: Error) => toast(error.message, "bad"),
  });

  const facultyOptions = (faculty.data ?? []).map((row) => ({
    value: String(row.employee_id),
    label: `${row.name} (${designationLabel(String(row.designation))}) · ${row.employee_id}`,
  }));

  const edit = (value: Draft) => {
    setFormError("");
    setDraft(value);
  };

  return (
    <Page
      title="User accounts"
      actions={
        <>
          <button className="button" onClick={() => bulk.mutate()} disabled={bulk.isPending}>
            Create faculty accounts
          </button>
          <button className="button primary" onClick={() => edit(EMPTY)}>
            Add account
          </button>
        </>
      }
    >
      <div className="card">
        <p className="muted small">
          <b>Administrators</b> can do everything, including managing accounts. <b>Coordinators</b> can import data,
          edit constraints, generate and export timetables. <b>Faculty</b> only see and print their own timetable.
          “Create faculty accounts” adds a login (username = employee ID) for every faculty member without one.
        </p>
        {users.error ? (
          <ErrorBox error={users.error} />
        ) : users.isLoading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Faculty</th>
                  <th>Last sign-in</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(users.data ?? []).map((user) => (
                  <tr key={user.id} className={user.is_active ? "" : "dimmed"}>
                    <td>
                      {user.username} {user.id === me.id && <Badge kind="info">you</Badge>}
                    </td>
                    <td>{user.full_name || user.faculty?.name}</td>
                    <td>
                      <Badge>{ROLE_LABELS[user.role]}</Badge> {!user.is_active && <Badge>inactive</Badge>}
                    </td>
                    <td>
                      {user.faculty
                        ? `${user.faculty.name} (${user.faculty.designation_label})`
                        : user.faculty_employee_id
                          ? `${user.faculty_employee_id} (not in current data)`
                          : ""}
                    </td>
                    <td>{user.last_login_at ? formatDateTime(user.last_login_at) : "never"}</td>
                    <td className="actions">
                      <button
                        className="button small"
                        onClick={() =>
                          edit({
                            id: user.id,
                            username: user.username,
                            full_name: user.full_name,
                            password: "",
                            role: user.role,
                            faculty_employee_id: user.faculty_employee_id ?? "",
                            is_active: user.is_active,
                          })
                        }
                      >
                        Edit
                      </button>{" "}
                      {user.id !== me.id && (
                        <button className="button small danger" onClick={() => setDeleting(user)}>
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog
        open={draft !== null}
        title={draft?.id ? `Edit ${draft.username}` : "Add account"}
        onClose={() => setDraft(null)}
        onSubmit={() => draft && save.mutate(draft)}
        footer={
          <>
            <button type="button" className="button" onClick={() => setDraft(null)}>
              Cancel
            </button>
            <button type="submit" className="button primary" disabled={save.isPending}>
              Save
            </button>
          </>
        }
      >
        {draft && (
          <>
            <label className="field">
              <span>Username *</span>
              <input value={draft.username} onChange={(e) => setDraft({ ...draft, username: e.target.value })} required />
            </label>
            <label className="field">
              <span>Full name</span>
              <input value={draft.full_name} onChange={(e) => setDraft({ ...draft, full_name: e.target.value })} />
            </label>
            <label className="field">
              <span>Role *</span>
              <select value={draft.role} onChange={(e) => setDraft({ ...draft, role: e.target.value as Role })}>
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {ROLE_LABELS[role]}
                  </option>
                ))}
              </select>
            </label>
            {draft.role === "FACULTY" && (
              <label className="field">
                <span>Faculty member *</span>
                <select
                  value={draft.faculty_employee_id}
                  onChange={(e) => setDraft({ ...draft, faculty_employee_id: e.target.value })}
                  required
                >
                  <option value="">Choose…</option>
                  {facultyOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="field">
              <span>{draft.id ? "New password (leave empty to keep)" : "Password *"}</span>
              <input
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={draft.password}
                required={!draft.id}
                onChange={(e) => setDraft({ ...draft, password: e.target.value })}
              />
            </label>
            <label className="field check">
              <input
                type="checkbox"
                checked={draft.is_active}
                onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })}
              />
              <span>Active (can sign in)</span>
            </label>
            {formError && (
              <p className="field-error" role="alert">
                {formError}
              </p>
            )}
          </>
        )}
      </Dialog>

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
        <p>Delete the account {deleting?.username}?</p>
      </Dialog>

      <Dialog
        open={created !== null}
        title="Faculty accounts"
        onClose={() => setCreated(null)}
        onSubmit={() => setCreated(null)}
        footer={
          <>
            {created && created.length > 0 && (
              <button type="button" className="button" onClick={() => downloadCsv(created)}>
                Download CSV
              </button>
            )}
            <button type="submit" className="button primary">
              Done
            </button>
          </>
        }
      >
        {created && created.length === 0 ? (
          <p>Every active faculty member already has an account.</p>
        ) : (
          <>
            <p className="warn-card card small">
              These passwords are shown <b>only once</b>. Download the CSV and hand them out; faculty can change their
              password after signing in.
            </p>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Name</th>
                    <th>Password</th>
                  </tr>
                </thead>
                <tbody>
                  {(created ?? []).map((item) => (
                    <tr key={item.username}>
                      <td>{item.username}</td>
                      <td>{item.full_name}</td>
                      <td>
                        <code>{item.password}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Dialog>
    </Page>
  );
}
