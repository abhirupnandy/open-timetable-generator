import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { RESOURCE_KEYS, RESOURCES } from "../lib/resources";

const MenuContext = createContext<() => void>(() => {});

const MAIN_LINKS = [
  { to: "/", label: "Overview", end: true },
  { to: "/generate", label: "Generate" },
  { to: "/timetable", label: "Timetable" },
  { to: "/constraints", label: "Constraints" },
];

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

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
            {MAIN_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} end={link.end}>
                {link.label}
              </NavLink>
            ))}
            <div className="nav-section">Data</div>
            {RESOURCE_KEYS.map((key) => (
              <NavLink key={key} to={`/data/${key}`}>
                {RESOURCES[key].label}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-foot">
            <a href="/docs" target="_blank" rel="noopener noreferrer">
              API docs
            </a>
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
