import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { subscribeToStream } from "../lib/sse.js";
import { useSentinelStore } from "../stores/useSentinelStore.js";

export function useLiveStream() {
  const pushEvent = useSentinelStore((s) => s.pushEvent);
  const setStreamStatus = useSentinelStore((s) => s.setStreamStatus);
  const qc = useQueryClient();

  useEffect(() => {
    const unsub = subscribeToStream({
      onEvent: (ev) => {
        if (ev?.type === "heartbeat") return;
        pushEvent(ev);
        if (ev?.type === "complete" || ev?.type === "resolved") {
          qc.invalidateQueries({ queryKey: ["tickets"] });
          qc.invalidateQueries({ queryKey: ["metrics"] });
          if (ev.ticket_id) {
            qc.invalidateQueries({ queryKey: ["ticket", ev.ticket_id] });
          }
        }
      },
      onStatus: setStreamStatus,
    });
    return () => {
      unsub();
      setStreamStatus("idle");
    };
  }, [pushEvent, setStreamStatus, qc]);
}
