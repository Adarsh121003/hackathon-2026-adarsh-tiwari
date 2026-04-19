import { create } from "zustand";

const MAX_EVENTS = 120;

export const useSentinelStore = create((set, get) => ({
  streamStatus: "idle", // idle | connecting | open | error | failed
  events: [],
  toast: null,

  pushEvent: (ev) =>
    set((s) => {
      const next = [{ ...ev, _receivedAt: Date.now() }, ...s.events];
      if (next.length > MAX_EVENTS) next.length = MAX_EVENTS;
      return { events: next };
    }),

  clearEvents: () => set({ events: [] }),

  setStreamStatus: (status) => set({ streamStatus: status }),

  showToast: (toast) => {
    set({ toast: { ...toast, id: Date.now() } });
    setTimeout(() => {
      const current = get().toast;
      if (current && current.id === toast.id) set({ toast: null });
    }, 4500);
  },
  dismissToast: () => set({ toast: null }),

  // Filter state for Tickets page (in-memory only)
  ticketFilters: {
    search: "",
    status: "all",
    category: "all",
  },
  setTicketFilter: (key, value) =>
    set((s) => ({
      ticketFilters: { ...s.ticketFilters, [key]: value },
    })),
  resetTicketFilters: () =>
    set({
      ticketFilters: { search: "", status: "all", category: "all" },
    }),
}));
