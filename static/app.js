const state = { data: null, view: "schedule", resource: "faculty", search: "", listMode: false };
const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const resourceMeta = {
  faculty: { title: "Faculty members", description: "Faculty who teach classes during this term.", singular: "faculty member", columns: [["name", "Name"], ["department", "Department"], ["email", "Email"]], fields: [{ name: "name", label: "Full name", required: true }, { name: "department", label: "Department" }, { name: "email", label: "Email", type: "email" }] },
  subjects: { title: "Subjects", description: "Subjects assigned to a faculty member and student batch.", singular: "subject", columns: [["code", "Code"], ["name", "Subject name"], ["faculty_name", "Faculty"], ["batch_name", "Batch"], ["sessions_per_week", "Sessions / week"]], fields: [{ name: "code", label: "Subject code", required: true }, { name: "name", label: "Subject name", required: true }, { name: "faculty_id", label: "Faculty", type: "faculty" }, { name: "batch_id", label: "Student batch", type: "batch" }, { name: "sessions_per_week", label: "Sessions per week", type: "number", min: 1, max: 10, value: 2 }] },
  batches: { title: "Student batches", description: "Manage student groups and the number of seats each room must support.", singular: "batch", columns: [["name", "Batch"], ["program", "Program"], ["student_count", "Students"]], fields: [{ name: "name", label: "Batch name", required: true }, { name: "program", label: "Program" }, { name: "student_count", label: "Student count", type: "number", min: 1, value: 30 }] },
  rooms: { title: "Classrooms", description: "Classrooms and their seating capacity.", singular: "classroom", columns: [["name", "Room"], ["building", "Building"], ["capacity", "Capacity"]], fields: [{ name: "name", label: "Room name", required: true }, { name: "building", label: "Building" }, { name: "capacity", label: "Seating capacity", type: "number", min: 1, value: 40 }] },
  slots: { title: "Time slots", description: "Weekly time periods available for classes.", singular: "time slot", columns: [["day", "Day"], ["start_time", "Starts"], ["end_time", "Ends"]], fields: [{ name: "day", label: "Day", type: "day" }, { name: "start_time", label: "Start time", type: "time" }, { name: "end_time", label: "End time", type: "time" }] },
};

function esc(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])); }
function id(name) { return document.getElementById(name); }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) } });
  const type = response.headers.get("content-type") || "";
  const result = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(result.error || "Something went wrong. Please try again.");
  return result;
}
function toast(message, type = "") {
  const node = document.createElement("div"); node.className = `toast ${type}`; node.textContent = message; id("toast-region").append(node); setTimeout(() => node.remove(), 3800);
}
async function refresh() { state.data = await api("/api/data"); renderAll(); }
function setView(view) {
  state.view = view;
  document.querySelectorAll(".view").forEach(node => node.classList.toggle("active-view", node.id === `view-${view}`));
  document.querySelectorAll(".nav-item").forEach(node => node.classList.toggle("active", node.dataset.view === view));
  id("crumb-current").textContent = view === "schedule" ? "Timetable" : view === "resources" ? "Resources" : "Algorithms";
  window.location.hash = view;
  if (view === "resources") renderResources();
}
function renderAll() { renderStats(); renderBatchFilter(); renderSchedule(); renderResources(); }
function renderStats() {
  const d = state.data, count = d.schedule.length;
  id("stat-classes").textContent = count;
  id("stat-batches").textContent = d.batches.length;
  id("stat-faculty").textContent = d.faculty.length;
  const total = d.slots.length * Math.max(d.rooms.length, 1);
  const utilization = total ? Math.min(100, Math.round(count / total * 100)) : 0;
  id("stat-utilization").textContent = utilization;
  id("utilization-bar").style.width = `${utilization}%`;
  for (const key of Object.keys(resourceMeta)) id(`count-${key}`).textContent = d[key].length;
}
function renderBatchFilter() {
  const select = id("batch-filter"), previous = select.value;
  select.innerHTML = state.data.batches.map(batch => `<option value="${batch.id}">${esc(batch.name)} · ${batch.student_count} students</option>`).join("");
  if (state.data.batches.some(batch => String(batch.id) === previous)) select.value = previous;
  if (!state.data.batches.length) select.innerHTML = `<option value="">No batches added</option>`;
}
function timeLabel(time) { const [hour, minute] = time.split(":").map(Number); const meridiem = hour >= 12 ? "PM" : "AM"; return `${hour % 12 || 12}:${String(minute).padStart(2, "0")} ${meridiem}`; }
function renderSchedule() {
  const d = state.data, root = id("schedule-grid");
  root.classList.toggle("list-mode", state.listMode);
  const batchId = Number(id("batch-filter").value);
  const selected = d.batches.find(batch => batch.id === batchId);
  const schedule = d.schedule.filter(item => item.batch_id === batchId);
  if (!selected) { root.innerHTML = `<div class="empty-state"><strong>Add a student batch to get started</strong>Open Resources to add a batch, subjects, faculty, rooms, and slots.</div>`; return; }
  if (!d.schedule.length) { root.innerHTML = `<div class="empty-state"><strong>Your timetable is ready to generate</strong>Add or review the resources, then select “Generate timetable”.</div>`; return; }
  const weekdays = days.filter(day => d.slots.some(slot => slot.day === day));
  const timeKeys = [...new Set(d.slots.map(slot => `${slot.start_time}|${slot.end_time}`))].sort((a, b) => a.localeCompare(b));
  const slotsByKeyDay = new Map(d.slots.map(slot => [`${slot.day}|${slot.start_time}|${slot.end_time}`, slot]));
  const classesBySlot = new Map(schedule.map(item => [item.slot_id, item]));
  let html = `<table class="schedule-table"><thead><tr><th>TIME</th>${weekdays.map(day => `<th>${day.toUpperCase()}</th>`).join("")}</tr></thead><tbody>`;
  for (const key of timeKeys) {
    const [start, end] = key.split("|");
    html += `<tr><td class="time-label">${timeLabel(start)}<small>${timeLabel(end)}</small></td>`;
    for (const day of weekdays) {
      const slot = slotsByKeyDay.get(`${day}|${start}|${end}`); const item = slot && classesBySlot.get(slot.id);
      if (!item) html += `<td>${slot ? `<span class="empty-cell"></span>` : ""}</td>`;
      else {
        const tone = [...item.code].reduce((n, char) => n + char.charCodeAt(0), 0) % 5;
        html += `<td><div class="class-card tone-${tone}" data-edit-class="${item.id}" title="Edit ${esc(item.subject_name)}"><span class="class-room">${esc(item.room_name)}</span><div class="class-title">${esc(item.subject_name)}</div><div class="class-meta">${esc(item.faculty_name)} · ${esc(item.code)}</div></div></td>`;
      }
    }
    html += `</tr>`;
  }
  html += `</tbody></table>`;
  if (state.listMode) {
    html += `<div class="list-classes">${schedule.map(item => `<div class="list-class-row" data-edit-class="${item.id}"><span class="list-time">${esc(item.day)}<br>${timeLabel(item.start_time)}</span><span class="list-class-main"><strong>${esc(item.subject_name)}</strong><small>${esc(item.batch_name)} · ${esc(item.faculty_name)} · ${esc(item.room_name)}</small></span>↗</div>`).join("")}</div>`;
  }
  root.innerHTML = html;
}
function valueFor(row, key) {
  if (key === "sessions_per_week") return `<span class="resource-tag">${esc(row[key])} / week</span>`;
  if (key === "student_count") return `${esc(row[key])} students`;
  if (key === "capacity") return `${esc(row[key])} seats`;
  return esc(row[key]);
}
function renderResources() {
  if (!state.data) return;
  const meta = resourceMeta[state.resource], records = state.data[state.resource] || [];
  id("resource-title").textContent = meta.title;
  id("resource-description").textContent = meta.description;
  document.querySelectorAll("#resource-tabs button").forEach(button => button.classList.toggle("selected", button.dataset.resource === state.resource));
  id("resource-head").innerHTML = `<tr>${meta.columns.map(([, label]) => `<th>${esc(label.toUpperCase())}</th>`).join("")}<th>OPTIONS</th></tr>`;
  const query = state.search.trim().toLowerCase();
  const filtered = records.filter(row => !query || meta.columns.some(([key]) => String(row[key] ?? "").toLowerCase().includes(query)));
  if (!filtered.length) {
    id("resource-body").innerHTML = `<tr><td class="empty-table" colspan="${meta.columns.length + 1}">${records.length ? "No matching resources found." : `No ${esc(state.resource)} added yet. Select “Add resource” to begin.`}</td></tr>`;
  } else {
    id("resource-body").innerHTML = filtered.map(row => `<tr>${meta.columns.map(([key], index) => `<td class="${index === 0 ? "resource-name" : ""}">${valueFor(row, key)}</td>`).join("")}<td><div class="row-actions"><button class="icon-button" data-edit-resource="${row.id}">Edit</button><button class="icon-button delete" data-delete-resource="${row.id}">Delete</button></div></td></tr>`).join("");
  }
  id("resource-footer").textContent = `${filtered.length} of ${records.length} ${meta.singular}${records.length === 1 ? "" : "s"}`;
}
function makeField(field, value, prefix = "resource") {
  const fieldId = `${prefix}-${field.name}`, val = value ?? field.value ?? "";
  let input;
  if (field.type === "faculty" || field.type === "batch") {
    const records = field.type === "faculty" ? state.data.faculty : state.data.batches;
    input = `<select class="form-control" id="${fieldId}" name="${field.name}" required><option value="">Choose ${field.type === "faculty" ? "faculty" : "batch"}</option>${records.map(row => `<option value="${row.id}" ${String(row.id) === String(val) ? "selected" : ""}>${esc(row.name)}</option>`).join("")}</select>`;
  } else if (field.type === "day") {
    input = `<select class="form-control" id="${fieldId}" name="${field.name}" required>${days.map(day => `<option ${day === val ? "selected" : ""}>${day}</option>`).join("")}</select>`;
  } else {
    const type = field.type || "text";
    input = `<input class="form-control" id="${fieldId}" name="${field.name}" type="${type}" value="${esc(val)}" ${field.required ? "required" : ""} ${field.min ? `min="${field.min}"` : ""} ${field.max ? `max="${field.max}"` : ""}>`;
  }
  return `<div class="form-field ${field.wide ? "wide" : ""}"><label for="${fieldId}">${esc(field.label)}</label>${input}</div>`;
}
function openEntityModal(resource, row = null) {
  const meta = resourceMeta[resource], isEdit = Boolean(row);
  const fields = meta.fields.map(field => makeField(field, row?.[field.name])).join("");
  id("modal-root").innerHTML = `<div class="modal-backdrop" data-close-modal><form class="modal" id="entity-form"><div class="modal-header"><h2>${isEdit ? "Edit" : "Add"} ${meta.singular}</h2><button type="button" class="modal-close" data-close-modal aria-label="Close">×</button></div><div class="modal-body">${fields}</div><div class="modal-footer">${isEdit ? `<button type="button" class="button button-danger" data-delete-resource="${row.id}" data-modal-delete="${resource}">Delete</button>` : `<span></span>`}<div class="modal-footer-right"><button type="button" class="button button-quiet" data-close-modal>Cancel</button><button type="submit" class="button button-primary">${isEdit ? "Save changes" : "Add"} ${meta.singular}</button></div></div></form></div>`;
  id("entity-form").addEventListener("submit", async event => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      await api(isEdit ? `/api/${resource}/${row.id}` : `/api/${resource}`, { method: isEdit ? "PUT" : "POST", body: JSON.stringify(payload) });
      id("modal-root").innerHTML = ""; await refresh(); toast(`${meta.singular[0].toUpperCase()}${meta.singular.slice(1)} ${isEdit ? "updated" : "added"}.`, "success");
    } catch (error) { toast(error.message, "error"); }
  });
}
function openClassModal(row) {
  const subject = state.data.subjects.find(item => item.id === row.subject_id);
  const eligibleRooms = state.data.rooms.filter(room => !subject || room.capacity >= subject.student_count);
  id("modal-root").innerHTML = `<div class="modal-backdrop" data-close-modal><form class="modal" id="class-form"><div class="modal-header"><h2>Edit class time or room</h2><button type="button" class="modal-close" data-close-modal aria-label="Close">×</button></div><div class="modal-body"><div class="form-field wide"><label>Class</label><div class="form-control" style="background:#fafbfc">${esc(row.subject_name)} · ${esc(row.batch_name)} · ${esc(row.faculty_name)}</div></div><div class="form-field"><label for="class-slot">Time slot</label><select class="form-control" id="class-slot" name="slot_id">${state.data.slots.map(slot => `<option value="${slot.id}" ${slot.id === row.slot_id ? "selected" : ""}>${esc(slot.day)} · ${timeLabel(slot.start_time)}–${timeLabel(slot.end_time)}</option>`).join("")}</select></div><div class="form-field"><label for="class-room">Classroom</label><select class="form-control" id="class-room" name="room_id">${eligibleRooms.map(room => `<option value="${room.id}" ${room.id === row.room_id ? "selected" : ""}>${esc(room.name)} · ${room.capacity} seats</option>`).join("")}</select></div></div><div class="modal-footer"><button type="button" class="button button-danger" data-delete-class="${row.id}">Remove from timetable</button><div class="modal-footer-right"><button type="button" class="button button-quiet" data-close-modal>Cancel</button><button type="submit" class="button button-primary">Save changes</button></div></div></form></div>`;
  id("class-form").addEventListener("submit", async event => {
    event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    try { await api(`/api/schedule/${row.id}`, { method: "PATCH", body: JSON.stringify(values) }); id("modal-root").innerHTML = ""; await refresh(); toast("Class time and room updated.", "success"); }
    catch (error) { toast(error.message, "error"); }
  });
}
async function deleteResource(resource, resourceId, closeModal = false) {
  const meta = resourceMeta[resource];
  if (!window.confirm(`Delete this ${meta.singular}?`)) return;
  try { await api(`/api/${resource}/${resourceId}`, { method: "DELETE" }); if (closeModal) id("modal-root").innerHTML = ""; await refresh(); toast(`${meta.singular[0].toUpperCase()}${meta.singular.slice(1)} deleted.`, "success"); }
  catch (error) { toast(error.message, "error"); }
}
async function generate(method = "backtracking") {
  const button = id("generate-button"), previous = button.innerHTML;
  button.disabled = true; button.innerHTML = `<span class="sparkle">…</span> Generating`;
  try {
    const result = await api("/api/generate", { method: "POST", body: JSON.stringify({ method }) });
    await refresh();
    const resultBox = id("algorithm-result");
    if (resultBox) { resultBox.classList.remove("hidden"); resultBox.classList.add("visible"); resultBox.innerHTML = `<strong>${result.algorithm === "backtracking" ? "Backtracking + graph coloring" : "Greedy scheduler"}</strong> placed ${result.scheduled_classes} classes across ${result.vertices} graph vertices and ${result.conflict_edges} conflict edges. Search steps: ${result.search_steps} · Runtime: ${result.elapsed_ms} ms.`; }
    toast(`Timetable generated with ${result.algorithm === "backtracking" ? "backtracking" : "greedy"}.`, "success");
  } catch (error) { toast(error.message, "error"); }
  finally { button.disabled = false; button.innerHTML = previous; }
}
document.addEventListener("click", async event => {
  const nav = event.target.closest("[data-view]"); if (nav) return setView(nav.dataset.view);
  const goto = event.target.closest("[data-goto]"); if (goto) return setView(goto.dataset.goto);
  const tab = event.target.closest("[data-resource]"); if (tab) { state.resource = tab.dataset.resource; state.search = ""; id("resource-search").value = ""; return renderResources(); }
  const editClass = event.target.closest("[data-edit-class]"); if (editClass) { const row = state.data.schedule.find(item => item.id === Number(editClass.dataset.editClass)); if (row) openClassModal(row); return; }
  const editResource = event.target.closest("[data-edit-resource]"); if (editResource) { const row = state.data[state.resource].find(item => item.id === Number(editResource.dataset.editResource)); if (row) openEntityModal(state.resource, row); return; }
  const modalDelete = event.target.closest("[data-modal-delete]"); if (modalDelete) { event.preventDefault(); return deleteResource(modalDelete.dataset.modalDelete, Number(modalDelete.dataset.deleteResource), true); }
  const deleteResourceButton = event.target.closest("[data-delete-resource]"); if (deleteResourceButton) return deleteResource(state.resource, Number(deleteResourceButton.dataset.deleteResource));
  const deleteClass = event.target.closest("[data-delete-class]"); if (deleteClass) {
    if (!window.confirm("Remove this class from the timetable?")) return;
    try { await api(`/api/schedule/${deleteClass.dataset.deleteClass}`, { method: "DELETE" }); id("modal-root").innerHTML = ""; await refresh(); toast("Class removed from the timetable.", "success"); } catch (error) { toast(error.message, "error"); }
    return;
  }
  if (event.target.closest("[data-close-modal]") && (event.target === event.target.closest("[data-close-modal]") || event.target.closest(".modal-close"))) id("modal-root").innerHTML = "";
});
id("batch-filter").addEventListener("change", renderSchedule);
id("generate-button").addEventListener("click", () => generate("backtracking"));
id("run-algorithm").addEventListener("click", () => generate(id("algorithm-select").value));
id("export-button").addEventListener("click", () => { if (!state.data.schedule.length) return toast("Generate a timetable before exporting it.", "error"); window.location.href = "/api/export.csv"; });
id("add-resource-button").addEventListener("click", () => openEntityModal(state.resource));
id("resource-search").addEventListener("input", event => { state.search = event.target.value; renderResources(); });
id("list-toggle").addEventListener("click", event => { state.listMode = !state.listMode; event.currentTarget.classList.toggle("selected", state.listMode); event.currentTarget.previousElementSibling.classList.toggle("selected", !state.listMode); renderSchedule(); });
function updateDate() { const now = new Date(); id("today-label").textContent = now.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" }); }
updateDate();
api("/api/data").then(data => { state.data = data; renderAll(); if (location.hash === "#resources") setView("resources"); else if (location.hash === "#algorithms") setView("algorithms"); }).catch(error => { id("schedule-grid").innerHTML = `<div class="empty-state"><strong>Could not connect to the timetable database</strong>${esc(error.message)}. Restart the app and refresh this page.</div>`; });

