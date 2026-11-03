import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { api } from "../lib/api";
import { ROLE_LABELS, useAuth } from "../lib/auth";
import { RESOURCE_KEYS, RESOURCES } from "../lib/resources";
import { Dialog } from "./Dialog";
import { useToast } from "./Toasts";

const MenuContext = createContext<() => void>(() => {});

const MAIN_LINKS = [
  { to: "/", label: "Overview", end: true },
  { to: "/import", label: "Import data" },
  { to: "/constraints", label: "Constraints" },
  { to: "/generate", label: "Generate" },
  { to: "/runs", label: "Run history" },
  { to: "/timetable", label: "Timetable" },
];

function UserBox() {
  const { user, signOut } = useAuth();
  const toast = useToast();
  const [changing, setChanging] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");

  const close = () => {
    setChanging(false);
    setCurrent("");
    setNext("");
    setError("");
  };

  const submit = async () => {
    try {
      await api.changePassword(current, next);
      toast("Password changed");
      close();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    }
  };

  const name = user.faculty?.name ?? (user.full_name || user.username);
  const role = user.faculty ? `${user.faculty.designation_label} · ${ROLE_LABELS[user.role]}` : ROLE_LABELS[user.role];

  return (
    <div className="user-box">
      <div className="user-name">{name}</div>
      <div className="muted small">{role}</div>
      <div className="user-actions">
        <button className="link-button" onClick={() => setChanging(true)}>
          Change password
        </button>
        <button className="link-button" onClick={() => void signOut()}>
          Sign out
        </button>
      </div>
      <Dialog
        open={changing}
        small
        title="Change password"
        onClose={close}
        onSubmit={() => void submit()}
        footer={
          <>
            <button type="button" className="button" onClick={close}>
              Cancel
            </button>
            <button type="submit" className="button primary">
              Change
            </button>
          </>
        }
      >
        <label className="field">
          <span>Current password</span>
          <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
        </label>
        <label className="field">
          <span>New password (min 8 characters)</span>
          <input type="password" autoComplete="new-password" minLength={8} value={next} onChange={(e) => setNext(e.target.value)} required />
        </label>
        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
      </Dialog>
    </div>
  );
}

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { isStaff, isAdmin } = useAuth();

  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <MenuContext.Provider value={() => setOpen((value) => !value)}>
      <div className="layout">
        <aside className={`sidebar ${open ? "open" : ""}`}>
          <div className="brand">
            <span className="brand-mark" aria-hidden="true" />
            <span>Timetable Generator</span>
          </div>
          <nav aria-label="Main">
            {isStaff ? (
              <>
                {MAIN_LINKS.map((link) => (
                  <NavLink key={link.to} to={link.to} end={link.end}>
                    {link.label}
                  </NavLink>
                ))}
                <div className="nav-section">Edit data</div>
                {RESOURCE_KEYS.map((key) => (
                  <NavLink key={key} to={`/data/${key}`}>
                    {RESOURCES[key].label}
                  </NavLink>
                ))}
                {isAdmin && (
                  <>
                    <div className="nav-section">Administration</div>
                    <NavLink to="/users">User accounts</NavLink>
                  </>
                )}
              </>
            ) : (
              <NavLink to="/timetable">My timetable</NavLink>
            )}
          </nav>
          <div className="sidebar-foot">
            <UserBox />
            {isStaff && (
              <a href="/docs" target="_blank" rel="noopener noreferrer">
                API docs
              </a>
            )}
          </div>
        </aside>
        <div className="main">
          <Outlet />
        </div>
      </div>
    </MenuContext.Provider>
  );
}

export function Page({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  const toggleMenu = useContext(MenuContext);

  useEffect(() => {
    document.title = `${title} · Timetable Generator`;
  }, [title]);

  return (
    <>
      <header className="topbar">
        <button className="icon-button menu-toggle" onClick={toggleMenu} aria-label="Toggle navigation">
          ☰
        </button>
        <h1>{title}</h1>
        <div className="topbar-actions">{actions}</div>
      </header>
      <main className="view">{children}</main>
    </>
  );
}
