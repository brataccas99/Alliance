"use strict";
function parseDate(value) {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
}
function matchesFilter(row, activeFilter) {
    if (activeFilter === "highlight" && row.dataset.highlight !== "true") {
        return false;
    }
    if (activeFilter === "open" && row.dataset.status?.toLowerCase() !== "open") {
        return false;
    }
    return true;
}
function matchesSearch(row, term) {
    if (!term)
        return true;
    const haystack = row.dataset.search?.toLowerCase() || "";
    return haystack.includes(term);
}
function updateVisibility(rows, activeFilter, searchTerm, resultCounter) {
    let visible = 0;
    rows.forEach((row) => {
        const show = matchesFilter(row, activeFilter) && matchesSearch(row, searchTerm);
        row.style.display = show ? "table-row" : "none";
        if (show)
            visible += 1;
    });
    resultCounter.textContent = `${visible} record`;
}
function sortRows(key, rows, tbody, headers, currentSort, activeFilter, searchTerm, resultCounter) {
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
    updateVisibility(rows, activeFilter, searchTerm, resultCounter);
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
    const resultCounter = document.getElementById("resultsCount");
    const chipButtons = Array.from(document.querySelectorAll(".chip"));
    if (!searchInput || !resultCounter)
        return;
    let rows = Array.from(tbody.querySelectorAll("tr"));
    let activeFilter = "none";
    let currentSort = { key: "date", direction: "desc" };
    headers.forEach((header) => {
        header.addEventListener("click", () => {
            const sortKey = header.dataset.sort;
            if (sortKey) {
                currentSort = sortRows(sortKey, rows, tbody, headers, currentSort, activeFilter, searchInput.value.trim().toLowerCase(), resultCounter);
            }
        });
    });
    chipButtons.forEach((chip) => {
        chip.addEventListener("click", () => {
            chipButtons.forEach((c) => c.classList.remove("active"));
            chip.classList.add("active");
            activeFilter = chip.dataset.filter;
            updateVisibility(rows, activeFilter, searchInput.value.trim().toLowerCase(), resultCounter);
        });
    });
    searchInput.addEventListener("input", () => {
        const term = searchInput.value.trim().toLowerCase();
        updateVisibility(rows, activeFilter, term, resultCounter);
    });
    currentSort = sortRows("date", rows, tbody, headers, currentSort, activeFilter, "", resultCounter);
}
document.addEventListener("DOMContentLoaded", initDashboard);
//# sourceMappingURL=main.js.map