// Timetable Generator web UI: a dependency-free single-page app on top of /api/v1.

const API = "/api/v1";
const DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const $ = (selector, root = document) => root.querySelector(selector);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

const title = (text) => String(text).toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

function errorMessage(body, status) {
  const detail = body && body.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = (item.loc || []).filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join("\n");
  }
  if (typeof detail === "string") return detail;
  return `Request failed (${status})`;
}

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    headers: options.body ? { "Content-Type": "application/json" } : {},
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorMessage(body, response.status));
    error.status = response.status;
    throw error;
  }
  return body;
}

function toast(message, kind = "") {
  const element = document.createElement("div");
  element.className = `toast ${kind}`;
  element.textContent = message;
  $("#toasts").append(element);
  setTimeout(() => element.remove(), kind === "bad" ? 6000 : 3000);
}

function confirmDelete(text) {
  const dialog = $("#confirm-dialog");
  $("#confirm-text").textContent = text;
  dialog.returnValue = "";
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
  });
}

const storage = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* ignore */ } },
};

function hue(text) {
  let hash = 0;
  for (const char of String(text)) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % 360;
}

function badgeFor(status) {
  const kinds = { succeeded: "ok", OPTIMAL: "ok", FEASIBLE: "info", running: "info", infeasible: "warn", failed: "bad" };
  return `<span class="badge ${kinds[status] || ""}">${esc(status)}</span>`;
}

// ---------------------------------------------------------------------------
// Resource definitions (generic CRUD)
// ---------------------------------------------------------------------------

const ENUMS = {
  designation: ["ASSISTANT_PROFESSOR", "ASSOCIATE_PROFESSOR", "PROFESSOR", "PHD_SCHOLAR"],
  time_preference: ["ANY", "MORNING", "AFTERNOON", "EVENING"],
  room_type: ["LECTURE_HALL", "COMPUTER_LAB", "SPECIAL_LAB", "CLASSROOM"],
  subject_type: ["LECTURE", "LAB", "TUTORIAL"],
  group_type: ["GROUP", "BATCH"],
  mode: ["IN_PERSON", "ONLINE", "EITHER"],
  day: DAYS,
  resource_type: ["FACULTY", "ROOM"],
};

const active = { name: "is_active", label: "Active", type: "bool", default: true };

const RESOURCES = {
  schools: {
    label: "Schools", singular: "school", path: "/schools",
    display: (r) => r.code,
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      active,
    ],
    columns: ["code", "name", "is_active"],
  },
  courses: {
    label: "Courses", singular: "course", path: "/courses",
    display: (r) => r.code,
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "school_id", label: "School", type: "ref", ref: "schools", required: true },
      { name: "duration_years", type: "int", required: true, default: 4 },
      { name: "total_semesters", type: "int", required: true, default: 8 },
      active,
    ],
    columns: ["code", "name", "school_id", "duration_years", "total_semesters", "is_active"],
  },
  faculty: {
    label: "Faculty", singular: "faculty member", path: "/faculty",
    display: (r) => r.name,
    fields: [
      { name: "employee_id", label: "Employee ID", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "email", type: "email", required: true },
      { name: "designation", type: "enum", required: true },
      { name: "time_preference", type: "enum", default: "ANY" },
      { name: "preferred_day_off", type: "enum", enum: "day", nullable: true,
        hint: "Used by the faculty_preferred_day_off soft constraint." },
      { name: "school_id", label: "School", type: "ref", ref: "schools", required: true },
      active,
    ],
    columns: ["employee_id", "name", "designation", "time_preference", "preferred_day_off", "is_active"],
  },
  rooms: {
    label: "Rooms", singular: "room", path: "/rooms",
    display: (r) => r.code,
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "room_type", type: "enum", required: true },
      { name: "capacity", type: "int", required: true },
      { name: "school_id", label: "School", type: "ref", ref: "schools", required: true },
      { name: "is_shared", label: "Shared room", type: "bool", default: false,
        hint: "Record external bookings as room unavailability." },
      active,
    ],
    columns: ["code", "name", "room_type", "capacity", "is_shared", "is_active"],
  },
  subjects: {
    label: "Subjects", singular: "subject", path: "/subjects",
    display: (r) => r.code,
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "subject_type", type: "enum", required: true },
      active,
    ],
    columns: ["code", "name", "subject_type", "is_active"],
  },
  groups: {
    label: "Groups & batches", singular: "group", path: "/groups",
    display: (r) => r.code,
    fields: [
      { name: "code", type: "text", required: true },
      { name: "name", type: "text", required: true },
      { name: "group_type", type: "enum", required: true },
      { name: "course_id", label: "Course", type: "ref", ref: "courses", required: true },
      { name: "parent_group_id", label: "Parent group", type: "ref", ref: "groups", nullable: true },
      { name: "capacity", type: "int", nullable: true },
      active,
    ],
    columns: ["code", "name", "group_type", "course_id", "parent_group_id", "capacity", "is_active"],
  },
  assignments: {
    label: "Teaching assignments", singular: "assignment", path: "/assignments",
    display: (r, refs) =>
      [refLabel(refs, "subjects", r.subject_id), refLabel(refs, "groups", r.academic_group_id), refLabel(refs, "faculty", r.faculty_id)].join(" · "),
    fields: [
      { name: "subject_id", label: "Subject", type: "ref", ref: "subjects", required: true },
      { name: "course_id", label: "Course", type: "ref", ref: "courses", required: true },
      { name: "academic_group_id", label: "Group", type: "ref", ref: "groups", required: true },
      { name: "faculty_id", label: "Faculty", type: "ref", ref: "faculty", required: true },
      { name: "sessions_per_week", type: "int", required: true, default: 3 },
      { name: "duration_periods", type: "int", required: true, default: 1 },
      { name: "mode", type: "enum", required: true, default: "IN_PERSON" },
      { name: "required_room_type", type: "enum", enum: "room_type", nullable: true },
      { name: "allow_across_lunch", type: "nullbool",
        hint: "Yes exempts this assignment from the lunch rule." },
      active,
    ],
    columns: ["subject_id", "academic_group_id", "faculty_id", "sessions_per_week", "duration_periods", "mode", "required_room_type", "is_active"],
  },
  unavailability: {
    label: "Unavailability", singular: "unavailability", path: "/unavailability",
    display: (r) => `${r.resource_type} ${r.resource_id} ${r.day}`,
    fields: [
      { name: "resource_type", type: "enum", required: true, createOnly: true },
      { name: "resource_id", label: "Faculty / room", type: "ref",
        ref: (values) => (values.resource_type === "ROOM" ? "rooms" : "faculty"),
        dependsOn: "resource_type", required: true, createOnly: true },
      { name: "day", type: "enum", required: true },
      { name: "start_period", type: "int", required: true, default: 1 },
      { name: "end_period", type: "int", required: true, default: 1 },
      { name: "reason", type: "text", nullable: true },
    ],
    columns: ["resource_type", "resource_id", "day", "start_period", "end_period", "reason"],
  },
  "group-blocked-slots": {
    label: "Group blocked slots", singular: "blocked slot", path: "/group-blocked-slots",
    display: (r) => `${r.day} P${r.period}`,
    fields: [
      { name: "academic_group_id", label: "Group", type: "ref", ref: "groups", required: true, createOnly: true,
        hint: "Also applies to the group's batches." },
      { name: "day", type: "enum", required: true },
      { name: "period", type: "int", required: true, default: 1 },
      { name: "label", type: "text", nullable: true },
    ],
    columns: ["academic_group_id", "day", "period", "label"],
  },
  "session-locks": {
    label: "Session locks", singular: "lock", path: "/session-locks",
    display: (r) => `${r.day} P${r.start_period}`,
    fields: [
      { name: "teaching_assignment_id", label: "Assignment", type: "ref", ref: "assignments", required: true, createOnly: true },
      { name: "session_number", type: "int", required: true, default: 1, createOnly: true },
      { name: "day", type: "enum", required: true },
      { name: "start_period", type: "int", required: true, default: 1 },
      { name: "room_id", label: "Room (optional)", type: "ref", ref: "rooms", nullable: true },
    ],
    columns: ["teaching_assignment_id", "session_number", "day", "start_period", "room_id"],
  },
};

const fieldLabel = (field) => field.label || title(field.name);
const enumOptions = (field) => ENUMS[field.enum || field.name] || [];

// Reference data cache, invalidated after every write.
let refCache = {};

async function loadRefs(keys) {
  await Promise.all(
    [...new Set(keys)].map(async (key) => {
      if (!refCache[key]) refCache[key] = api(RESOURCES[key].path);
      refCache[key] = await refCache[key];
    }),
  );
  return refCache;
}

function refLabel(refs, key, id) {
  if (id === null || id === undefined) return "";
  const row = (refs[key] || []).find((item) => item.id === id);
  if (!row) return `#${id}`;
  return RESOURCES[key].display(row, refs);
}

function refKeysFor(resource) {
  const keys = [];
  for (const field of resource.fields) {
    if (field.type !== "ref") continue;
    if (typeof field.ref === "function") keys.push("faculty", "rooms");
    else keys.push(field.ref);
  }
  if (resource === RESOURCES.assignments || resource === RESOURCES["session-locks"]) {
    keys.push("subjects", "groups", "faculty");
  }
  return keys;
}

function cellValue(resource, refs, row, column) {
  const field = resource.fields.find((item) => item.name === column);
  const value = row[column];
  if (field && field.type === "ref") {
    const key = typeof field.ref === "function" ? field.ref(row) : field.ref;
    return esc(refLabel(refs, key, value));
  }
  if (typeof value === "boolean") return value ? "Yes" : '<span class="muted">No</span>';
  if (value === null || value === undefined || value === "") return '<span class="muted">—</span>';
  if (typeof value === "number") return String(value);
  return esc(ENUMS[field?.enum || column] ? title(value) : value);
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

let renderToken = 0;

const ROUTES = {
  overview: renderOverview,
  generate: renderGenerate,
  timetable: renderTimetable,
  constraints: renderConstraints,
};

function setPage(heading, actions = "") {
  $("#page-title").textContent = heading;
  $("#page-actions").innerHTML = actions;
  document.title = `${heading} · Timetable Generator`;
}

async function route() {
  const token = ++renderToken;
  const [name, arg] = (location.hash.replace(/^#\/?/, "") || "overview").split("/");

  document.querySelectorAll("nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === name || link.dataset.route === `data/${arg}`);
  });
  $("#sidebar").classList.remove("open");

  const view = $("#view");
  view.innerHTML = '<p class="muted">Loading…</p>';

  try {
    if (name === "data" && RESOURCES[arg]) await renderResource(arg, token);
    else if (ROUTES[name]) await ROUTES[name](token);
    else location.hash = "#/overview";
  } catch (error) {
    if (token !== renderToken) return;
    view.innerHTML = `<div class="card"><pre class="error">${esc(error.message)}</pre></div>`;
  }
}

const isCurrent = (token) => token === renderToken;

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

async function renderOverview(token) {
  setPage("Overview", '<a class="button primary" href="#/generate">Generate timetable</a>');
  refCache = {};
  const keys = Object.keys(RESOURCES);
  const [refs, runs] = await Promise.all([loadRefs(keys), api("/timetable/runs")]);
  if (!isCurrent(token)) return;

  const tiles = keys
    .map((key) => `
      <a class="tile" href="#/data/${key}">
        <div class="tile-label">${esc(RESOURCES[key].label)}</div>
        <div class="tile-value">${refs[key].length}</div>
      </a>`)
    .join("");

  const sessions = refs.assignments
    .filter((row) => row.is_active)
    .reduce((sum, row) => sum + row.sessions_per_week, 0);

  const latest = runs[0];
  const latestHtml = latest
    ? `<p>${badgeFor(latest.status)} started ${esc(new Date(latest.started_at).toLocaleString())},
         ${latest.elapsed_seconds}s${latest.total_weighted_penalty != null ? `, weighted penalty <b>${latest.total_weighted_penalty}</b>` : ""}</p>
       <p><a href="#/timetable">Open timetable</a> · <a href="#/generate">Run details</a></p>`
    : '<p class="muted">No timetable generated since the server started.</p><p><a href="#/generate">Generate one</a></p>';

  $("#view").innerHTML = `
    <div class="tiles">${tiles}</div>
    <div class="grid-2">
      <div class="card">
        <h2>Weekly demand</h2>
        <p><b>${sessions}</b> sessions per week from
           <b>${refs.assignments.filter((row) => row.is_active).length}</b> active assignments.</p>
      </div>
      <div class="card"><h2>Latest run</h2>${latestHtml}</div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Generic resource page
// ---------------------------------------------------------------------------

const tableState = {};

async function renderResource(key, token) {
  const resource = RESOURCES[key];
  setPage(resource.label, `<button class="button primary" id="add-record">Add ${esc(resource.singular)}</button>`);

  const [rows, refs] = await Promise.all([api(resource.path), loadRefs(refKeysFor(resource))]);
  if (!isCurrent(token)) return;

  const state = (tableState[key] ||= { query: "", sort: null, desc: false });

  $("#view").innerHTML = `
    <div class="card">
      <div class="toolbar">
        <input type="search" id="table-search" placeholder="Filter ${esc(resource.label.toLowerCase())}…" value="${esc(state.query)}" aria-label="Filter">
        <span class="spacer"></span>
        <span class="muted" id="table-count"></span>
      </div>
      <div class="table-wrap" id="table-wrap"></div>
    </div>`;

  const draw = () => {
    const query = state.query.trim().toLowerCase();
    const labelled = rows.map((row) => ({
      row,
      text: resource.columns.map((column) => cellValue(resource, refs, row, column).replace(/<[^>]+>/g, "")),
    }));
    let visible = query
      ? labelled.filter((item) => item.text.join(" ").toLowerCase().includes(query))
      : labelled;

    if (state.sort !== null) {
      const index = state.sort;
      visible = [...visible].sort((a, b) => {
        const left = a.row[resource.columns[index]];
        const right = b.row[resource.columns[index]];
        const result = typeof left === "number" && typeof right === "number"
          ? left - right
          : a.text[index].localeCompare(b.text[index], undefined, { numeric: true });
        return state.desc ? -result : result;
      });
    }

    $("#table-count").textContent = `${visible.length} of ${rows.length}`;

    if (!rows.length) {
      $("#table-wrap").innerHTML = `<div class="empty">No ${esc(resource.label.toLowerCase())} yet.</div>`;
      return;
    }

    const head = resource.columns
      .map((column, index) => {
        const field = resource.fields.find((item) => item.name === column);
        const arrow = state.sort === index ? (state.desc ? " ↓" : " ↑") : "";
        return `<th class="sortable" data-sort="${index}">${esc(field ? fieldLabel(field) : title(column))}${arrow}</th>`;
      })
      .join("");

    const body = visible
      .map(({ row }) => `
        <tr>
          ${resource.columns.map((column) => `<td>${cellValue(resource, refs, row, column)}</td>`).join("")}
          <td class="actions">
            <button class="button small" data-edit="${row.id}">Edit</button>
            <button class="button small danger" data-delete="${row.id}">Delete</button>
          </td>
        </tr>`)
      .join("");

    $("#table-wrap").innerHTML = `
      <table class="data">
        <thead><tr>${head}<th></th></tr></thead>
        <tbody>${body || `<tr><td colspan="${resource.columns.length + 1}" class="empty">No matches.</td></tr>`}</tbody>
      </table>`;
  };

  draw();

  $("#table-search").addEventListener("input", (event) => {
    state.query = event.target.value;
    draw();
  });

  $("#table-wrap").addEventListener("click", async (event) => {
    const sort = event.target.closest("[data-sort]");
    if (sort) {
      const index = Number(sort.dataset.sort);
      state.desc = state.sort === index ? !state.desc : false;
      state.sort = index;
      draw();
      return;
    }

    const edit = event.target.closest("[data-edit]");
    if (edit) {
      const row = rows.find((item) => item.id === Number(edit.dataset.edit));
      openForm(key, row);
      return;
    }

    const remove = event.target.closest("[data-delete]");
    if (remove) {
      const row = rows.find((item) => item.id === Number(remove.dataset.delete));
      const label = resource.display(row, refs);
      if (!(await confirmDelete(`Delete ${resource.singular} “${label}”?`))) return;
      try {
        await api(`${resource.path}/${row.id}`, { method: "DELETE" });
        refCache = {};
        toast(`Deleted ${label}`);
        route();
      } catch (error) {
        toast(error.message, "bad");
      }
    }
  });

  $("#add-record").addEventListener("click", () => openForm(key, null));
}

// ---------------------------------------------------------------------------
// Record form
// ---------------------------------------------------------------------------

function fieldInput(field, value, refs, values, editing) {
  const id = `f-${field.name}`;
  const disabled = editing && field.createOnly ? "disabled" : "";
  const required = field.required ? "required" : "";

  if (field.type === "bool") {
    return `<label class="field check"><input type="checkbox" id="${id}" name="${field.name}" ${value ? "checked" : ""} ${disabled}>
      <span>${esc(fieldLabel(field))}</span></label>${field.hint ? `<div class="hint muted">${esc(field.hint)}</div>` : ""}`;
  }

  let control;

  if (field.type === "enum" || field.type === "nullbool" || field.type === "ref") {
    let options;
    if (field.type === "enum") {
      options = enumOptions(field).map((option) => [option, title(option)]);
    } else if (field.type === "nullbool") {
      options = [["true", "Yes"], ["false", "No"]];
    } else {
      const key = typeof field.ref === "function" ? field.ref(values) : field.ref;
      options = (refs[key] || []).map((row) => [String(row.id), RESOURCES[key].display(row, refs)]);
    }
    const blank = field.required && field.type !== "nullbool" ? "Select…" : "—";
    const current = value === null || value === undefined ? "" : String(value);
    control = `<select id="${id}" name="${field.name}" ${required} ${disabled}>
      <option value="">${blank}</option>
      ${options.map(([optionValue, label]) => `<option value="${esc(optionValue)}" ${optionValue === current ? "selected" : ""}>${esc(label)}</option>`).join("")}
    </select>`;
  } else {
    const type = field.type === "int" ? "number" : field.type;
    const extra = field.type === "int" ? 'min="0" step="1"' : "";
    control = `<input id="${id}" name="${field.name}" type="${type}" value="${esc(value ?? "")}" ${extra} ${required} ${disabled}>`;
  }

  return `<label class="field" for="${id}"><span>${esc(fieldLabel(field))}${field.required ? " *" : ""}</span>${control}
    ${field.hint ? `<span class="hint">${esc(field.hint)}</span>` : ""}</label>`;
}

function readField(form, field) {
  const element = form.elements[field.name];
  if (!element) return undefined;
  if (field.type === "bool") return element.checked;
  const raw = element.value;
  if (raw === "") return field.type === "text" && field.required ? "" : null;
  if (field.type === "int" || field.type === "ref") return Number(raw);
  if (field.type === "nullbool") return raw === "true";
  return raw;
}

async function openForm(key, row) {
  const resource = RESOURCES[key];
  const refs = await loadRefs(refKeysFor(resource));
  const dialog = $("#form-dialog");
  const form = $("#record-form");
  const editing = Boolean(row);

  const values = {};
  for (const field of resource.fields) {
    values[field.name] = editing ? row[field.name] : field.default ?? (field.type === "bool" ? false : null);
  }

  const drawFields = () => {
    $("#form-fields").innerHTML = resource.fields
      .map((field) => fieldInput(field, values[field.name], refs, values, editing))
      .join("");
  };

  drawFields();
  $("#form-title").textContent = editing ? `Edit ${resource.singular}` : `Add ${resource.singular}`;
  $("#form-error").textContent = "";

  form.onchange = (event) => {
    const field = resource.fields.find((item) => item.name === event.target.name);
    if (!field) return;
    values[field.name] = readField(form, field);
    if (resource.fields.some((item) => item.dependsOn === field.name)) {
      for (const dependent of resource.fields.filter((item) => item.dependsOn === field.name)) {
        values[dependent.name] = null;
      }
      drawFields();
    }
  };

  form.onsubmit = async (event) => {
    event.preventDefault();
    const payload = {};
    for (const field of resource.fields) {
      if (editing && field.createOnly) continue;
      const value = readField(form, field);
      if (value !== undefined) payload[field.name] = value;
    }

    const missing = resource.fields.filter(
      (field) => field.required && !(editing && field.createOnly) && (payload[field.name] === null || payload[field.name] === ""),
    );
    if (missing.length) {
      $("#form-error").textContent = `Required: ${missing.map(fieldLabel).join(", ")}`;
      return;
    }

    $("#form-submit").disabled = true;
    try {
      if (editing) await api(`${resource.path}/${row.id}`, { method: "PATCH", body: payload });
      else await api(resource.path, { method: "POST", body: payload });
      refCache = {};
      dialog.close();
      toast(editing ? "Saved" : `Added ${resource.singular}`);
      route();
    } catch (error) {
      $("#form-error").textContent = error.message;
    } finally {
      $("#form-submit").disabled = false;
    }
  };

  dialog.querySelectorAll("[data-close]").forEach((button) => {
    button.onclick = () => dialog.close();
  });

  dialog.showModal();
  dialog.querySelector("input:not([disabled]), select:not([disabled])")?.focus();
}

// ---------------------------------------------------------------------------
// Generate
// ---------------------------------------------------------------------------

let configCache = null;

async function loadConfig() {
  configCache ||= await api("/timetable/config");
  return configCache;
}

function constraintChips(config) {
  const chips = [];
  for (const [key, item] of Object.entries(config.hard)) {
    chips.push(`<span class="chip ${item.enabled ? "" : "off"}"><b>${esc(key)}</b> ${item.enabled ? "hard" : "off"}</span>`);
  }
  for (const [key, item] of Object.entries(config.constraints)) {
    const text = item.mode === "soft" ? `soft ×${item.weight}` : item.mode;
    chips.push(`<span class="chip ${item.mode === "off" ? "off" : ""}"><b>${esc(key)}</b> ${esc(text)}</span>`);
  }
  for (const [key, item] of Object.entries(config.soft)) {
    chips.push(`<span class="chip ${item.enabled ? "" : "off"}"><b>${esc(key)}</b> ${item.enabled ? `×${item.weight}` : "off"}</span>`);
  }
  return chips.join("");
}

async function renderGenerate(token) {
  setPage("Generate timetable");
  const [{ config }, runs] = await Promise.all([loadConfig(), api("/timetable/runs")]);
  if (!isCurrent(token)) return;

  const selectedId = storage.get("selectedRun");
  const selected = runs.find((run) => run.id === selectedId) || runs[0];

  $("#view").innerHTML = `
    <div class="card">
      <div class="run-bar">
        <label class="field"><span>Time limit (seconds)</span>
          <input type="number" id="time-limit" min="1" max="3600" value="${esc(storage.get("timeLimit") || config.solver.max_time_seconds)}">
        </label>
        <button class="button primary" id="start-run">Run solver</button>
        <span class="muted">${config.solver.workers} workers · constraints from <span class="mono">config/timetable.toml</span></span>
      </div>
      <details style="margin-top:14px"><summary class="muted">Active constraints</summary>
        <div class="chips" style="margin-top:10px">${constraintChips(config)}</div>
      </details>
    </div>
    <div id="run-detail"></div>
    <div class="card">
      <h2>Runs</h2>
      <div id="run-list"></div>
    </div>`;

  drawRunList(runs, selected?.id);

  $("#start-run").addEventListener("click", async () => {
    const limit = Number($("#time-limit").value);
    storage.set("timeLimit", String(limit));
    $("#start-run").disabled = true;
    try {
      const run = await api("/timetable/runs", { method: "POST", body: { max_time_seconds: limit } });
      storage.set("selectedRun", run.id);
      toast("Solver started");
      showRun(run.id, token);
      drawRunList(await api("/timetable/runs"), run.id);
    } catch (error) {
      toast(error.message, "bad");
    } finally {
      $("#start-run").disabled = false;
    }
  });

  $("#run-list").addEventListener("click", (event) => {
    const link = event.target.closest("[data-run]");
    if (!link) return;
    event.preventDefault();
    storage.set("selectedRun", link.dataset.run);
    showRun(link.dataset.run, token);
  });

  if (selected) showRun(selected.id, token);
}

function drawRunList(runs, selectedId) {
  const target = $("#run-list");
  if (!target) return;
  if (!runs.length) {
    target.innerHTML = '<p class="muted">No runs yet. Runs are kept in memory until the server restarts.</p>';
    return;
  }
  target.innerHTML = `
    <div class="table-wrap"><table class="data">
      <thead><tr><th>Started</th><th>Status</th><th>Solver</th><th class="num">Time (s)</th><th class="num">Weighted penalty</th><th></th></tr></thead>
      <tbody>${runs.map((run) => `
        <tr>
          <td>${esc(new Date(run.started_at).toLocaleString())}</td>
          <td>${badgeFor(run.status)}</td>
          <td>${run.solver_status ? badgeFor(run.solver_status) : ""}</td>
          <td class="num">${run.elapsed_seconds}</td>
          <td class="num">${run.total_weighted_penalty ?? ""}</td>
          <td class="actions">${run.id === selectedId ? '<span class="muted">shown</span>' : `<a href="#" data-run="${run.id}">Show</a>`}</td>
        </tr>`).join("")}
      </tbody>
    </table></div>`;
}

let shownRun = null;

async function showRun(runId, token) {
  shownRun = runId;
  let run;
  try {
    run = await api(`/timetable/runs/${runId}`);
  } catch (error) {
    if (error.status === 404) return;
    throw error;
  }
  if (!isCurrent(token) || shownRun !== runId) return;
  const target = $("#run-detail");
  if (!target) return;

  if (run.status === "running") {
    const percent = Math.min(100, (run.elapsed_seconds / run.max_time_seconds) * 100);
    target.innerHTML = `
      <div class="card">
        <div class="card-head"><h2>Solving ${run.session_count} sessions…</h2>${badgeFor("running")}</div>
        <p class="muted">${run.elapsed_seconds.toFixed(0)}s of up to ${run.max_time_seconds}s. CP-SAT keeps improving until the time limit.</p>
        <div class="progress"><div style="width:${percent}%"></div></div>
      </div>`;
    setTimeout(async () => {
      if (!isCurrent(token) || shownRun !== runId) return;
      await showRun(runId, token);
    }, 1000);
    return;
  }

  // Finished: refresh the run list once so its status column is current.
  if (run.finished_at && $("#run-list")) {
    drawRunList(await api("/timetable/runs"), runId);
  }

  if (run.status !== "succeeded") {
    target.innerHTML = `
      <div class="card">
        <div class="card-head"><h2>Run ${esc(run.id)}</h2>${badgeFor(run.status)}</div>
        <pre class="error">${esc(run.error)}</pre>
      </div>`;
    return;
  }

  const result = run.result;
  const report = result.score_report;
  const metrics = Object.entries(report.metrics)
    .map(([key, value]) => `<div class="tile"><div class="tile-label">${esc(title(key))}</div><div class="tile-value">${value}</div></div>`)
    .join("");

  const rows = report.constraints
    .map((row) => `
      <tr class="${row.mismatch ? "mismatch" : ""} ${row.mode === "off" ? "off" : ""}">
        <td>${esc(row.key)} ${row.constraint_id ? `<span class="badge">${esc(row.constraint_id)}</span>` : ""}</td>
        <td>${esc(row.mode)}</td>
        <td class="num">${row.weight}</td>
        <td class="num">${row.raw_penalty}</td>
        <td class="num">${row.weighted_penalty}</td>
        <td class="num">${row.solver_penalty ?? "—"}</td>
        <td>${row.mismatch ? '<span class="badge bad">mismatch</span>' : row.solver_penalty != null ? '<span class="badge ok">ok</span>' : ""}</td>
      </tr>`)
    .join("");

  const validation = result.validation.is_valid
    ? '<span class="badge ok">All hard constraints pass</span>'
    : `<span class="badge bad">${result.validation.conflicts} conflicts, ${result.validation.violations.length} violations</span>`;

  target.innerHTML = `
    <div class="card">
      <div class="card-head">
        <h2>Run ${esc(run.id)}</h2>
        <div>${badgeFor(report.status)} ${validation}</div>
      </div>
      <p class="muted">Objective ${report.objective_value ?? "—"} · best bound ${report.best_bound ?? "—"} ·
        solve ${report.wall_time_seconds}s · build ${report.build_time_seconds}s ·
        ${report.model_stats.candidates} candidates, ${report.model_stats.variables} variables</p>
      <div class="tiles">${metrics}</div>
      <div class="toolbar">
        <a class="button primary" href="#/timetable">View timetable</a>
        ${run.files.map((file) => `<a class="button" href="${API}/timetable/runs/${run.id}/files/${file.name}" download>${esc(file.label)}</a>`).join("")}
      </div>
      ${result.diagnostics.length ? `<p class="muted">${result.diagnostics.map(esc).join("<br>")}</p>` : ""}
    </div>
    <div class="card">
      <h2>Score report</h2>
      <div class="table-wrap"><table class="data">
        <thead><tr><th>Constraint</th><th>Mode</th><th class="num">Weight</th><th class="num">Raw</th><th class="num">Weighted</th><th class="num">Solver</th><th>Check</th></tr></thead>
        <tbody>${rows}</tbody>
        <tfoot><tr><td colspan="4"><b>Total weighted penalty</b></td><td class="num"><b>${report.total_weighted_penalty}</b></td><td colspan="2"></td></tr></tfoot>
      </table></div>
      <p class="muted">“Raw” is computed independently from the finished timetable; “Solver” is the CP-SAT penalty variable. They must match.</p>
    </div>`;
}

// ---------------------------------------------------------------------------
// Timetable grid
// ---------------------------------------------------------------------------

function relatedGroups(code, parents) {
  const related = new Set([code]);
  let current = parents[code];
  while (current && !related.has(current)) {
    related.add(current);
    current = parents[current];
  }
  for (const other of Object.keys(parents)) {
    let ancestor = parents[other];
    const seen = new Set();
    while (ancestor && !seen.has(ancestor)) {
      if (ancestor === code) {
        related.add(other);
        break;
      }
      seen.add(ancestor);
      ancestor = parents[ancestor];
    }
  }
  return related;
}

function sessionCard(entry, by) {
  const meta = [];
  if (by !== "group") meta.push(entry.group_code);
  if (by !== "faculty") meta.push(entry.faculty);
  if (by !== "room") meta.push(entry.room || "Online");
  return `<div class="session" style="--hue:${hue(entry.subject)}" title="${esc(entry.session_id)}">
    <div class="s-title">${esc(entry.subject)}</div>
    <div class="s-meta">${meta.map(esc).join(" · ")}</div>
  </div>`;
}

function gridHtml(entries, calendar, by, blocked) {
  const periods = calendar.periods;
  const lunch = calendar.lunch_after_period;
  const ids = (list) => list.map((entry) => entry.session_id).sort().join("|");

  const head = periods
    .map((period) => {
      const time = period.start ? `<small>${period.start}–${period.end}</small>` : "";
      const cell = `<th>P${period.number}${time}</th>`;
      return period.number === lunch ? `${cell}<th class="lunch" title="Lunch"></th>` : cell;
    })
    .join("");

  const body = calendar.days
    .map((day) => {
      const cells = [];
      let index = 0;
      while (index < periods.length) {
        const number = periods[index].number;
        const here = entries.filter((entry) => entry.day === day && entry.start_period <= number && entry.end_period >= number);
        let span = 1;
        if (here.length) {
          while (index + span < periods.length && number + span - 1 !== lunch) {
            const next = number + span;
            const there = entries.filter((entry) => entry.day === day && entry.start_period <= next && entry.end_period >= next);
            if (ids(there) !== ids(here)) break;
            span += 1;
          }
        }
        const block = blocked.find((slot) => slot.day === day && slot.period === number);
        let cell;
        if (!here.length && block) cell = `<td class="blocked">${esc(block.label || "Blocked")}</td>`;
        else cell = `<td colspan="${span}">${here.map((entry) => sessionCard(entry, by)).join("")}</td>`;
        cells.push(cell);
        const last = number + span - 1;
        if (last === lunch) cells.push('<td class="lunch"></td>');
        index += span;
      }
      return `<tr><th class="day">${esc(title(day))}</th>${cells.join("")}</tr>`;
    })
    .join("");

  return `<div class="tt-wrap"><table class="tt"><thead><tr><th class="day"></th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

async function renderTimetable(token) {
  setPage("Timetable", '<button class="button" id="print-grid">Print</button>');
  const [runs, { config }] = await Promise.all([api("/timetable/runs"), loadConfig()]);
  if (!isCurrent(token)) return;

  const succeeded = runs.filter((run) => run.status === "succeeded");
  if (!succeeded.length) {
    $("#view").innerHTML = `<div class="card empty">No timetable yet. <a href="#/generate">Generate one</a> first.</div>`;
    $("#page-actions").innerHTML = "";
    return;
  }

  const preferred = storage.get("selectedRun");
  const runId = (succeeded.find((run) => run.id === preferred) || succeeded[0]).id;
  const run = await api(`/timetable/runs/${runId}`);
  if (!isCurrent(token)) return;

  const { entries, calendar, group_parents: parents } = run.result;
  const blocked = config.calendar.blocked_slots;

  const options = {
    group: [...new Set([...Object.keys(parents), ...entries.map((entry) => entry.group_code)])].sort(),
    faculty: [...new Set(entries.map((entry) => entry.faculty))].sort(),
    room: [...new Set(entries.map((entry) => entry.room).filter(Boolean))].sort(),
  };

  const state = {
    by: storage.get("ttBy") || "group",
    entity: storage.get("ttEntity") || "",
  };

  $("#view").innerHTML = `
    <div class="card">
      <div class="toolbar">
        <label>Run
          <select id="tt-run">${succeeded.map((item) => `<option value="${item.id}" ${item.id === runId ? "selected" : ""}>${esc(new Date(item.started_at).toLocaleString())} · ${item.total_weighted_penalty}</option>`).join("")}</select>
        </label>
        <label>View by
          <select id="tt-by">${["group", "faculty", "room"].map((by) => `<option value="${by}">${title(by)}</option>`).join("")}</select>
        </label>
        <select id="tt-entity" aria-label="Entity"></select>
        <button class="button small" id="tt-prev" aria-label="Previous">‹</button>
        <button class="button small" id="tt-next" aria-label="Next">›</button>
        <span class="spacer"></span>
        <span class="muted" id="tt-count"></span>
      </div>
      <h2 id="tt-heading"></h2>
      <div id="tt-grid"></div>
      <div class="legend"><span>Hatched: blocked slot</span><span>Striped column: lunch</span>
        <span>Group view includes parent-group and batch sessions.</span></div>
    </div>`;

  const draw = () => {
    const list = options[state.by];
    if (!list.includes(state.entity)) state.entity = list[0] || "";
    $("#tt-by").value = state.by;
    $("#tt-entity").innerHTML = list.map((item) => `<option ${item === state.entity ? "selected" : ""}>${esc(item)}</option>`).join("");
    storage.set("ttBy", state.by);
    storage.set("ttEntity", state.entity);

    let selected;
    if (state.by === "group") {
      const related = relatedGroups(state.entity, parents);
      selected = entries.filter((entry) => related.has(entry.group_code));
    } else if (state.by === "faculty") {
      selected = entries.filter((entry) => entry.faculty === state.entity);
    } else {
      selected = entries.filter((entry) => entry.room === state.entity);
    }

    const name = state.by === "group" ? entries.find((entry) => entry.group_code === state.entity)?.group_name : "";
    $("#tt-heading").textContent = name ? `${state.entity} · ${name}` : state.entity;
    const periods = selected.reduce((sum, entry) => sum + entry.end_period - entry.start_period + 1, 0);
    $("#tt-count").textContent = `${selected.length} sessions · ${periods} periods`;
    $("#tt-grid").innerHTML = list.length ? gridHtml(selected, calendar, state.by, blocked) : '<div class="empty">Nothing to show.</div>';
  };

  draw();

  $("#tt-run").addEventListener("change", (event) => {
    storage.set("selectedRun", event.target.value);
    route();
  });
  $("#tt-by").addEventListener("change", (event) => { state.by = event.target.value; state.entity = ""; draw(); });
  $("#tt-entity").addEventListener("change", (event) => { state.entity = event.target.value; draw(); });
  const step = (delta) => {
    const list = options[state.by];
    const index = list.indexOf(state.entity);
    state.entity = list[(index + delta + list.length) % list.length];
    draw();
  };
  $("#tt-prev").addEventListener("click", () => step(-1));
  $("#tt-next").addEventListener("click", () => step(1));
  $("#print-grid").addEventListener("click", () => window.print());
}

// ---------------------------------------------------------------------------
// Constraints (read-only view of config/timetable.toml)
// ---------------------------------------------------------------------------

function params(item, skip) {
  const entries = Object.entries(item).filter(([key]) => !skip.includes(key));
  if (!entries.length) return '<span class="muted">—</span>';
  return entries
    .map(([key, value]) => `<span class="mono">${esc(key)}=${esc(typeof value === "object" ? JSON.stringify(value) : value)}</span>`)
    .join("<br>");
}

async function renderConstraints(token) {
  setPage("Constraints");
  configCache = null;
  const { config } = await loadConfig();
  if (!isCurrent(token)) return;

  const calendar = config.calendar;
  const periodRows = calendar.periods
    .map((period) => `<tr><td>P${period.number}</td><td>${period.start}</td><td>${period.end}</td>
      <td>${period.number === calendar.lunch_after_period ? '<span class="badge">lunch after</span>' : ""}</td></tr>`)
    .join("");

  const hardRows = Object.entries(config.hard)
    .map(([key, item]) => `<tr class="${item.enabled ? "" : "off"}"><td>${esc(key)}</td><td>${item.enabled ? '<span class="badge ok">on</span>' : "off"}</td><td>${params(item, ["enabled"])}</td></tr>`)
    .join("");

  const flexibleRows = Object.entries(config.constraints)
    .map(([key, item]) => `<tr class="${item.mode === "off" ? "off" : ""}"><td>${esc(key)}</td><td>${esc(item.mode)}</td><td class="num">${item.weight}</td><td>${params(item, ["mode", "weight"])}</td></tr>`)
    .join("");

  const softRows = Object.entries(config.soft)
    .map(([key, item]) => `<tr class="${item.enabled ? "" : "off"}"><td>${esc(key)}</td><td>${item.enabled ? '<span class="badge ok">on</span>' : "off"}</td><td class="num">${item.weight}</td><td>${params(item, ["enabled", "weight"])}</td></tr>`)
    .join("");

  $("#view").innerHTML = `
    <div class="card">
      <p class="muted" style="margin:0">Read-only. Edit <span class="mono">config/timetable.toml</span> and restart the server to change constraints.
      Always on: each session placed once; no faculty, student or room overlap; session fits in the day; room type, capacity and online/in-person rules.</p>
    </div>
    <div class="grid-2">
      <div class="card">
        <h2>Calendar</h2>
        <p>${calendar.days.map((day) => title(day)).join(", ")}</p>
        <div class="table-wrap"><table class="data"><thead><tr><th>Period</th><th>Start</th><th>End</th><th></th></tr></thead><tbody>${periodRows}</tbody></table></div>
        <p class="muted">Blocked for everyone: ${calendar.blocked_slots.map((slot) => `${title(slot.day)} P${slot.period}${slot.label ? ` (${esc(slot.label)})` : ""}`).join(", ") || "none"}</p>
      </div>
      <div class="card">
        <h2>Solver</h2>
        <p>Time limit ${config.solver.max_time_seconds}s · ${config.solver.workers} workers</p>
        <h2 style="margin-top:20px">Optional hard constraints</h2>
        <div class="table-wrap"><table class="data"><thead><tr><th>Key</th><th>State</th><th>Parameters</th></tr></thead><tbody>${hardRows}</tbody></table></div>
      </div>
    </div>
    <div class="card">
      <h2>Flexible constraints</h2>
      <div class="table-wrap"><table class="data"><thead><tr><th>Key</th><th>Mode</th><th class="num">Weight</th><th>Parameters</th></tr></thead><tbody>${flexibleRows}</tbody></table></div>
    </div>
    <div class="card">
      <h2>Soft constraints</h2>
      <div class="table-wrap"><table class="data"><thead><tr><th>Key</th><th>State</th><th class="num">Weight</th><th>Parameters</th></tr></thead><tbody>${softRows}</tbody></table></div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

$("#nav-data").innerHTML = Object.entries(RESOURCES)
  .map(([key, resource]) => `<a href="#/data/${key}" data-route="data/${key}">${esc(resource.label)}</a>`)
  .join("");

$("#menu-toggle").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
window.addEventListener("hashchange", route);
route();
