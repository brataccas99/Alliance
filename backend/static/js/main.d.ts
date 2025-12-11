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
declare function parseDate(value: string): number;
declare function matchesFilter(row: AnnouncementRow, activeFilter: FilterType): boolean;
declare function matchesSearch(row: AnnouncementRow, term: string): boolean;
declare function updateVisibility(rows: AnnouncementRow[], activeFilter: FilterType, searchTerm: string, resultCounter: HTMLElement): void;
declare function sortRows(key: SortKey, rows: AnnouncementRow[], tbody: HTMLTableSectionElement, headers: NodeListOf<HTMLTableCellElement>, currentSort: SortState, activeFilter: FilterType, searchTerm: string, resultCounter: HTMLElement): SortState;
declare function initDashboard(): void;
//# sourceMappingURL=main.d.ts.map