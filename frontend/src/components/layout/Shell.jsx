import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar.jsx";
import { Topbar } from "./Topbar.jsx";
import { useLiveStream } from "../../hooks/useLiveStream.js";
import { useSentinelStore } from "../../stores/useSentinelStore.js";
import { Toast } from "../ui/Toast.jsx";

export function Shell() {
  useLiveStream();
  const toast = useSentinelStore((s) => s.toast);
  const dismissToast = useSentinelStore((s) => s.dismissToast);
  return (
    <div className="flex min-h-screen bg-bg text-text">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar />
        <main className="flex-1 px-6 py-6">
          <div className="max-w-7xl mx-auto animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
      {toast && <Toast toast={toast} onDismiss={dismissToast} />}
    </div>
  );
}
