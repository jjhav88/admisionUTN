/**
 * AdmiTomi frontend modular
 * - Token JWT en localStorage
 * - fetch con Authorization Bearer
 * - Notificaciones, modales y formularios API
 */

const TOKEN_KEY = "admitomi_access_token";

/* ---------- Auth / Token ---------- */

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(extra = {}) {
  const headers = { Accept: "application/json", ...extra };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

/* ---------- Notificaciones ---------- */

function ensureToastHost() {
  let host = document.getElementById("toast-host");
  if (!host) {
    host = document.createElement("div");
    host.id = "toast-host";
    host.className = "toast-host";
    document.body.appendChild(host);
  }
  return host;
}

function debounce(fn, wait = 280) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function bindLiveSearch(form, reloadFn, { delay = 280 } = {}) {
  if (!form || typeof reloadFn !== "function") return;

  const run = () => reloadFn();
  const runDebounced = debounce(run, delay);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });

  form.addEventListener("input", (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.matches('input[type="search"], input[type="text"], input[name="q"]')) {
      runDebounced();
    }
  });

  form.addEventListener("change", (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.matches("select")) {
      run();
    }
  });
}

function notify(message, type = "info") {
  const host = ensureToastHost();
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 250);
  }, 3200);
}

/* ---------- API client ---------- */

async function apiRequest(url, options = {}) {
  const opts = { credentials: "same-origin", ...options };
  const isFormData = opts.body instanceof FormData;
  opts.headers = authHeaders(
    isFormData ? opts.headers || {} : { "Content-Type": "application/json", ...(opts.headers || {}) }
  );

  if (opts.body && !isFormData && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
  }

  const response = await fetch(url, opts);
  if (response.status === 204) return null;

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
          : `Error ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

const api = {
  get: (url) => apiRequest(url),
  post: (url, body) => apiRequest(url, { method: "POST", body }),
  put: (url, body) => apiRequest(url, { method: "PUT", body }),
  del: (url) => apiRequest(url, { method: "DELETE" }),
  upload: (file, kind = null) => {
    const form = new FormData();
    form.append("file", file);
    const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
    return apiRequest(`/api/upload${query}`, { method: "POST", body: form });
  },
};

/* ---------- Validaciones cliente ---------- */

function requiredFields(form, names) {
  for (const name of names) {
    const field = form.elements.namedItem(name);
    if (!field || !String(field.value || "").trim()) {
      notify(`El campo "${name}" es obligatorio`, "error");
      field?.focus();
      return false;
    }
  }
  return true;
}

/* ---------- Login ---------- */

async function handleLoginForm(form) {
  if (!requiredFields(form, ["username", "password"])) return;
  const username = form.username.value.trim();
  const password = form.password.value;

  try {
    const data = await api.post("/api/auth/login/json", { username, password });
    setToken(data.access_token);
    notify("Bienvenido", "ok");
    const me = await api.get("/api/auth/me");
    window.location.href = me.role === "admin" ? "/admin" : "/specialist";
  } catch (err) {
    notify(err.message || "Credenciales inválidas", "error");
    const box = document.getElementById("login-error");
    if (box) {
      box.hidden = false;
      box.textContent = err.message || "Credenciales inválidas";
    }
  }
}

/* ---------- Admin careers (API) ---------- */

async function handleCareerForm(form) {
  if (!requiredFields(form, ["name", "level"])) return;
  const careerId = form.dataset.careerId;
  const payload = {
    name: form.name.value.trim(),
    level: form.level.value,
    description: form.description.value.trim() || null,
  };
  if (form.is_active) payload.is_active = form.is_active.checked;

  try {
    if (careerId) {
      await api.put(`/api/admin/careers/${careerId}`, payload);
      notify("Carrera actualizada", "ok");
    } else {
      await api.post("/api/admin/careers", payload);
      notify("Carrera creada", "ok");
    }
    window.location.href = "/admin/careers";
  } catch (err) {
    notify(err.message, "error");
  }
}

const CAREER_LEVEL_LABELS = {
  licenciatura: "Licenciatura",
  maestria: "Maestría",
  curso_posgrado: "Curso Posgrado",
  preparatoria: "Preparatoria",
};

function careerLevelLabel(level) {
  return CAREER_LEVEL_LABELS[level] || level || "—";
}

function renderCareerCards(careers) {
  if (!careers.length) {
    return `<p class="empty-state" id="careers-empty">Aún no hay carreras. Crea la primera con “Nueva carrera”.</p>`;
  }
  return careers
    .map(
      (c) => `
    <article class="career-card" draggable="true" data-career-id="${c.id}">
      <div class="career-card-handle" title="Arrastrar">⋮⋮</div>
      <div class="career-card-body">
        <strong>${escapeHtml(c.name)}</strong>
        <span class="muted">${escapeHtml(c.description || "Sin descripción")}</span>
        <div class="career-card-meta">
          <span class="badge">${escapeHtml(careerLevelLabel(c.level))}</span>
          <code>${escapeHtml(c.slug)}</code>
          <span class="badge ${c.is_active ? "badge-ok" : "badge-muted"}">
            ${c.is_active ? "Activa" : "Inactiva"}
          </span>
        </div>
      </div>
      <div class="actions">
        <a class="btn btn-secondary btn-sm" href="/admin/careers/${c.id}/info">Información</a>
        <a class="btn btn-ghost btn-sm" href="/admin/careers/${c.id}/edit">Editar</a>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-danger-text"
          data-delete-career="${c.id}"
          data-career-name="${escapeHtml(c.name)}"
        >Eliminar</button>
      </div>
    </article>`
    )
    .join("");
}

async function reloadCareersBoard() {
  const list = document.getElementById("careers-list");
  const form = document.getElementById("career-search-form");
  if (!list) return;

  const params = new URLSearchParams();
  if (form?.q.value.trim()) params.set("q", form.q.value.trim());
  if (form?.level?.value) params.set("level", form.level.value);
  if (form?.is_active.value) params.set("is_active", form.is_active.value);
  const query = params.toString() ? `?${params.toString()}` : "";

  try {
    const careers = await api.get(`/api/admin/careers${query}`);
    list.innerHTML = renderCareerCards(careers);
    initCareerDragAndDrop();
  } catch (err) {
    notify(err.message, "error");
  }
}

async function deleteCareer(careerId, name) {
  const accepted = await confirmDialog({
    title: "Eliminar carrera",
    message: `¿Eliminar la carrera "${name}"? Se eliminarán también su información, permisos y descuentos asociados.`,
    confirmText: "Eliminar",
    cancelText: "Cancelar",
    danger: true,
    eyebrow: "Acción irreversible",
  });
  if (!accepted) return;

  try {
    await api.del(`/api/admin/careers/${careerId}`);
    notify("Carrera eliminada", "ok");
    await reloadCareersBoard();
  } catch (err) {
    notify(err.message, "error");
  }
}

function initCareerDragAndDrop() {
  const list = document.getElementById("careers-list");
  if (!list) return;

  const cards = [...list.querySelectorAll(".career-card")];
  let dragged = null;

  cards.forEach((card) => {
    card.addEventListener("dragstart", () => {
      dragged = card;
      card.classList.add("dragging");
    });

    card.addEventListener("dragend", async () => {
      card.classList.remove("dragging");
      list.querySelectorAll(".career-card").forEach((c) => c.classList.remove("drag-over"));
      dragged = null;
      const ids = [...list.querySelectorAll(".career-card")].map((c) => Number(c.dataset.careerId));
      if (!ids.length) return;
      try {
        await api.put("/api/admin/careers/reorder", { ids });
        notify("Orden actualizado", "ok");
      } catch (err) {
        notify(err.message, "error");
        await reloadCareersBoard();
      }
    });

    card.addEventListener("dragover", (event) => {
      event.preventDefault();
      const target = event.currentTarget;
      if (!dragged || dragged === target) return;
      target.classList.add("drag-over");
      const cardsNow = [...list.querySelectorAll(".career-card")];
      const draggedIndex = cardsNow.indexOf(dragged);
      const targetIndex = cardsNow.indexOf(target);
      if (draggedIndex < targetIndex) {
        target.after(dragged);
      } else {
        target.before(dragged);
      }
    });

    card.addEventListener("dragleave", (event) => {
      event.currentTarget.classList.remove("drag-over");
    });
  });
}

// Compatibilidad con llamadas antiguas
async function reloadCareersTable() {
  await reloadCareersBoard();
}

/* ---------- Categories / Users / Permissions / Discounts ---------- */

async function handleCategoryForm(form) {
  if (!requiredFields(form, ["name", "field_type"])) return;
  const categoryId = form.dataset.categoryId;
  const fieldType = form.field_type.value;
  const isSelect =
    fieldType === "single_select" ||
    fieldType === "multi_select" ||
    fieldType === "select_list";
  const options = [...form.querySelectorAll('input[name="field_options"]')]
    .map((el) => el.value.trim())
    .filter(Boolean);

  if (isSelect && options.length < 2) {
    notify("Agrega al menos 2 opciones para este tipo de selección", "error");
    return;
  }

  const payload = {
    name: form.name.value.trim(),
    description: form.description.value.trim() || null,
    is_editable: form.is_editable ? form.is_editable.checked : true,
    allows_document:
      fieldType === "file"
        ? true
        : form.allows_document
          ? form.allows_document.checked
          : false,
    field_type: fieldType,
    field_options: isSelect ? options : null,
  };

  try {
    if (categoryId) {
      await api.put(`/api/admin/categories/${categoryId}`, payload);
      notify("Categoría actualizada", "ok");
    } else {
      await api.post("/api/admin/categories", payload);
      notify("Categoría creada", "ok");
    }
    window.location.href = "/admin/categories";
  } catch (err) {
    notify(err.message, "error");
  }
}

const CATEGORY_FIELD_LABELS = {
  short_text: "Texto corto",
  long_text: "Texto largo",
  single_select: "Selección única",
  multi_select: "Selección múltiple",
  select_list: "Lista de selección",
  weekday_hours: "Días y horario",
  file: "Archivo",
  item_list: "Lista de elementos",
};

const WEEKDAY_LABELS = {
  lunes: "Lunes",
  martes: "Martes",
  miercoles: "Miércoles",
  jueves: "Jueves",
  viernes: "Viernes",
  sabado: "Sábado",
  domingo: "Domingo",
};

function formatTime12(hhmm) {
  if (!hhmm || !hhmm.includes(":")) return "";
  const [hRaw, mRaw] = hhmm.split(":");
  let h = Number(hRaw);
  const m = Number(mRaw);
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmm;
  const suffix = h >= 12 ? "p.m." : "a.m.";
  const hour = ((h + 11) % 12) + 1;
  return `${hour}:${String(m).padStart(2, "0")} ${suffix}`;
}

function formatScheduleLabel(schedule) {
  if (!schedule) return "";
  const dayFrom = WEEKDAY_LABELS[schedule.day_from] || "";
  const dayTo = WEEKDAY_LABELS[schedule.day_to] || "";
  const timeFrom = formatTime12(schedule.time_from);
  const timeTo = formatTime12(schedule.time_to);
  if (!dayFrom || !dayTo || !timeFrom || !timeTo) return "";
  return `${dayFrom} – ${dayTo}, ${timeFrom} – ${timeTo}`;
}

function renderCategoryCards(categories) {
  if (!categories.length) {
    return `<p class="empty-state" id="categories-empty">Aún no hay categorías. Crea la primera con “Nueva categoría”.</p>`;
  }
  return categories
    .map(
      (c) => `
    <article class="category-card" draggable="true" data-category-id="${c.id}">
      <div class="category-card-handle" title="Arrastrar">⋮⋮</div>
      <div class="category-card-body">
        <strong>${escapeHtml(c.name)}</strong>
        <span class="muted">${escapeHtml(c.description || "Sin descripción")}</span>
        <div class="category-card-meta">
          <span class="badge">${escapeHtml(CATEGORY_FIELD_LABELS[c.field_type] || c.field_type || "Texto largo")}</span>
          <span class="badge ${c.is_editable ? "badge-ok" : "badge-muted"}">
            ${c.is_editable ? "Editable" : "No editable"}
          </span>
          ${
            c.allows_document || c.field_type === "file"
              ? `<span class="badge">Archivo PNG/PDF</span>`
              : ""
          }
        </div>
      </div>
      <div class="actions">
        <a class="btn btn-ghost btn-sm" href="/admin/categories/${c.id}/edit">Editar</a>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-danger-text"
          data-delete-category="${c.id}"
          data-category-name="${escapeHtml(c.name)}"
        >Eliminar</button>
      </div>
    </article>`
    )
    .join("");
}

async function reloadCategoriesBoard() {
  const list = document.getElementById("categories-list");
  const form = document.getElementById("category-search-form");
  if (!list) return;

  const params = new URLSearchParams();
  if (form?.q.value.trim()) params.set("q", form.q.value.trim());
  const query = params.toString() ? `?${params.toString()}` : "";

  try {
    const categories = await api.get(`/api/admin/categories${query}`);
    list.innerHTML = renderCategoryCards(categories);
    initCategoryDragAndDrop();
  } catch (err) {
    notify(err.message, "error");
  }
}

async function deleteCategory(categoryId, categoryName) {
  const accepted = await confirmDialog({
    title: "Eliminar categoría",
    message: `¿Eliminar la categoría “${categoryName}”? Se borrará también su contenido asociado.`,
    confirmText: "Eliminar",
    cancelText: "Cancelar",
    danger: true,
    eyebrow: "Acción irreversible",
  });
  if (!accepted) return;

  try {
    await api.del(`/api/admin/categories/${categoryId}`);
    notify("Categoría eliminada", "ok");
    await reloadCategoriesBoard();
  } catch (err) {
    notify(err.message, "error");
  }
}

function initCategoryDragAndDrop() {
  const list = document.getElementById("categories-list");
  if (!list) return;

  const cards = [...list.querySelectorAll(".category-card")];
  let dragged = null;

  cards.forEach((card) => {
    card.addEventListener("dragstart", () => {
      dragged = card;
      card.classList.add("dragging");
    });

    card.addEventListener("dragend", async () => {
      card.classList.remove("dragging");
      list.querySelectorAll(".category-card").forEach((c) => c.classList.remove("drag-over"));
      dragged = null;
      const ids = [...list.querySelectorAll(".category-card")].map((c) =>
        Number(c.dataset.categoryId)
      );
      if (!ids.length) return;
      try {
        await api.put("/api/admin/categories/reorder", { ids });
        notify("Orden actualizado", "ok");
      } catch (err) {
        notify(err.message, "error");
        await reloadCategoriesBoard();
      }
    });

    card.addEventListener("dragover", (event) => {
      event.preventDefault();
      const target = event.currentTarget;
      if (!dragged || dragged === target) return;
      target.classList.add("drag-over");
      const cardsNow = [...list.querySelectorAll(".category-card")];
      const draggedIndex = cardsNow.indexOf(dragged);
      const targetIndex = cardsNow.indexOf(target);
      if (draggedIndex < targetIndex) {
        target.after(dragged);
      } else {
        target.before(dragged);
      }
    });

    card.addEventListener("dragleave", (event) => {
      event.currentTarget.classList.remove("drag-over");
    });
  });
}

async function handleUserForm(form) {
  const userId = form.user_id.value;
  const isEdit = Boolean(userId);
  if (!requiredFields(form, ["username", "email", "role"])) return;

  const password = (form.password?.value || "").trim();
  const confirmPassword = (form.password_confirm?.value || "").trim();

  if (!isEdit || password || confirmPassword) {
    if (!password) {
      notify("La contraseña es obligatoria", "error");
      return;
    }
    if (password.length < 6) {
      notify("La contraseña debe tener al menos 6 caracteres", "error");
      return;
    }
    if (password !== confirmPassword) {
      notify("La confirmación de contraseña no coincide", "error");
      return;
    }
  }

  const payload = {
    username: form.username.value.trim(),
    email: form.email.value.trim(),
    full_name: form.full_name.value.trim() || null,
    role: form.role.value,
    is_active: form.is_active.checked,
  };
  if (password) payload.password = password;

  const avatarFile = form.avatar?.files?.[0] || null;

  try {
    let saved;
    if (isEdit) {
      saved = await api.put(`/api/admin/users/${userId}`, payload);
      notify("Usuario actualizado", "ok");
    } else {
      saved = await api.post("/api/admin/users", payload);
      notify("Usuario creado", "ok");
    }

    if (avatarFile) {
      const formData = new FormData();
      formData.append("file", avatarFile);
      saved = await apiRequest(`/api/admin/users/${saved.id}/avatar`, {
        method: "POST",
        body: formData,
      });
      notify("Foto de perfil guardada", "ok");
      maybeRefreshHeaderAvatar(saved);
    }

    closeUserModal();
    await reloadUsersTable();
  } catch (err) {
    notify(err.message, "error");
  }
}

function setAvatarPreview(url, initial = "?") {
  const preview = document.getElementById("avatar-preview");
  const fallback = document.getElementById("avatar-fallback");
  if (!preview || !fallback) return;
  if (url) {
    preview.src = url;
    preview.hidden = false;
    fallback.hidden = true;
  } else {
    preview.removeAttribute("src");
    preview.hidden = true;
    fallback.hidden = false;
    fallback.textContent = (initial || "?").charAt(0).toUpperCase();
  }
}

function openUserModal(mode = "create", user = null) {
  const modal = document.getElementById("user-modal");
  const form = document.getElementById("user-form");
  const title = document.getElementById("user-modal-title");
  const hint = document.getElementById("password-hint");
  if (!modal || !form) return;

  form.reset();
  form.user_id.value = "";
  form.is_active.checked = true;
  form.role.value = "specialist";
  form.password.value = "";
  form.password_confirm.value = "";
  form.password.required = mode === "create";
  form.password_confirm.required = mode === "create";
  setAvatarPreview(null, "?");

  if (mode === "edit" && user) {
    title.textContent = "Editar usuario";
    form.user_id.value = user.id;
    form.username.value = user.username;
    form.email.value = user.email;
    form.full_name.value = user.full_name || "";
    form.role.value = user.role;
    form.is_active.checked = user.is_active;
    setAvatarPreview(user.avatar_url, user.full_name || user.username || "?");
    const currentPassword = user.password || "";
    form.password.value = currentPassword;
    form.password_confirm.value = currentPassword;
    if (hint) {
      hint.textContent = currentPassword
        ? "Contraseña actual visible solo para administradores. Puedes modificarla aquí."
        : "Este usuario no tiene contraseña recuperable. Escribe una nueva (mín. 6) para guardarla.";
    }
  } else {
    title.textContent = "Nuevo usuario";
    if (hint) hint.textContent = "Visible solo para administradores. Mínimo 6 caracteres.";
  }
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeUserModal() {
  const modal = document.getElementById("user-modal");
  if (!modal) return;
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function currentUserId() {
  const page = document.getElementById("users-page");
  return page ? Number(page.dataset.currentUserId) : null;
}

function avatarCell(user) {
  if (user.avatar_url) {
    return `<img class="avatar-circle avatar-sm" src="${escapeHtml(user.avatar_url)}" alt="">`;
  }
  const initial = escapeHtml((user.full_name || user.username || "?").charAt(0).toUpperCase());
  return `<span class="avatar-circle avatar-sm avatar-fallback">${initial}</span>`;
}

function renderUsersRows(users) {
  const me = currentUserId();
  if (!users.length) {
    return `<tr><td colspan="7">Sin usuarios que coincidan.</td></tr>`;
  }
  return users
    .map((item) => {
      const deleteBtn =
        item.id === me
          ? ""
          : `<button type="button" class="btn btn-ghost btn-sm btn-danger-text" data-delete-user="${item.id}" data-username="${escapeHtml(item.username)}">Eliminar</button>`;
      return `
        <tr data-user-id="${item.id}">
          <td>${avatarCell(item)}</td>
          <td>${escapeHtml(item.username)}</td>
          <td>${escapeHtml(item.full_name || "—")}</td>
          <td>${escapeHtml(item.email)}</td>
          <td><span class="badge">${escapeHtml(item.role)}</span></td>
          <td>
            <span class="badge ${item.is_active ? "badge-ok" : "badge-muted"}">
              ${item.is_active ? "Activo" : "Inactivo"}
            </span>
          </td>
          <td class="actions">
            <button type="button" class="btn btn-ghost btn-sm" data-edit-user="${item.id}">Editar</button>
            ${deleteBtn}
          </td>
        </tr>`;
    })
    .join("");
}

function maybeRefreshHeaderAvatar(user) {
  const me = currentUserId();
  if (!user?.avatar_url) return;
  // En página de usuarios solo refresca si editas tu propio registro;
  // en perfil siempre eres tú.
  if (me && user.id !== me && document.getElementById("users-page")) return;

  const chip = document.querySelector(".user-chip");
  if (!chip) return;

  let img = chip.querySelector("img.avatar-circle");
  const fallback = chip.querySelector(".avatar-fallback");
  const nameEl = chip.querySelector(".user-chip-link span, .user-chip > span");

  if (img) {
    img.src = user.avatar_url;
  } else {
    img = document.createElement("img");
    img.className = "avatar-circle";
    img.alt = `Foto de ${user.full_name || user.username}`;
    img.src = user.avatar_url;
    const link = chip.querySelector(".user-chip-link");
    if (link) {
      link.insertBefore(img, link.firstChild);
      fallback?.remove();
    } else {
      chip.insertBefore(img, chip.firstChild);
      fallback?.remove();
    }
  }

  if (nameEl && (user.full_name || user.username)) {
    nameEl.textContent = user.full_name || user.username;
  }
}

function setProfileAvatarPreview(url, initial = "?") {
  const preview = document.getElementById("profile-avatar-preview");
  const fallback = document.getElementById("profile-avatar-fallback");
  if (!preview || !fallback) return;
  if (url) {
    preview.src = url;
    preview.hidden = false;
    fallback.hidden = true;
  } else {
    preview.removeAttribute("src");
    preview.hidden = true;
    fallback.hidden = false;
    fallback.textContent = (initial || "?").charAt(0).toUpperCase();
  }
}

async function handleProfileForm(form) {
  if (!requiredFields(form, ["username", "email"])) return;

  const payload = {
    username: form.username.value.trim(),
    email: form.email.value.trim(),
    full_name: form.full_name.value.trim() || null,
  };
  const password = form.password.value;
  if (password) payload.password = password;

  try {
    let saved = await api.put("/api/auth/me", payload);

    const avatarFile = form.avatar?.files?.[0] || null;
    if (avatarFile) {
      const formData = new FormData();
      formData.append("file", avatarFile);
      saved = await apiRequest("/api/auth/me/avatar", {
        method: "POST",
        body: formData,
      });
    }

    notify("Perfil actualizado", "ok");
    maybeRefreshHeaderAvatar(saved);
    form.password.value = "";
    if (form.avatar) form.avatar.value = "";
    if (saved.avatar_url) setProfileAvatarPreview(saved.avatar_url, saved.full_name || saved.username);
  } catch (err) {
    notify(err.message, "error");
  }
}

async function reloadUsersTable() {
  const tbody = document.querySelector("#users-table tbody");
  const form = document.getElementById("user-search-form");
  if (!tbody) return;

  const params = new URLSearchParams();
  if (form?.q.value.trim()) params.set("q", form.q.value.trim());
  if (form?.role.value) params.set("role", form.role.value);
  if (form?.is_active.value) params.set("is_active", form.is_active.value);

  const query = params.toString() ? `?${params.toString()}` : "";
  try {
    const users = await api.get(`/api/admin/users${query}`);
    tbody.innerHTML = renderUsersRows(users);
  } catch (err) {
    notify(err.message, "error");
  }
}

async function editUser(userId) {
  try {
    const user = await api.get(`/api/admin/users/${userId}`);
    openUserModal("edit", user);
  } catch (err) {
    notify(err.message, "error");
  }
}

/* ---------- Confirmación estilizada (reemplaza window.confirm) ---------- */

function confirmDialog({
  title = "¿Continuar?",
  message = "",
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  danger = true,
  eyebrow = "Confirmación",
} = {}) {
  return new Promise((resolve) => {
    const modal = document.getElementById("app-confirm-modal");
    const titleEl = document.getElementById("app-confirm-title");
    const messageEl = document.getElementById("app-confirm-message");
    const eyebrowEl = document.getElementById("app-confirm-eyebrow");
    const okBtn = document.getElementById("app-confirm-ok");
    const cancelBtn = document.getElementById("app-confirm-cancel");

    if (!modal || !okBtn || !cancelBtn) {
      resolve(window.confirm(message || title));
      return;
    }

    titleEl.textContent = title;
    messageEl.textContent = message;
    eyebrowEl.textContent = eyebrow;
    okBtn.textContent = confirmText;
    cancelBtn.textContent = cancelText;
    okBtn.className = danger ? "btn btn-danger" : "btn btn-primary";

    const previouslyFocused = document.activeElement;

    const cleanup = (result) => {
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
      modal.removeEventListener("click", onBackdrop);
      document.removeEventListener("keydown", onKey);
      previouslyFocused?.focus?.();
      resolve(result);
    };

    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onBackdrop = (event) => {
      if (event.target === modal) cleanup(false);
    };
    const onKey = (event) => {
      if (event.key === "Escape") cleanup(false);
      if (event.key === "Enter") cleanup(true);
    };

    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
    modal.addEventListener("click", onBackdrop);
    document.addEventListener("keydown", onKey);

    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    okBtn.focus();
  });
}

async function deleteUser(userId, username) {
  const accepted = await confirmDialog({
    title: "Eliminar usuario",
    message: `¿Eliminar al usuario "${username}"? Esta acción no se puede deshacer.`,
    confirmText: "Eliminar",
    cancelText: "Cancelar",
    danger: true,
    eyebrow: "Acción irreversible",
  });
  if (!accepted) return;

  try {
    await api.del(`/api/admin/users/${userId}`);
    notify("Usuario eliminado", "ok");
    await reloadUsersTable();
  } catch (err) {
    notify(err.message, "error");
  }
}

function previewLocalImage(input, previewId, fallbackId = null) {
  const file = input?.files?.[0];
  if (!file) return;
  const preview = document.getElementById(previewId);
  const fallback = fallbackId ? document.getElementById(fallbackId) : null;
  if (!preview) return;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  if (fallback) fallback.hidden = true;
}

async function handleSettingsForm(form) {
  const payload = {
    header_title: form.header_title?.value?.trim() || null,
    footer_title: form.footer_title?.value?.trim() || null,
    footer_org: form.footer_org?.value?.trim() || null,
    footer_copy: form.footer_copy?.value?.trim() || null,
    contact_phone: form.contact_phone?.value?.trim() || null,
    contact_email: form.contact_email?.value?.trim() || null,
    contact_address: form.contact_address?.value?.trim() || null,
  };

  const headerFile = form.header_logo?.files?.[0] || null;
  const footerFile = form.footer_logo?.files?.[0] || null;

  try {
    await api.put("/api/admin/settings", payload);

    if (headerFile) {
      const data = new FormData();
      data.append("file", headerFile);
      await apiRequest("/api/admin/settings/header-logo", { method: "POST", body: data });
    }
    if (footerFile) {
      const data = new FormData();
      data.append("file", footerFile);
      await apiRequest("/api/admin/settings/footer-logo", { method: "POST", body: data });
    }

    notify("Settings guardados", "ok");
    window.location.reload();
  } catch (err) {
    notify(err.message, "error");
  }
}

function initSettingsForm() {
  const form = document.getElementById("settings-form");
  if (!form) return;

  document.getElementById("header-logo-input")?.addEventListener("change", (e) => {
    previewLocalImage(e.target, "header-logo-preview", "header-logo-fallback");
  });
  document.getElementById("footer-logo-input")?.addEventListener("change", (e) => {
    previewLocalImage(e.target, "footer-logo-preview", "footer-logo-fallback");
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSettingsForm(form);
  });
}

async function handlePermissionForm(form) {
  const userId = Number(form.user_id.value);
  const categoryIds = [...form.querySelectorAll('input[name="category_ids"]:checked')].map((el) =>
    Number(el.value)
  );
  const careerIds = [...form.querySelectorAll('input[name="career_ids"]:checked')].map((el) =>
    Number(el.value)
  );

  if (!userId) {
    notify("Selecciona un especialista", "error");
    return;
  }
  if (!categoryIds.length) {
    notify("Selecciona al menos una categoría", "error");
    return;
  }
  if (!careerIds.length) {
    notify("Selecciona al menos una carrera", "error");
    return;
  }

  try {
    const created = await api.post("/api/admin/permissions/bulk", {
      user_id: userId,
      category_ids: categoryIds,
      career_ids: careerIds,
      can_edit: true,
    });
    const count = Array.isArray(created) ? created.length : categoryIds.length * careerIds.length;
    notify(
      count === 1 ? "Permiso asignado" : `${count} permisos asignados`,
      "ok"
    );
    window.location.reload();
  } catch (err) {
    notify(err.message, "error");
  }
}

function updateCheckboxGroupCount({ listId, counterId, selectAllId, inputName, singular, plural }) {
  const list = document.getElementById(listId);
  const counter = document.getElementById(counterId);
  const selectAll = document.getElementById(selectAllId);
  if (!list || !counter) return;

  const boxes = [...list.querySelectorAll(`input[name="${inputName}"]`)];
  const checked = boxes.filter((box) => box.checked).length;
  counter.textContent = checked === 1 ? `1 ${singular}` : `${checked} ${plural}`;

  if (selectAll) {
    selectAll.checked = boxes.length > 0 && checked === boxes.length;
    selectAll.indeterminate = checked > 0 && checked < boxes.length;
  }
}

function initCheckboxGroup({ listId, selectAllId, inputName, onChange }) {
  const list = document.getElementById(listId);
  const selectAll = document.getElementById(selectAllId);
  if (!list) return;

  selectAll?.addEventListener("change", () => {
    list.querySelectorAll(`input[name="${inputName}"]`).forEach((box) => {
      box.checked = selectAll.checked;
    });
    onChange();
  });

  list.addEventListener("change", (e) => {
    if (e.target?.matches?.(`input[name="${inputName}"]`)) onChange();
  });

  onChange();
}

function readJsonScript(id, fallback = []) {
  const el = document.getElementById(id);
  if (!el) return fallback;
  try {
    return JSON.parse(el.textContent || "null") ?? fallback;
  } catch {
    return fallback;
  }
}

function initPermissionViewer() {
  const userSelect = document.getElementById("perm-view-user");
  const careerSelect = document.getElementById("perm-view-career");
  const tbody = document.getElementById("perm-view-tbody");
  if (!userSelect || !careerSelect || !tbody) return;

  const permissions = readJsonScript("permissions-data", []);
  const categories = readJsonScript("permission-categories-data", []);

  const render = () => {
    const userId = Number(userSelect.value || 0);
    const careerId = Number(careerSelect.value || 0);

    careerSelect.disabled = !userId;
    const careerPlaceholder = careerSelect.querySelector('option[value=""]');
    if (careerPlaceholder) {
      careerPlaceholder.textContent = userId
        ? "— Seleccionar carrera —"
        : "— Primero selecciona un usuario —";
    }

    if (!userId) {
      careerSelect.value = "";
      tbody.innerHTML =
        `<tr><td colspan="2" class="muted">Selecciona un usuario y una carrera para ver los permisos.</td></tr>`;
      return;
    }

    if (!careerId) {
      tbody.innerHTML =
        `<tr><td colspan="2" class="muted">Selecciona una carrera para ver las categorías y su permiso.</td></tr>`;
      return;
    }

    if (!categories.length) {
      tbody.innerHTML = `<tr><td colspan="2" class="muted">No hay categorías registradas.</td></tr>`;
      return;
    }

    const allowed = new Set(
      permissions
        .filter(
          (p) =>
            Number(p.user_id) === userId &&
            Number(p.career_id) === careerId &&
            p.can_edit
        )
        .map((p) => Number(p.category_id))
    );

    tbody.innerHTML = categories
      .map((category) => {
        const canEdit = allowed.has(Number(category.id));
        return `<tr>
          <td>${escapeHtml(category.name)}</td>
          <td>
            <span class="badge ${canEdit ? "badge-ok" : "badge-muted"}">
              ${canEdit ? "Sí" : "No"}
            </span>
          </td>
        </tr>`;
      })
      .join("");
  };

  userSelect.addEventListener("change", () => {
    if (!userSelect.value) careerSelect.value = "";
    render();
  });
  careerSelect.addEventListener("change", render);
  render();
}

function initPermissionCareerCheckboxes() {
  initPermissionViewer();

  const updateCategories = () =>
    updateCheckboxGroupCount({
      listId: "categories-checkbox-list",
      counterId: "categories-selected-count",
      selectAllId: "categories-select-all",
      inputName: "category_ids",
      singular: "seleccionada",
      plural: "seleccionadas",
    });
  const updateCareers = () =>
    updateCheckboxGroupCount({
      listId: "careers-checkbox-list",
      counterId: "careers-selected-count",
      selectAllId: "careers-select-all",
      inputName: "career_ids",
      singular: "seleccionada",
      plural: "seleccionadas",
    });

  initCheckboxGroup({
    listId: "categories-checkbox-list",
    selectAllId: "categories-select-all",
    inputName: "category_ids",
    onChange: updateCategories,
  });
  initCheckboxGroup({
    listId: "careers-checkbox-list",
    selectAllId: "careers-select-all",
    inputName: "career_ids",
    onChange: updateCareers,
  });
}

async function handleDiscountForm(form) {
  if (!requiredFields(form, ["career_id", "title", "percentage", "start_date"])) return;

  const unlimited = Boolean(form.unlimited?.checked);
  const endDate = form.end_date?.value || "";
  if (!unlimited && !endDate) {
    notify("Indica la fecha de fin o activa vigencia ilimitada", "error");
    form.end_date?.focus();
    return;
  }
  if (!unlimited && form.start_date.value && endDate < form.start_date.value) {
    notify("La fecha de fin no puede ser anterior a la de inicio", "error");
    form.end_date?.focus();
    return;
  }

  const discountId = form.dataset.discountId;
  const payload = {
    career_id: Number(form.career_id.value),
    category_id: form.category_id.value ? Number(form.category_id.value) : null,
    title: form.title.value.trim(),
    percentage: Number(form.percentage.value),
    description: form.description.value.trim() || null,
    start_date: form.start_date.value,
    end_date: unlimited ? null : endDate,
  };
  if (form.is_active) payload.is_active = form.is_active.checked;
  else payload.is_active = true;

  try {
    if (discountId) {
      await api.put(`/api/admin/discounts/${discountId}`, payload);
      notify("Descuento actualizado", "ok");
    } else {
      await api.post("/api/admin/discounts", payload);
      notify("Descuento creado", "ok");
    }
    window.location.href = "/admin/discounts";
  } catch (err) {
    notify(err.message, "error");
  }
}

function initDiscountValiditySwitch() {
  const unlimited = document.getElementById("discount-unlimited");
  const endInput = document.getElementById("discount-end-date");
  const startInput = document.querySelector('#discount-form input[name="start_date"]');
  if (!unlimited || !endInput) return;

  if (startInput && !startInput.value) {
    startInput.value = new Date().toISOString().slice(0, 10);
  }

  const sync = () => {
    const isUnlimited = unlimited.checked;
    endInput.disabled = isUnlimited;
    endInput.required = !isUnlimited;
    if (isUnlimited) endInput.value = "";
  };

  unlimited.addEventListener("change", sync);
  sync();
}

function renderDiscountRows(discounts) {
  if (!discounts.length) {
    return `<tr id="discounts-empty-row"><td colspan="8">Aún no hay descuentos. Crea el primero con “Nuevo descuento”.</td></tr>`;
  }
  return discounts
    .map(
      (d) => `
    <tr data-discount-id="${d.id}">
      <td>${escapeHtml(d.title)}</td>
      <td>${escapeHtml(d.career_name || "—")}</td>
      <td>${escapeHtml(d.category_name || "General")}</td>
      <td>${escapeHtml(String(d.percentage))}%</td>
      <td>${escapeHtml(d.start_date || "—")}</td>
      <td>${escapeHtml(d.end_date || "Ilimitado")}</td>
      <td>
        <span class="badge ${d.is_active ? "badge-ok" : "badge-muted"}">
          ${d.is_active ? "Activo" : "Inactivo"}
        </span>
      </td>
      <td class="actions">
        <a class="btn btn-ghost btn-sm" href="/admin/discounts/${d.id}/edit">Editar</a>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-danger-text"
          data-delete-discount="${d.id}"
          data-discount-title="${escapeHtml(d.title)}"
        >Eliminar</button>
      </td>
    </tr>`
    )
    .join("");
}

async function reloadDiscountsTable() {
  const tbody = document.querySelector("#discounts-table tbody");
  const form = document.getElementById("discount-search-form");
  if (!tbody) return;

  const params = new URLSearchParams();
  if (form?.q.value.trim()) params.set("q", form.q.value.trim());
  if (form?.is_active.value) params.set("is_active", form.is_active.value);
  const query = params.toString() ? `?${params.toString()}` : "";

  try {
    const discounts = await api.get(`/api/admin/discounts${query}`);
    tbody.innerHTML = renderDiscountRows(discounts);
  } catch (err) {
    notify(err.message, "error");
  }
}

async function deleteDiscount(discountId, title) {
  const accepted = await confirmDialog({
    title: "Eliminar descuento",
    message: `¿Eliminar el descuento “${title}”?`,
    confirmText: "Eliminar",
    cancelText: "Cancelar",
    danger: true,
    eyebrow: "Acción irreversible",
  });
  if (!accepted) return;

  try {
    await api.del(`/api/admin/discounts/${discountId}`);
    notify("Descuento eliminado", "ok");
    await reloadDiscountsTable();
  } catch (err) {
    notify(err.message, "error");
  }
}

/* ---------- Specialist editor (Quill + upload) ---------- */

const QUILL_TOOLBAR = [
  [{ header: [1, 2, 3, false] }],
  ["bold", "italic", "underline"],
  [{ list: "ordered" }, { list: "bullet" }],
  ["link", "image"],
  ["clean"],
];

function createQuillEditor(mount, initialHtml = "") {
  if (!mount || typeof Quill === "undefined") return null;
  const quill = new Quill(mount, {
    theme: "snow",
    placeholder: mount.dataset.placeholder || "Escribe el contenido de la categoría...",
    modules: { toolbar: QUILL_TOOLBAR },
  });
  if (initialHtml && !isEmptyRichText(initialHtml)) quill.root.innerHTML = initialHtml;
  return quill;
}

function isEmptyRichText(html) {
  if (!html) return true;
  const text = String(html)
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  return !text;
}

function stripHtmlToText(value) {
  if (!value) return "";
  const tmp = document.createElement("div");
  tmp.innerHTML = String(value);
  return (tmp.textContent || tmp.innerText || "").replace(/\s+/g, " ").trim();
}

function initQuillEditor() {
  const mount = document.getElementById("quill-editor");
  const initial = document.getElementById("initial-content");
  return createQuillEditor(mount, initial?.value || "");
}

async function handleInfoEditForm(form, quill) {
  const careerId = form.dataset.careerId;
  const categoryId = form.dataset.categoryId;
  const fieldType = form.dataset.fieldType || "long_text";
  const payload = buildInfoPayload(form, fieldType, quill);

  try {
    await api.put(`/api/specialist/careers/${careerId}/info/${categoryId}`, payload);
    notify("Contenido guardado", "ok");
    window.location.href = `/specialist/careers/${careerId}`;
  } catch (err) {
    notify(err.message, "error");
  }
}

function renderDocumentPreviewIn(preview, url, name, onRemove) {
  if (!preview) return;
  if (!url) {
    preview.hidden = true;
    preview.innerHTML = "";
    return;
  }

  const isPng = url.toLowerCase().endsWith(".png");
  preview.hidden = false;
  preview.innerHTML = isPng
    ? `<img src="${escapeHtml(url)}" alt="${escapeHtml(name || "Documento")}" class="document-preview-image">
       <button type="button" class="btn btn-ghost btn-sm btn-danger-text document-remove">Quitar documento</button>`
    : `<a class="btn btn-secondary btn-sm" href="${escapeHtml(url)}" target="_blank" rel="noopener">
         Ver ${escapeHtml(name || "documento PDF")}
       </a>
       <button type="button" class="btn btn-ghost btn-sm btn-danger-text document-remove">Quitar documento</button>`;

  preview.querySelector(".document-remove")?.addEventListener("click", onRemove);
}

function renderDocumentPreview(url, name) {
  const preview = document.getElementById("document-preview");
  const form = document.getElementById("info-edit-form");
  renderDocumentPreviewIn(preview, url, name, () => {
    if (form) {
      form.dataset.documentUrl = "";
      form.dataset.documentName = "";
    }
    const input = document.getElementById("document-upload");
    if (input) input.value = "";
    renderDocumentPreview("", "");
  });
}

function clearCategoryDocument() {
  const form = document.getElementById("info-edit-form");
  if (!form) return;
  form.dataset.documentUrl = "";
  form.dataset.documentName = "";
  const input = document.getElementById("document-upload");
  if (input) input.value = "";
  renderDocumentPreview("", "");
}

async function handleDocumentUploadInput(input, block = null) {
  const file = input.files?.[0];
  if (!file) return;
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (!["png", "pdf"].includes(ext)) {
    notify("Solo se permiten archivos .png o .pdf", "error");
    input.value = "";
    return;
  }

  const target =
    block || input.closest("[data-info-block]") || document.getElementById("info-edit-form");

  try {
    const result = await api.upload(file, "document");
    if (target) {
      target.dataset.documentUrl = result.url;
      target.dataset.documentName = result.filename || file.name;
    }
    const preview =
      target?.querySelector?.(".document-preview") || document.getElementById("document-preview");
    renderDocumentPreviewIn(preview, result.url, result.filename || file.name, () => {
      if (target) {
        target.dataset.documentUrl = "";
        target.dataset.documentName = "";
      }
      input.value = "";
      renderDocumentPreviewIn(preview, "", "", () => {});
    });
    notify("Documento cargado. Guarda para confirmar.", "ok");
  } catch (err) {
    notify(err.message, "error");
    input.value = "";
  }
}

function getItemListValues(root) {
  if (!root) return [];
  return [...root.querySelectorAll("[data-item-value]")]
    .map((el) => stripHtmlToText(el.textContent || ""))
    .filter(Boolean);
}

function syncItemListEmpty(container) {
  if (!container) return;
  const empty = container.querySelector(".item-list-empty");
  if (!empty) return;
  empty.hidden = getItemListValues(container).length > 0;
}

function addItemListRow(container, value) {
  const list = container.querySelector(".item-list-items");
  if (!list) return;
  const text = stripHtmlToText(value);
  if (!text) return;

  const existing = getItemListValues(container).map((item) => item.toLowerCase());
  if (existing.includes(text.toLowerCase())) {
    notify("Ese elemento ya está en la lista", "error");
    return false;
  }

  const row = document.createElement("li");
  row.className = "item-list-row";
  row.innerHTML = `
    <span data-item-value>${escapeHtml(text)}</span>
    <button type="button" class="btn btn-ghost btn-sm btn-danger-text" data-remove-item>Quitar</button>
  `;
  list.appendChild(row);
  syncItemListEmpty(container);
  return true;
}

function initItemListField(root) {
  const container = root?.matches?.("[data-item-list]")
    ? root
    : root?.querySelector?.("[data-item-list]");
  if (!container || container.dataset.itemListReady === "1") return;
  container.dataset.itemListReady = "1";

  const input = container.querySelector(".field-item-input");
  const addBtn = container.querySelector("[data-add-item]");

  const addCurrent = () => {
    if (!input) return;
    if (addItemListRow(container, input.value)) {
      input.value = "";
      input.focus();
    }
  };

  addBtn?.addEventListener("click", addCurrent);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addCurrent();
    }
  });

  container.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-remove-item]");
    if (!btn) return;
    btn.closest(".item-list-row")?.remove();
    syncItemListEmpty(container);
  });

  syncItemListEmpty(container);
}

function initInfoBulkForm() {
  const form = document.getElementById("info-bulk-form");
  if (!form) return null;

  const quills = new Map();
  form.querySelectorAll("[data-info-block]").forEach((block) => {
    const categoryId = Number(block.dataset.categoryId);
    const fieldType = block.dataset.fieldType || "long_text";
    if (fieldType === "long_text") {
      const mount = block.querySelector(".quill-editor");
      const initial = block.querySelector(".initial-content");
      const quill = createQuillEditor(mount, initial?.value || "");
      if (quill) quills.set(categoryId, quill);
    }
    if (fieldType === "item_list") {
      initItemListField(block);
    }

    const upload = block.querySelector(".document-upload");
    upload?.addEventListener("change", () => handleDocumentUploadInput(upload, block));

    block.querySelector(".document-remove")?.addEventListener("click", () => {
      block.dataset.documentUrl = "";
      block.dataset.documentName = "";
      if (upload) upload.value = "";
      renderDocumentPreviewIn(block.querySelector(".document-preview"), "", "", () => {});
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const careerId = form.dataset.careerId;
    const blocks = [...form.querySelectorAll("[data-info-block]")];
    if (!blocks.length) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
      for (const block of blocks) {
        const categoryId = Number(block.dataset.categoryId);
        const fieldType = block.dataset.fieldType || "long_text";
        const payload = buildInfoPayload(block, fieldType, quills.get(categoryId));
        await api.put(`/api/specialist/careers/${careerId}/info/${categoryId}`, payload);
      }
      notify("Información guardada", "ok");
      window.location.href = "/admin/careers";
    } catch (err) {
      notify(err.message, "error");
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });

  return quills;
}

function buildInfoPayload(block, fieldType, quill) {
  const payload = { content: null, extra_data: {} };
  const existingDoc = {
    document_url: block.dataset.documentUrl || null,
    document_name: block.dataset.documentName || null,
  };

  if (fieldType === "short_text") {
    payload.content = stripHtmlToText(block.querySelector(".field-short-text")?.value || "");
  } else if (fieldType === "single_select") {
    const selected = stripHtmlToText(block.querySelector(".field-single-select:checked")?.value || "");
    payload.content = selected;
    payload.extra_data.selected = selected || null;
  } else if (fieldType === "select_list") {
    const selected = stripHtmlToText(block.querySelector(".field-select-list")?.value || "");
    payload.content = selected;
    payload.extra_data.selected = selected || null;
  } else if (fieldType === "multi_select") {
    const selected = [...block.querySelectorAll(".field-multi-select:checked")]
      .map((el) => stripHtmlToText(el.value))
      .filter(Boolean);
    payload.content = selected.join(", ");
    payload.extra_data.selected = selected;
  } else if (fieldType === "weekday_hours") {
    const schedule = {
      day_from: block.querySelector(".field-day-from")?.value || "",
      day_to: block.querySelector(".field-day-to")?.value || "",
      time_from: block.querySelector(".field-time-from")?.value || "",
      time_to: block.querySelector(".field-time-to")?.value || "",
    };
    const label = formatScheduleLabel(schedule);
    payload.content = label;
    payload.extra_data.schedule = label ? schedule : null;
  } else if (fieldType === "file") {
    const url = block.dataset.documentUrl || "";
    const name = block.dataset.documentName || "";
    payload.content = name || "";
    payload.extra_data.document_url = url || null;
    payload.extra_data.document_name = name || null;
  } else if (fieldType === "item_list") {
    const items = getItemListValues(block);
    payload.content = items.join("\n");
    payload.extra_data.items = items;
  } else {
    const html = quill ? quill.root.innerHTML : "";
    payload.content = isEmptyRichText(html) ? "" : html;
  }

  if (block.dataset.allowsDocument === "true" && fieldType !== "file") {
    if (existingDoc.document_url) {
      payload.extra_data.document_url = existingDoc.document_url;
      payload.extra_data.document_name = existingDoc.document_name;
    } else {
      payload.extra_data.document_url = null;
      payload.extra_data.document_name = null;
    }
  }

  if (!Object.keys(payload.extra_data).length) {
    payload.extra_data = null;
  }
  return payload;
}

function initCategoryFieldTypeUI() {
  const typeSelect = document.getElementById("category-field-type");
  const optionsBlock = document.getElementById("category-options-block");
  const optionsList = document.getElementById("category-options-list");
  const addBtn = document.getElementById("add-category-option");
  const documentExtra = document.getElementById("document-extra-block");
  const fileHint = document.getElementById("file-type-hint");
  const itemListHint = document.getElementById("item-list-type-hint");
  if (!typeSelect || !optionsBlock || !optionsList) return;

  const sync = () => {
    const needsOptions =
      typeSelect.value === "single_select" ||
      typeSelect.value === "multi_select" ||
      typeSelect.value === "select_list";
    const isFile = typeSelect.value === "file";
    const isItemList = typeSelect.value === "item_list";
    optionsBlock.hidden = !needsOptions;
    if (documentExtra) documentExtra.hidden = isFile;
    if (fileHint) fileHint.hidden = !isFile;
    if (itemListHint) itemListHint.hidden = !isItemList;
  };

  const addOptionRow = (value = "") => {
    const row = document.createElement("div");
    row.className = "option-row";
    row.innerHTML = `
      <input type="text" name="field_options" value="${escapeHtml(value)}" placeholder="Opción">
      <button type="button" class="btn btn-ghost btn-sm btn-danger-text" data-remove-option>Quitar</button>
    `;
    optionsList.appendChild(row);
  };

  addBtn?.addEventListener("click", () => addOptionRow());
  optionsList.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-remove-option]");
    if (!btn) return;
    const rows = optionsList.querySelectorAll(".option-row");
    if (rows.length <= 2) {
      notify("Debes conservar al menos 2 opciones", "error");
      return;
    }
    btn.closest(".option-row")?.remove();
  });

  typeSelect.addEventListener("change", sync);
  sync();
}

async function handleFileUploadInput(input, quill) {
  const file = input.files?.[0];
  if (!file) return;
  try {
    const result = await api.upload(file);
    if (quill) {
      const range = quill.getSelection(true) || { index: quill.getLength() };
      if (file.type.startsWith("image/")) {
        quill.insertEmbed(range.index, "image", result.url, "user");
      } else {
        quill.insertText(range.index, `${file.name}: ${result.url}\n`, "user");
      }
    } else {
      const area = document.querySelector("textarea[name='content']");
      if (area) area.value = `${area.value}\n${result.url}`;
    }
    notify("Archivo subido", "ok");
  } catch (err) {
    notify(err.message, "error");
  } finally {
    input.value = "";
  }
}

/* ---------- Utils ---------- */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function initTabs() {
  document.querySelectorAll("[data-tabs]").forEach((root) => {
    const buttons = root.querySelectorAll("[data-tab]");
    const panels = root.querySelectorAll("[data-tab-panel]");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.tab;
        buttons.forEach((b) => b.classList.toggle("active", b === btn));
        panels.forEach((p) => p.classList.toggle("active", p.dataset.tabPanel === id));
      });
    });
  });
}

function initModals() {
  document.querySelectorAll("[data-open-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.openModal === "user-modal") {
        openUserModal("create");
        return;
      }
      const modal = document.getElementById(btn.dataset.openModal);
      modal?.classList.add("open");
    });
  });
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal");
      if (modal?.id === "user-modal") closeUserModal();
      else modal?.classList.remove("open");
    });
  });
}

/* ---------- Boot ---------- */

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initModals();

  // Confirmaciones declarativas: <button data-confirm="mensaje">...</button>
  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", async (event) => {
      event.preventDefault();
      const accepted = await confirmDialog({
        title: el.dataset.confirmTitle || "¿Continuar?",
        message: el.dataset.confirm,
        confirmText: el.dataset.confirmOk || "Confirmar",
        cancelText: el.dataset.confirmCancel || "Cancelar",
        danger: el.dataset.confirmDanger !== "false",
      });
      if (!accepted) return;

      const href = el.getAttribute("href");
      if (href) {
        window.location.href = href;
        return;
      }
      if (el.dataset.confirmAction === "submit") {
        el.closest("form")?.requestSubmit();
      }
    });
  });

  const logoutLink = document.querySelector('a[href="/logout"]');
  logoutLink?.addEventListener("click", () => clearToken());

  const loginForm = document.getElementById("login-form");
  loginForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleLoginForm(loginForm);
  });

  const careerForm = document.getElementById("career-form");
  careerForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleCareerForm(careerForm);
  });

  bindLiveSearch(document.getElementById("career-search-form"), reloadCareersBoard);

  document.getElementById("careers-list")?.addEventListener("click", (e) => {
    const deleteBtn = e.target.closest("[data-delete-career]");
    if (deleteBtn) {
      deleteCareer(Number(deleteBtn.dataset.deleteCareer), deleteBtn.dataset.careerName || "");
    }
  });

  if (document.getElementById("careers-list")) {
    initCareerDragAndDrop();
  }

  const categoryForm = document.getElementById("category-form");
  categoryForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleCategoryForm(categoryForm);
  });

  const allowsDocument = document.getElementById("allows-document");
  const documentHint = document.getElementById("document-hint");
  allowsDocument?.addEventListener("change", () => {
    if (documentHint) documentHint.hidden = !allowsDocument.checked;
  });
  initCategoryFieldTypeUI();

  bindLiveSearch(document.getElementById("category-search-form"), reloadCategoriesBoard);

  document.getElementById("categories-list")?.addEventListener("click", (e) => {
    const deleteBtn = e.target.closest("[data-delete-category]");
    if (deleteBtn) {
      deleteCategory(
        Number(deleteBtn.dataset.deleteCategory),
        deleteBtn.dataset.categoryName || ""
      );
    }
  });

  if (document.getElementById("categories-list")) {
    initCategoryDragAndDrop();
  }

  const userForm = document.getElementById("user-form");
  userForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleUserForm(userForm);
  });

  const avatarInput = document.getElementById("avatar-input");
  avatarInput?.addEventListener("change", () => {
    const file = avatarInput.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setAvatarPreview(url, file.name);
  });

  const profileForm = document.getElementById("profile-form");
  profileForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleProfileForm(profileForm);
  });

  const profileAvatarInput = document.getElementById("profile-avatar-input");
  profileAvatarInput?.addEventListener("change", () => {
    const file = profileAvatarInput.files?.[0];
    if (!file) return;
    setProfileAvatarPreview(URL.createObjectURL(file), file.name);
  });

  bindLiveSearch(document.getElementById("user-search-form"), reloadUsersTable);

  document.getElementById("users-table")?.addEventListener("click", (e) => {
    const editBtn = e.target.closest("[data-edit-user]");
    if (editBtn) {
      editUser(Number(editBtn.dataset.editUser));
      return;
    }
    const deleteBtn = e.target.closest("[data-delete-user]");
    if (deleteBtn) {
      deleteUser(Number(deleteBtn.dataset.deleteUser), deleteBtn.dataset.username || "");
    }
  });

  const permissionForm = document.getElementById("permission-form");
  permissionForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handlePermissionForm(permissionForm);
  });
  initPermissionCareerCheckboxes();
  initSettingsForm();

  const discountForm = document.getElementById("discount-form");
  discountForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleDiscountForm(discountForm);
  });
  initDiscountValiditySwitch();

  bindLiveSearch(document.getElementById("discount-search-form"), reloadDiscountsTable);

  document.querySelector("#discounts-table")?.addEventListener("click", (e) => {
    const deleteBtn = e.target.closest("[data-delete-discount]");
    if (deleteBtn) {
      deleteDiscount(
        Number(deleteBtn.dataset.deleteDiscount),
        deleteBtn.dataset.discountTitle || ""
      );
    }
  });

  const quill = initQuillEditor();
  const infoForm = document.getElementById("info-edit-form");
  if (infoForm?.dataset.fieldType === "item_list") {
    initItemListField(infoForm);
  }
  infoForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleInfoEditForm(infoForm, quill);
  });

  const uploadInput = document.getElementById("file-upload");
  uploadInput?.addEventListener("change", () => handleFileUploadInput(uploadInput, quill));

  const documentUpload = document.getElementById("document-upload");
  documentUpload?.addEventListener("change", () => handleDocumentUploadInput(documentUpload));
  document.getElementById("document-remove")?.addEventListener("click", clearCategoryDocument);

  initInfoBulkForm();

  if (document.getElementById("careers-list") && getToken()) {
    reloadCareersBoard();
  }
});

window.AdmiTomi = {
  api,
  getToken,
  setToken,
  clearToken,
  notify,
  confirmDialog,
  reloadCareersTable,
  reloadCareersBoard,
  reloadUsersTable,
};
