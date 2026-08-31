"use client";

import { useEffect, useRef, useState } from "react";

type OutputState = {
  device_id: string;
  r1: boolean; r2: boolean; r3: boolean; r4: boolean;
  r5: boolean; r6: boolean; r7: boolean; r8: boolean;
  updated_at: string;
};

const outputs = [
  { id: "R1", key: "r1" as const, gpio: "GP8", role: "Filterpomp", type: "Pomp" },
  { id: "R2", key: "r2" as const, gpio: "GP9", role: "Warmtepomp", type: "Pomp" },
  { id: "R3", key: "r3" as const, gpio: "GP10", role: "Bronpomp", type: "Pomp" },
  { id: "R4", key: "r4" as const, gpio: "GP11", role: "Aanvoer VAN zwembad", type: "NO-klep" },
  { id: "R5", key: "r5" as const, gpio: "GP12", role: "Bronpomp-aanvoer", type: "NC-klep" },
  { id: "R6", key: "r6" as const, gpio: "GP13", role: "Tuin", type: "NO-klep" },
  { id: "R7", key: "r7" as const, gpio: "GP14", role: "Bypass collector", type: "NC-klep" },
  { id: "R8", key: "r8" as const, gpio: "GP15", role: "Aanvoer NAAR zwembad", type: "NO-klep" },
];

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("nl-NL", {
    dateStyle: "medium", timeStyle: "medium", timeZone: "Europe/Amsterdam",
  }).format(new Date(value));
}

export default function OutputPanel({ initialState }: { initialState: OutputState }) {
  const [state, setState] = useState(initialState);
  const [pendingR1, setPendingR1] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pendingSince = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const response = await fetch("/api/output-state", { cache: "no-store" });
        if (!response.ok) throw new Error("status");
        const next = (await response.json()) as OutputState;
        if (cancelled) return;
        setState(next);
        setError(null);
        if (pendingR1 !== null && next.r1 === pendingR1) {
          setPendingR1(null);
          pendingSince.current = null;
        } else if (pendingSince.current && Date.now() - pendingSince.current > 10000) {
          setPendingR1(null);
          pendingSince.current = null;
          setError("R1-opdracht is niet binnen 10 seconden bevestigd door de controller.");
        }
      } catch {
        if (!cancelled) setError("Actuele outputstatus kon niet worden opgehaald.");
      }
    }

    const timer = window.setInterval(refresh, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [pendingR1]);

  async function commandR1(enabled: boolean) {
    setPendingR1(enabled);
    pendingSince.current = Date.now();
    setError(null);
    try {
      const response = await fetch("/api/outputs/R1/command", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error("command");
    } catch {
      setPendingR1(null);
      pendingSince.current = null;
      setError("R1-opdracht kon niet worden verstuurd.");
    }
  }

  return (
    <>
      <p className="cardMeta">Laatste synchronisatie {formatDateTime(state.updated_at)} · automatische statuscontrole iedere 2 seconden</p>
      <p className="cardMeta">LOW = COM/NO open = UIT. HIGH = COM/NO gesloten = AAN. Alleen R1 is in deze testfase op afstand bestuurbaar.</p>
      {error && <div className="panel warning" style={{ marginTop: 16 }}><p>{error}</p></div>}
      <div className="grid" style={{ marginTop: 20 }}>
        {outputs.map((output) => {
          const active = state[output.key];
          const isR1 = output.id === "R1";
          const switching = isR1 && pendingR1 !== null;
          return (
            <article className={`card ${active ? "primaryCard" : ""}`} key={output.id}>
              <div className="cardLabel">{output.id} · {output.gpio}</div>
              <div className="cardValue">{switching ? "SCHAKELEN…" : active ? "AAN" : "UIT"}</div>
              <div className="cardMeta">{output.role}</div><div className="cardMeta">{output.type}</div>
              {isR1 && (
                <button
                  type="button"
                  className="primaryButton"
                  style={{ marginTop: 16 }}
                  disabled={switching}
                  onClick={() => commandR1(!active)}
                >
                  {switching ? "Wachten op controller…" : `R1 ${active ? "uitschakelen" : "inschakelen"}`}
                </button>
              )}
            </article>
          );
        })}
      </div>
    </>
  );
}
