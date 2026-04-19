import { Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "./components/layout/Shell.jsx";
import { Dashboard } from "./pages/Dashboard.jsx";
import { Tickets } from "./pages/Tickets.jsx";
import { TicketDetail } from "./pages/TicketDetail.jsx";
import { AuditLog } from "./pages/AuditLog.jsx";
import { About } from "./pages/About.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/audit" element={<AuditLog />} />
        <Route path="/about" element={<About />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
