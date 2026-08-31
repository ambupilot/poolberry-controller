"use client";

import { useEffect, useRef, useState } from "react";

type OutputKey = "r1" | "r2" | "r3" | "r4" | "r5" | "r6" | "r7" | "r8";
type OutputId = "R1" | "R2" | "R3" | "R4" | "R5" | "R6" | "R7" | "R8";
type ControllerModeName = "NORMAL" | "MANUAL";

type OutputState = {
  device_id: string;
  r1: boolean; r2: boolean; r3: boolean; r4: boolean;
  r5: boolean; r6: boolean; r7: boolean; r8: boolean;
  updated_at: string;
};

type ControllerMode = {
  device_id: string;
  mode: ControllerModeName;
  updated_at: string;
};

type OutputDefinition = {
  id: OutputId;
  key: OutputKey;
  gpio: string;
  role: string;
  type: "Pomp" | "NO-klep" | "NC-klep";
};

const outputs: OutputDefinition[] = [
  { id: "R1", key: "r1", gpio: "GP8", role: "Filterpomp", type: "Pomp" },
  { id: "R2", key: "r2", gpio: "GP9", role: "Warmtepomp", type: "Pomp" },
  { id: "R3", key: "r3", gpio: "GP10", role: "Bronpomp", type: "Pomp" },
  { id: "R4", key: "r4", gpio: "GP11", role: "Aanvoer VAN zwembad", type: "NO-klep" },
  { id: "R5", key: "r5", gpio: "GP12", role: "Bronpomp-aanvoer", type: "NC-klep" },
  { id: "R6", key: "r6", gpio: "GP13", role: "Tuin", type: "NO-klep" },
  { id: "R7", key: "r7", gpio: "GP14", role: "Bypass collector", type: "NC-klep" },
  { id: "R8", key: "r8", gpio: "GP15", role: "Aanvoer NAAR zwembad", type: "NO-klep" },
];

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("nl-NL", {
    dateStyle: "medium", timeStyle: "medium", timeZone: "Europe/Amsterdam",
  }).format(new Date(value));
}

function physicalState(output: OutputDefinition, relayActive: boolean) {
  if (output.type === "Pomp") return relayActive ? "AAN" : "UIT";
  if (output.type === "NO-klep") return relayActive ? "GESLOTEN" : "OPEN";
  return relayActive ? "OPEN" : "GESLOTEN";
}

function actionLabel(output: OutputDefinition, relayActive: boolean) {
  if (output.type === "Pomp") return `${output.id} ${relayActive ? "uitschakelen" : "inschakelen"}`;
  return `${output.id} ${relayActive ? "vrijgeven" : "bekrachtigen"}`;
}

export default function OutputPanel({ initialState, initialMode }: { initialState: OutputState; initialMode: ControllerMode }) {
  const [state, setState] = useState(initialState);
  const [mode, setMode] = useState(initialMode);
  const [pending, setPending] = useState<Partial<Record<OutputId, boolean>>>({});
  const [modePending, setModePending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pendingSince = useRef<Partial<Record<OutputId, number>>>({});

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const [stateResponse, modeResponse] = await Promise.all([
          fetch("/browser-api/output-state", { cache: "no-store" }),
          fetch("/browser-api/mode", { cache: "no-store" }),
        ]);
        if (!stateResponse.ok || !modeResponse.ok) throw new Error("status");
        const nextState = (await stateResponse.json()) as OutputState;
        const nextMode = (await modeResponse.json()) as ControllerMode;
        if (cancelled) return;
        setState(nextState);
        setMode(nextMode);
        setError(null);

        setPending((current) => {
          const updated = { ...current };
          for (const output of outputs) {
            const target = current[output.id];
            if (target === undefined) continue;
            if (nextState[output.key] === target) {
              delete updated[output.id];
              delete pendingSince.current[output.id];
            } else {
              const started = pendingSince.current[output.id];
              if (started && Date.now() - started > 10000) {
                delete updated[output.id];
                delete pendingSince.current[output.id];
                setError(`${output.id}-opdracht is niet binnen 10 seconden bevestigd door de controller.`);
              }
            }
          }
          return updated;
        });
      } catch {
        if (!cancelled) setError("Actuele outputstatus of controller-modus kon niet worden opgehaald.");
      }
    }

    const timer = window.setInterval(refresh, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  async function changeMode(target: ControllerModeName) {
    setModePending(true);
    setError(null);
    try {
      const response = await fetch("/browser-api/mode", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: target }),
      });
      if (!response.ok) throw new Error("mode");
      const next = (await response.json()) as ControllerMode;
      setMode(next);
      if (target === "NORMAL") {
        setPending({});
        pendingSince.current = {};
      }
    } catch {
      setError(`Controller kon niet naar ${target} worden gezet.`);
    } finally {
      setModePending(false);
    }
  }

  async function commandOutput(output: OutputDefinition, enabled: boolean) {
    if (mode.mode !== "MANUAL") {
      setError("Directe relaisbediening is alleen toegestaan wanneer MANUAL actief is.");
      return;
    }

    setPending((current) => ({ ...current, [output.id]: enabled }));
    pendingSince.current[output.id] = Date.now();
    setError(null);

    try {
      const response = await fetch(`/browser-api/outputs/${output.id}/command`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error("command");
    } catch {
      setPending((current) => {
        const updated = { ...current };
        delete updated[output.id];
        return updated;
      });
      delete pendingSince.current[output.id];
      setError(`${output.id}-opdracht kon niet worden verstuurd.`);
    }
  }

  const manualActive = mode.mode === "MANUAL";

  return <>
    <div className="card" style={{ marginTop: 16, marginBottom: 20 }}>
      <div className="cardLabel">Controller-modus</div>
      <div className="cardValue" style={{ color: manualActive ? "#dc2626" : undefined }}>
        {manualActive ? "MANUAL ACTIEF" : "NORMAL"}
      </div>
      <div className="cardMeta">Gewijzigd {formatDateTime(mode.updated_at)}</div>
      <div className="cardMeta" style={{ marginTop: 8 }}>
        {manualActive
          ? "Automatische/operationele besturing is geblokkeerd. R1–R8 kunnen rechtstreeks worden geschakeld."
          : "Directe relaisbediening is vergrendeld."}
      </div>
      <button
        type="button"
        className="primaryButton"
        style={{ marginTop: 16 }}
        disabled={modePending}
        onClick={() => changeMode(manualActive ? "NORMAL" : "MANUAL")}
      >
        {modePending ? "Modus wijzigen…" : manualActive ? "MANUAL beëindigen" : "MANUAL inschakelen"}
      </button>
      {manualActive && <p className="cardMeta" style={{ marginTop: 10 }}>Bij beëindigen worden R1–R8 naar relais UIT gestuurd.</p>}
    </div>

    <p className="cardMeta">Laatste outputsynchronisatie {formatDateTime(state.updated_at)} · automatische statuscontrole iedere 2 seconden</p>
    <p className="cardMeta">Relais LOW = UIT, HIGH = AAN. Bij kleppen wordt de hydraulische OPEN/GESLOTEN-stand afgeleid uit het NO/NC-type.</p>
    {error && <div className="panel warning" style={{ marginTop: 16 }}><p>{error}</p></div>}

    <div className="grid" style={{ marginTop: 20 }}>
      {outputs.map((output) => {
        const relayActive = state[output.key];
        const switching = pending[output.id] !== undefined;
        const displayState = switching ? "SCHAKELEN…" : physicalState(output, relayActive);
        const isPump = output.type === "Pomp";
        const mainStateStyle = !switching && relayActive
          ? { color: isPump ? "#16a34a" : "#dc2626" }
          : undefined;

        return <article className={`card ${relayActive ? "primaryCard" : ""}`} key={output.id}>
          <div className="cardLabel">{output.id} · {output.gpio}</div>
          <div className="cardValue" style={mainStateStyle}>{displayState}</div>
          <div className="cardMeta">{output.role}</div>
          <div className="cardMeta">{output.type} · relais {relayActive ? "AAN" : "UIT"}</div>
          <button
            type="button"
            className="primaryButton"
            style={{ marginTop: 16 }}
            disabled={!manualActive || switching || modePending}
            onClick={() => commandOutput(output, !relayActive)}
          >
            {!manualActive ? "MANUAL vereist" : switching ? "Wachten op controller…" : actionLabel(output, relayActive)}
          </button>
        </article>;
      })}
    </div>
  </>;
}
