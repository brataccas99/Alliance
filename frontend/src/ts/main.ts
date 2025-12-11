/**
 * Main TypeScript file for Alliance PNRR Futura Dashboard
 */

interface AnnouncementRow extends HTMLTableRowElement {
  dataset: DOMStringMap & {
    date: string;
    title: string;
    school: string;
    category: string;
    status: string;
    highlight: string;
    search: string;
    sort?: string;
    filter?: string;
  };
}

type SortKey = "title" | "school" | "category" | "date" | "status";
type SortDirection = "asc" | "desc";
type FilterType = "none" | "highlight" | "open";

interface SortState {
  key: SortKey;
  direction: SortDirection;
}

/**
 * Parse date string to timestamp
 */
function parseDate(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

/**
 * Check if row matches active filter
 */
function matchesFilter(row: AnnouncementRow, activeFilter: FilterType): boolean {
  if (activeFilter === "highlight" && row.dataset.highlight !== "true") {
    return false;
  }
  if (activeFilter === "open" && row.dataset.status?.toLowerCase() !== "open") {
    return false;
  }
  return true;
}

/**
 * Check if row matches search term
 */
function matchesSearch(row: AnnouncementRow, term: string): boolean {
  if (!term) return true;
  const haystack = row.dataset.search?.toLowerCase() || "";
  return haystack.includes(term);
}

/**
 * Update visibility of table rows based on filters and search
 */
function updateVisibility(
  rows: AnnouncementRow[],
  activeFilter: FilterType,
  searchTerm: string,
  resultCounter: HTMLElement
): void {
  let visible = 0;
  rows.forEach((row) => {
    const show = matchesFilter(row, activeFilter) && matchesSearch(row, searchTerm);
    row.style.display = show ? "table-row" : "none";
    if (show) visible += 1;
  });
  resultCounter.textContent = `${visible} record`;
}

/**
 * Sort table rows by specified key
 */
function sortRows(
  key: SortKey,
  rows: AnnouncementRow[],
  tbody: HTMLTableSectionElement,
  headers: NodeListOf<HTMLTableCellElement>,
  currentSort: SortState,
  activeFilter: FilterType,
  searchTerm: string,
  resultCounter: HTMLElement
): SortState {
  const direction: SortDirection =
    currentSort.key === key && currentSort.direction === "asc" ? "desc" : "asc";
  const newSort: SortState = { key, direction };

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
    const sortKey = h.dataset.sort as SortKey;
    h.classList.toggle("active", sortKey === key);
  });

  updateVisibility(rows, activeFilter, searchTerm, resultCounter);

  return newSort;
}

/**
 * Initialize the dashboard
 */
function initDashboard(): void {
  const table = document.getElementById("annTable") as HTMLTableElement | null;
  if (!table) return;

  const tbody = table.querySelector("tbody") as HTMLTableSectionElement | null;
  if (!tbody) return;

  const headers = table.querySelectorAll<HTMLTableCellElement>("th[data-sort]");
  const searchInput = document.getElementById("searchInput") as HTMLInputElement | null;
  const resultCounter = document.getElementById("resultsCount") as HTMLElement | null;
  const chipButtons = Array.from(
    document.querySelectorAll<HTMLButtonElement>(".chip")
  );

  if (!searchInput || !resultCounter) return;

  let rows = Array.from(
    tbody.querySelectorAll<AnnouncementRow>("tr")
  ) as AnnouncementRow[];
  let activeFilter: FilterType = "none";
  let currentSort: SortState = { key: "date", direction: "desc" };

  // Header click handlers for sorting
  headers.forEach((header) => {
    header.addEventListener("click", () => {
      const sortKey = header.dataset.sort as SortKey;
      if (sortKey) {
        currentSort = sortRows(
          sortKey,
          rows,
          tbody,
          headers,
          currentSort,
          activeFilter,
          searchInput.value.trim().toLowerCase(),
          resultCounter
        );
      }
    });
  });

  // Chip filter handlers
  chipButtons.forEach((chip) => {
    chip.addEventListener("click", () => {
      chipButtons.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeFilter = chip.dataset.filter as FilterType;
      updateVisibility(
        rows,
        activeFilter,
        searchInput.value.trim().toLowerCase(),
        resultCounter
      );
    });
  });

  // Search input handler
  searchInput.addEventListener("input", () => {
    const term = searchInput.value.trim().toLowerCase();
    updateVisibility(rows, activeFilter, term, resultCounter);
  });

  // Initialize: sort by date desc and apply default filter/search
  currentSort = sortRows(
    "date",
    rows,
    tbody,
    headers,
    currentSort,
    activeFilter,
    "",
    resultCounter
  );
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initDashboard);
