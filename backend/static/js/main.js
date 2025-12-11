"use strict";
const STATE_STORAGE_KEY = "alliance_ann_states";
const PRESETS_STORAGE_KEY = "alliance_filter_presets";
const RECENT_STORAGE_KEY = "alliance_recent_viewed";
function loadStates() {
    try {
        const raw = localStorage.getItem(STATE_STORAGE_KEY);
        if (!raw)
            return {};
        return JSON.parse(raw);
    }
    catch {
        return {};
    }
}
function saveStates(states) {
    try {
        localStorage.setItem(STATE_STORAGE_KEY, JSON.stringify(states));
    }
    catch {
    }
}
function loadPresets() {
    try {
        const raw = localStorage.getItem(PRESETS_STORAGE_KEY);
        if (!raw)
            return [];
        return JSON.parse(raw);
    }
    catch {
        return [];
    }
}
function savePresets(presets) {
    try {
        localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
    }
    catch {
    }
}
function loadRecentlyViewed() {
    try {
        const raw = localStorage.getItem(RECENT_STORAGE_KEY);
        if (!raw)
            return [];
        return JSON.parse(raw);
    }
    catch {
        return [];
    }
}
function saveRecentlyViewed(recent) {
    try {
        localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(recent));
    }
    catch {
    }
}
function addRecentlyViewed(id, title, school) {
    const recent = loadRecentlyViewed();
    const filtered = recent.filter((r) => r.id !== id);
    filtered.unshift({ id, title, school, viewedAt: new Date().toISOString() });
    const trimmed = filtered.slice(0, 10);
    saveRecentlyViewed(trimmed);
}
function parseDate(value) {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
}
function matchesFilter(row, activeFilter, schoolFilter, dateFrom, dateTo) {
    if (activeFilter === "highlight" && row.dataset.highlight !== "true") {
        return false;
    }
    if (activeFilter === "open" && row.dataset.status?.toLowerCase() !== "open") {
        return false;
    }
    const categoryVal = row.dataset.category?.toLowerCase() || "";
    if (activeFilter === "pnrr" && !categoryVal.includes("pnrr")) {
        return false;
    }
    if (activeFilter === "pon" && !categoryVal.includes("pon")) {
        return false;
    }
    if (schoolFilter && row.dataset.schoolId !== schoolFilter) {
        return false;
    }
    if (dateFrom || dateTo) {
        const rowDate = parseDate(row.dataset.date || "");
        if (rowDate === 0)
            return false;
        if (dateFrom) {
            const fromTimestamp = parseDate(dateFrom);
            if (rowDate < fromTimestamp)
                return false;
        }
        if (dateTo) {
            const toTimestamp = parseDate(dateTo);
            if (rowDate > toTimestamp + 86400000)
                return false;
        }
    }
    return true;
}
function matchesSearch(row, term) {
    if (!term)
        return true;
    const haystack = row.dataset.search?.toLowerCase() || "";
    return haystack.includes(term);
}
function updateVisibility(rows, activeFilter, schoolFilter, searchTerm, resultCounter, dateFrom = "", dateTo = "") {
    let visible = 0;
    rows.forEach((row) => {
        const show = matchesFilter(row, activeFilter, schoolFilter, dateFrom, dateTo) && matchesSearch(row, searchTerm);
        row.style.display = show ? "table-row" : "none";
        if (show)
            visible += 1;
    });
    resultCounter.textContent = `${visible} record`;
}
function sortRows(key, rows, tbody, headers, currentSort, activeFilter, schoolFilter, searchTerm, resultCounter, dateFrom = "", dateTo = "") {
    const direction = currentSort.key === key && currentSort.direction === "asc" ? "desc" : "asc";
    const newSort = { key, direction };
    const multiplier = direction === "asc" ? 1 : -1;
    rows.sort((a, b) => {
        const aVal = a.dataset[key] || "";
        const bVal = b.dataset[key] || "";
        if (key === "date") {
            return (parseDate(aVal) - parseDate(bVal)) * multiplier;
        }
        return aVal.toLowerCase().localeCompare(bVal.toLowerCase()) * multiplier;
    });
    rows.forEach((row) => tbody.appendChild(row));
    headers.forEach((h) => {
        const sortKey = h.dataset.sort;
        h.classList.toggle("active", sortKey === key);
    });
    updateVisibility(rows, activeFilter, schoolFilter, searchTerm, resultCounter, dateFrom, dateTo);
    return newSort;
}
function initDashboard() {
    const table = document.getElementById("annTable");
    if (!table)
        return;
    const tbody = table.querySelector("tbody");
    if (!tbody)
        return;
    const headers = table.querySelectorAll("th[data-sort]");
    const searchInput = document.getElementById("searchInput");
    const schoolSelect = document.getElementById("schoolFilter");
    const resultCounter = document.getElementById("resultsCount");
    const chipButtons = Array.from(document.querySelectorAll(".chip"));
    const personalStates = loadStates();
    if (!searchInput || !resultCounter)
        return;
    let rows = Array.from(tbody.querySelectorAll("tr"));
    let activeFilter = "none";
    let schoolFilter = "";
    let currentSort = { key: "date", direction: "desc" };
    const dateFromInput = document.getElementById("dateFrom");
    const dateToInput = document.getElementById("dateTo");
    const clearDatesBtn = document.getElementById("clearDatesBtn");
    let dateFrom = "";
    let dateTo = "";
    const savePresetBtn = document.getElementById("savePresetBtn");
    const presetsList = document.getElementById("presetsList");
    const recentlyViewedList = document.getElementById("recentlyViewedList");
    const clearRecentBtn = document.getElementById("clearRecentBtn");
    const applyState = (row, newState) => {
        const annId = row.dataset.id || "";
        personalStates[annId] = newState;
        saveStates(personalStates);
        const pill = row.querySelector(".state-pill");
        const select = row.querySelector(".state-select");
        if (select) {
            select.value = newState;
        }
        if (pill) {
            if (newState === "none") {
                pill.textContent = "";
                pill.style.display = "none";
            }
            else {
                const labels = {
                    none: "",
                    read: "Letto",
                    applied: "Candidatura inviata",
                    skip: "Non rilevante",
                };
                pill.textContent = labels[newState];
                pill.style.display = "inline-block";
            }
        }
    };
    const renderPresets = () => {
        if (!presetsList)
            return;
        const presets = loadPresets();
        if (presets.length === 0) {
            presetsList.innerHTML = '<p class="empty-message">Nessun filtro salvato. Configura i filtri e clicca "Salva filtri".</p>';
            return;
        }
        presetsList.innerHTML = presets.map((preset) => `
      <div class="preset-item" data-preset-id="${preset.id}">
        <div class="preset-info">
          <strong class="preset-name">${preset.name}</strong>
          <span class="preset-details">${formatPresetDetails(preset)}</span>
        </div>
        <div class="preset-actions">
          <button class="action-btn small apply-preset" data-preset-id="${preset.id}" title="Applica filtro">
            ✓ Applica
          </button>
          <button class="action-btn small delete-preset" data-preset-id="${preset.id}" title="Elimina">
            ✕
          </button>
        </div>
      </div>
    `).join("");
        presetsList.querySelectorAll(".apply-preset").forEach((btn) => {
            btn.addEventListener("click", () => {
                const presetId = btn.dataset.presetId;
                if (presetId)
                    applyPreset(presetId);
            });
        });
        presetsList.querySelectorAll(".delete-preset").forEach((btn) => {
            btn.addEventListener("click", () => {
                const presetId = btn.dataset.presetId;
                if (presetId)
                    deletePreset(presetId);
            });
        });
    };
    const formatPresetDetails = (preset) => {
        const parts = [];
        if (preset.searchTerm)
            parts.push(`"${preset.searchTerm}"`);
        if (preset.schoolFilter)
            parts.push("Scuola");
        if (preset.activeFilter !== "none")
            parts.push(preset.activeFilter);
        if (preset.dateFrom || preset.dateTo)
            parts.push("Date");
        return parts.join(" · ") || "Nessun filtro";
    };
    const applyPreset = (presetId) => {
        const presets = loadPresets();
        const preset = presets.find((p) => p.id === presetId);
        if (!preset)
            return;
        if (searchInput)
            searchInput.value = preset.searchTerm;
        if (schoolSelect)
            schoolSelect.value = preset.schoolFilter;
        if (dateFromInput)
            dateFromInput.value = preset.dateFrom;
        if (dateToInput)
            dateToInput.value = preset.dateTo;
        dateFrom = preset.dateFrom;
        dateTo = preset.dateTo;
        schoolFilter = preset.schoolFilter;
        activeFilter = preset.activeFilter;
        chipButtons.forEach((chip) => {
            chip.classList.toggle("active", chip.dataset.filter === preset.activeFilter);
        });
        updateVisibility(rows, activeFilter, schoolFilter, preset.searchTerm, resultCounter, dateFrom, dateTo);
    };
    const deletePreset = (presetId) => {
        const presets = loadPresets();
        const filtered = presets.filter((p) => p.id !== presetId);
        savePresets(filtered);
        renderPresets();
    };
    const renderRecentlyViewed = () => {
        if (!recentlyViewedList)
            return;
        const recent = loadRecentlyViewed();
        if (recent.length === 0) {
            recentlyViewedList.innerHTML = '<p class="empty-message">Nessun annuncio visualizzato di recente.</p>';
            return;
        }
        recentlyViewedList.innerHTML = recent.map((item) => `
      <a href="/announcement/${item.id}" class="recent-item">
        <div class="recent-info">
          <strong class="recent-title">${item.title}</strong>
          <span class="recent-school">${item.school}</span>
        </div>
        <span class="recent-time">${formatTimeAgo(item.viewedAt)}</span>
      </a>
    `).join("");
    };
    const formatTimeAgo = (isoString) => {
        const now = new Date().getTime();
        const then = new Date(isoString).getTime();
        const diffMs = now - then;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        if (diffMins < 1)
            return "Ora";
        if (diffMins < 60)
            return `${diffMins}m fa`;
        if (diffHours < 24)
            return `${diffHours}h fa`;
        if (diffDays < 7)
            return `${diffDays}g fa`;
        return new Date(isoString).toLocaleDateString();
    };
    rows.forEach((row) => {
        const annId = row.dataset.id || "";
        const select = row.querySelector(".state-select");
        const link = row.querySelector(".detail-link");
        const currentState = personalStates[annId] || "none";
        applyState(row, currentState);
        if (select) {
            select.addEventListener("change", () => {
                applyState(row, select.value);
            });
        }
        if (link) {
            link.addEventListener("click", () => {
                applyState(row, "read");
                const title = row.dataset.title || "";
                const school = row.dataset.school || "";
                addRecentlyViewed(annId, title, school);
                renderRecentlyViewed();
            });
        }
    });
    headers.forEach((header) => {
        header.addEventListener("click", () => {
            const sortKey = header.dataset.sort;
            if (sortKey) {
                currentSort = sortRows(sortKey, rows, tbody, headers, currentSort, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
            }
        });
    });
    chipButtons.forEach((chip) => {
        chip.addEventListener("click", () => {
            chipButtons.forEach((c) => c.classList.remove("active"));
            chip.classList.add("active");
            activeFilter = chip.dataset.filter;
            updateVisibility(rows, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
        });
    });
    if (schoolSelect) {
        schoolSelect.addEventListener("change", () => {
            schoolFilter = schoolSelect.value;
            updateVisibility(rows, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
        });
    }
    if (dateFromInput) {
        dateFromInput.addEventListener("change", () => {
            dateFrom = dateFromInput.value;
            updateVisibility(rows, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
        });
    }
    if (dateToInput) {
        dateToInput.addEventListener("change", () => {
            dateTo = dateToInput.value;
            updateVisibility(rows, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
        });
    }
    if (clearDatesBtn) {
        clearDatesBtn.addEventListener("click", () => {
            if (dateFromInput)
                dateFromInput.value = "";
            if (dateToInput)
                dateToInput.value = "";
            dateFrom = "";
            dateTo = "";
            updateVisibility(rows, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
        });
    }
    if (savePresetBtn) {
        savePresetBtn.addEventListener("click", () => {
            const name = prompt("Nome del filtro:");
            if (!name)
                return;
            const preset = {
                id: Date.now().toString(),
                name,
                searchTerm: searchInput.value,
                schoolFilter,
                activeFilter,
                dateFrom,
                dateTo,
                createdAt: new Date().toISOString(),
            };
            const presets = loadPresets();
            presets.unshift(preset);
            savePresets(presets);
            renderPresets();
        });
    }
    if (clearRecentBtn) {
        clearRecentBtn.addEventListener("click", () => {
            if (confirm("Cancellare la cronologia visualizzazioni?")) {
                saveRecentlyViewed([]);
                renderRecentlyViewed();
            }
        });
    }
    searchInput.addEventListener("input", () => {
        const term = searchInput.value.trim().toLowerCase();
        updateVisibility(rows, activeFilter, schoolFilter, term, resultCounter, dateFrom, dateTo);
    });
    const viewButtons = document.querySelectorAll(".view-btn");
    const tableView = document.getElementById("annTable");
    const cardView = document.getElementById("cardView");
    viewButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const view = btn.dataset.view;
            viewButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            if (view === "table") {
                if (tableView)
                    tableView.style.display = "table";
                if (cardView)
                    cardView.style.display = "none";
            }
            else if (view === "cards") {
                if (tableView)
                    tableView.style.display = "none";
                if (cardView)
                    cardView.style.display = "grid";
                const cards = cardView?.querySelectorAll(".announcement-card");
                cards?.forEach((card) => {
                    const cardRow = card;
                    const show = matchesFilter(cardRow, activeFilter, schoolFilter, dateFrom, dateTo) && matchesSearch(cardRow, searchInput.value.trim().toLowerCase());
                    card.style.display = show ? "block" : "none";
                });
            }
        });
    });
    const statCards = document.querySelectorAll(".stat-card[data-quick-filter]");
    statCards.forEach((card) => {
        card.addEventListener("click", () => {
            const filterType = card.dataset.quickFilter;
            statCards.forEach((c) => c.classList.remove("active"));
            card.classList.add("active");
            if (filterType === "all") {
                chipButtons.forEach((c) => c.classList.remove("active"));
                chipButtons[0]?.classList.add("active");
                activeFilter = "none";
            }
            else if (filterType === "highlight") {
                chipButtons.forEach((c) => c.classList.remove("active"));
                chipButtons[1]?.classList.add("active");
                activeFilter = "highlight";
            }
            else if (filterType === "open") {
                chipButtons.forEach((c) => c.classList.remove("active"));
                chipButtons[2]?.classList.add("active");
                activeFilter = "open";
            }
            updateVisibility(rows, activeFilter, schoolFilter, searchInput.value.trim().toLowerCase(), resultCounter, dateFrom, dateTo);
        });
    });
    const exportBtn = document.getElementById("exportBtn");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            const visibleRows = rows.filter((row) => row.style.display !== "none");
            const csvData = [
                ["ID", "Titolo", "Scuola", "Città", "Categoria", "Data", "Stato", "Link"]
            ];
            visibleRows.forEach((row) => {
                const id = row.dataset.id || "";
                const title = row.dataset.title || "";
                const school = row.dataset.school || "";
                const city = row.dataset.city || "";
                const category = row.dataset.category || "";
                const date = row.dataset.date || "";
                const status = row.dataset.status || "";
                const link = row.querySelector(".detail-link")?.href || "";
                csvData.push([id, title, school, city, category, date, status, link]);
            });
            const csvContent = csvData.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
            const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `annunci_${new Date().toISOString().split("T")[0]}.csv`;
            link.click();
        });
    }
    const selectAllCheckbox = document.getElementById("selectAllCheckbox");
    const rowCheckboxes = document.querySelectorAll(".row-checkbox");
    const selectAllBtn = document.getElementById("selectAllBtn");
    const deselectAllBtn = document.getElementById("deselectAllBtn");
    const selectedCount = document.getElementById("selectedCount");
    const bulkReadBtn = document.getElementById("bulkReadBtn");
    const bulkSkipBtn = document.getElementById("bulkSkipBtn");
    const updateBulkActions = () => {
        const checked = Array.from(rowCheckboxes).filter((cb) => cb.checked && cb.closest("tr")?.style.display !== "none");
        const count = checked.length;
        if (selectedCount) {
            selectedCount.querySelector("strong").textContent = count.toString();
            selectedCount.style.display = count > 0 ? "inline" : "none";
        }
        if (bulkReadBtn)
            bulkReadBtn.disabled = count === 0;
        if (bulkSkipBtn)
            bulkSkipBtn.disabled = count === 0;
    };
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener("change", () => {
            const visibleCheckboxes = Array.from(rowCheckboxes).filter((cb) => cb.closest("tr")?.style.display !== "none");
            visibleCheckboxes.forEach((cb) => {
                cb.checked = selectAllCheckbox.checked;
            });
            updateBulkActions();
        });
    }
    rowCheckboxes.forEach((cb) => {
        cb.addEventListener("change", updateBulkActions);
    });
    if (selectAllBtn) {
        selectAllBtn.addEventListener("click", () => {
            const visibleCheckboxes = Array.from(rowCheckboxes).filter((cb) => cb.closest("tr")?.style.display !== "none");
            visibleCheckboxes.forEach((cb) => {
                cb.checked = true;
            });
            updateBulkActions();
        });
    }
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener("click", () => {
            rowCheckboxes.forEach((cb) => {
                cb.checked = false;
            });
            updateBulkActions();
        });
    }
    if (bulkReadBtn) {
        bulkReadBtn.addEventListener("click", () => {
            const checked = Array.from(rowCheckboxes).filter((cb) => cb.checked);
            checked.forEach((cb) => {
                const row = cb.closest("tr");
                if (row) {
                    applyState(row, "read");
                }
            });
            rowCheckboxes.forEach((cb) => {
                cb.checked = false;
            });
            updateBulkActions();
        });
    }
    if (bulkSkipBtn) {
        bulkSkipBtn.addEventListener("click", () => {
            const checked = Array.from(rowCheckboxes).filter((cb) => cb.checked);
            checked.forEach((cb) => {
                const row = cb.closest("tr");
                if (row) {
                    applyState(row, "skip");
                }
            });
            rowCheckboxes.forEach((cb) => {
                cb.checked = false;
            });
            updateBulkActions();
        });
    }
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }
        if (e.key === "Escape") {
            if (document.activeElement === searchInput) {
                searchInput.value = "";
                searchInput.blur();
                updateVisibility(rows, activeFilter, schoolFilter, "", resultCounter, dateFrom, dateTo);
            }
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "a" && document.activeElement !== searchInput) {
            e.preventDefault();
            const visibleCheckboxes = Array.from(rowCheckboxes).filter((cb) => cb.closest("tr")?.style.display !== "none");
            visibleCheckboxes.forEach((cb) => {
                cb.checked = true;
            });
            updateBulkActions();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === "e") {
            e.preventDefault();
            exportBtn?.click();
        }
    });
    currentSort = sortRows("date", rows, tbody, headers, currentSort, activeFilter, schoolFilter, "", resultCounter, dateFrom, dateTo);
    renderPresets();
    renderRecentlyViewed();
}
document.addEventListener("DOMContentLoaded", initDashboard);
//# sourceMappingURL=main.js.map