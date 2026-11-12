const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const authPage = document.getElementById("auth-page");
const repositoriesPage = document.getElementById("repositories-page");
const authStartButton = document.getElementById("auth-start");
const authCheckButton = document.getElementById("auth-check");
const usernameElement = document.getElementById("username");
const listElement = document.getElementById("repository-list");
const emptyState = document.getElementById("empty-state");
const countElement = document.getElementById("repository-count");
const selectedCountElement = document.getElementById("selected-count");
const deleteButton = document.getElementById("delete-selected");
const selectAllButton = document.getElementById("select-all");
const dialog = document.getElementById("delete-dialog");
const dialogList = document.getElementById("dialog-repositories");
const confirmDeleteButton = document.getElementById("confirm-delete");
const notice = document.getElementById("notice");
const globalError = document.getElementById("global-error");
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");
const themeLabel = document.getElementById("theme-label");

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.dataset.theme = isDark ? "dark" : "light";
  themeToggle.setAttribute("aria-pressed", String(isDark));
  themeIcon.textContent = isDark ? "☀" : "☾";
  themeLabel.textContent = isDark ? "Ativar modo claro" : "Ativar modo escuro";
}

let savedTheme = null;
try {
  savedTheme = localStorage.getItem("theme");
} catch {
  // Continue with the system preference when browser storage is unavailable.
}
const initialTheme = savedTheme === "light" || savedTheme === "dark"
  ? savedTheme
  : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
applyTheme(initialTheme);

themeToggle.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(nextTheme);
  try {
    localStorage.setItem("theme", nextTheme);
  } catch {
    // The theme still applies for this page even if it cannot be saved.
  }
});

async function requestJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.method === "POST") {
    headers.set("Content-Type", "application/json");
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(url, { ...options, headers });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `A solicitação falhou (${response.status}).`);
  }
  return data;
}

function showGlobalError(message) {
  globalError.textContent = message;
  globalError.hidden = false;
}

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("notice-error", isError);
  notice.hidden = false;
}

function updateSelection() {
  const selected = listElement.querySelectorAll('input[type="checkbox"]:checked');
  selectedCountElement.textContent = `${selected.length} selecionado${selected.length === 1 ? "" : "s"}`;
  deleteButton.disabled = selected.length === 0;
  const total = listElement.querySelectorAll('input[type="checkbox"]').length;
  selectAllButton.textContent = total > 0 && selected.length === total
    ? "Desmarcar todos"
    : "Selecionar todos";
}

function addRepositoryRow(repository) {
  const row = document.createElement("tr");
  const checkboxCell = document.createElement("td");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.value = repository.full_name;
  checkbox.setAttribute("aria-label", `Selecionar ${repository.name}`);
  checkbox.addEventListener("change", updateSelection);
  checkboxCell.append(checkbox);

  const nameCell = document.createElement("td");
  const name = document.createElement("span");
  name.className = "repository-name";
  name.textContent = repository.name;
  const fullName = document.createElement("span");
  fullName.className = "repository-full-name";
  fullName.textContent = repository.full_name;
  nameCell.append(name, fullName);

  const descriptionCell = document.createElement("td");
  descriptionCell.className = "description-cell";
  descriptionCell.textContent = repository.description || "Sem descrição";

  const visibilityCell = document.createElement("td");
  const badge = document.createElement("span");
  badge.className = `badge ${repository.private ? "badge-private" : "badge-public"}`;
  badge.textContent = repository.private ? "Privado" : "Público";
  visibilityCell.append(badge);

  row.append(checkboxCell, nameCell, descriptionCell, visibilityCell);
  listElement.append(row);
}

async function loadRepositories() {
  globalError.hidden = true;
  countElement.textContent = "Carregando repositórios…";
  listElement.replaceChildren();
  emptyState.hidden = true;
  try {
    const data = await requestJson("/api/repositories");
    usernameElement.textContent = data.username;
    for (const repository of data.repositories) {
      addRepositoryRow(repository);
    }
    countElement.textContent = `${data.repositories.length} repositório${data.repositories.length === 1 ? "" : "s"}`;
    emptyState.hidden = data.repositories.length > 0;
    updateSelection();
  } catch (error) {
    showGlobalError(error.message);
    countElement.textContent = "Não foi possível carregar os repositórios.";
  }
}

async function checkAuthentication() {
  globalError.hidden = true;
  try {
    const data = await requestJson("/api/auth/status");
    if (data.authenticated) {
      authPage.hidden = true;
      repositoriesPage.hidden = false;
      await loadRepositories();
    } else {
      authPage.hidden = false;
      repositoriesPage.hidden = true;
      if (data.error) {
        showGlobalError(data.error);
      }
    }
  } catch (error) {
    showGlobalError(error.message);
  }
}

authStartButton.addEventListener("click", async () => {
  authStartButton.disabled = true;
  try {
    const data = await requestJson("/api/auth/start", { method: "POST" });
    showNotice(data.message);
    authCheckButton.hidden = false;
  } catch (error) {
    showGlobalError(error.message);
  } finally {
    authStartButton.disabled = false;
  }
});

authCheckButton.addEventListener("click", checkAuthentication);
document.getElementById("reload").addEventListener("click", loadRepositories);

document.getElementById("refresh-permission").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const data = await requestJson("/api/auth/refresh", { method: "POST" });
    showNotice(data.message);
  } catch (error) {
    showGlobalError(error.message);
  } finally {
    button.disabled = false;
  }
});

selectAllButton.addEventListener("click", () => {
  const checkboxes = listElement.querySelectorAll('input[type="checkbox"]');
  const shouldCheck = [...checkboxes].some((checkbox) => !checkbox.checked);
  for (const checkbox of checkboxes) {
    checkbox.checked = shouldCheck;
  }
  updateSelection();
});

deleteButton.addEventListener("click", () => {
  const selected = [...listElement.querySelectorAll('input[type="checkbox"]:checked')];
  dialogList.replaceChildren();
  for (const checkbox of selected) {
    const item = document.createElement("li");
    item.textContent = checkbox.value;
    dialogList.append(item);
  }
  confirmDeleteButton.dataset.repositories = JSON.stringify(selected.map((checkbox) => checkbox.value));
  dialog.showModal();
});

confirmDeleteButton.addEventListener("click", async () => {
  const repositories = JSON.parse(confirmDeleteButton.dataset.repositories || "[]");
  confirmDeleteButton.disabled = true;
  confirmDeleteButton.textContent = "Excluindo…";
  try {
    const result = await requestJson("/api/repositories/delete", {
      method: "POST",
      body: JSON.stringify({ repositories }),
    });
    dialog.close();
    if (result.failures.length > 0) {
      const failures = result.failures.map((failure) => `${failure.repository}: ${failure.error}`).join(" | ");
      showNotice(
        `${result.deleted.length} excluído(s); ${result.failures.length} falha(s): ${failures}`,
        true,
      );
    } else {
      showNotice(`${result.deleted.length} repositório(s) excluído(s).`);
    }
    await loadRepositories();
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    confirmDeleteButton.disabled = false;
    confirmDeleteButton.textContent = "Sim, excluir repositórios";
  }
});

checkAuthentication();
