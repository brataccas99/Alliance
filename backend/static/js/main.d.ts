interface AnnouncementRow extends HTMLTableRowElement {
    dataset: DOMStringMap & {
        id: string;
        date: string;
        title: string;
        school: string;
        schoolId: string;
        city: string;
        category: string;
        status: string;
        highlight: string;
        summary: string;
        year: string;
        search: string;
        sort?: string;
        filter?: string;
    };
}
type SortKey = "title" | "school" | "city" | "category" | "date" | "status";
type SortDirection = "asc" | "desc";
type FilterType = "none" | "highlight" | "open" | "pnrr" | "pon" | "recent";
interface SortState {
    key: SortKey;
    direction: SortDirection;
}
type PersonalState = "none" | "read" | "applied" | "skip";
interface FilterPreset {
    id: string;
    name: string;
    searchTerm: string;
    schoolFilter: string;
    activeFilter: FilterType;
    dateFrom: string;
    dateTo: string;
    createdAt: string;
}
interface RecentAnnouncement {
    id: string;
    title: string;
    school: string;
    viewedAt: string;
}
declare const STATE_STORAGE_KEY = "alliance_ann_states";
declare const PRESETS_STORAGE_KEY = "alliance_filter_presets";
declare const RECENT_STORAGE_KEY = "alliance_recent_viewed";
declare function loadStates(): Record<string, PersonalState>;
declare function saveStates(states: Record<string, PersonalState>): void;
declare function loadPresets(): FilterPreset[];
declare function savePresets(presets: FilterPreset[]): void;
declare function loadRecentlyViewed(): RecentAnnouncement[];
declare function saveRecentlyViewed(recent: RecentAnnouncement[]): void;
declare function addRecentlyViewed(id: string, title: string, school: string): void;
declare function parseDate(value: string): number;
declare function matchesFilter(row: AnnouncementRow, activeFilter: FilterType, schoolFilter: string, yearFilter: string, dateFrom: string, dateTo: string): boolean;
declare function matchesSearch(row: AnnouncementRow, term: string): boolean;
declare function updateVisibility(rows: AnnouncementRow[], activeFilter: FilterType, schoolFilter: string, yearFilter: string, searchTerm: string, resultCounter: HTMLElement, dateFrom?: string, dateTo?: string): void;
declare function sortRows(key: SortKey, rows: AnnouncementRow[], tbody: HTMLTableSectionElement, headers: NodeListOf<HTMLTableCellElement>, currentSort: SortState, activeFilter: FilterType, schoolFilter: string, yearFilter: string, searchTerm: string, resultCounter: HTMLElement, dateFrom?: string, dateTo?: string): SortState;
declare function initDashboard(): void;
//# sourceMappingURL=main.d.ts.map