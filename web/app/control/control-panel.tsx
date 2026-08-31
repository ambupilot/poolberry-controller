"use client";

import { useEffect, useState } from "react";

type OutputState = { r1: boolean; r2: boolean; r3: boolean; r4: boolean; r5: boolean; r6: boolean; r7: boolean; r8: boolean; updated_at: string; };
type ControllerMode = { mode: "NORMAL" | "MANUAL"; updated_at: string };
type CollectorTransition = "opening" | "closing" | null;

const controls = [
  { key: "filter", label: "FILTERPOMP", on: "AAN", off: "UIT", enabled: true },
  { key: "heat", label: "WARMTEPOMP", on: "AAN", off: "UIT", enabled: true },
  { key: "collector", label: "COLLECTOR", on: "OPEN", off: "DICHT", enabled: true },
  { key: "source", label: "BRONPOMP", on: "AAN", off: "UIT", enabled: true },
];
const programs = ["AUTO", "SPOELEN", "SPROEIEN"];
const base = { minHeight: 72, border: 0, borderRadius: 10, color: "white", fontWeight: 700, fontSize: 15, lineHeight: 1.2, letterSpacing: "0.02em" } as const;
const blinkStyle = { animation: "poolberryControlBlink 0.8s ease-in-out infinite alternate" } as const;

export default function ControlPanel({ initialState, initialMode }: { initialState: OutputState; initialMode: ControllerMode }) {
  const [state, setState] = useState(initialState); const [mode, setMode] = useState(initialMode); const [busy, setBusy] = useState(false); const [message, setMessage] = useState<string | null>(null); const [collectorTransition, setCollectorTransition] = useState<CollectorTransition>(null); const [filterStopping, setFilterStopping] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const [s, m] = await Promise.all([fetch("/browser-api/output-state", { cache: "no-store" }), fetch("/browser-api/mode", { cache: "no-store" })]); if (!s.ok || !m.ok) return;
        const nextState: OutputState = await s.json(); const nextMode = await m.json();
        if (!cancelled) {
          setState(nextState); setMode(nextMode);
          setCollectorTransition((current) => {
            if (current === "opening" && nextState.r7 && nextState.r8) return null;
            if (current === "closing" && !nextState.r7 && !nextState.r8) return null;
            return current;
          });
          if (!nextState.r1) setFilterStopping(false);
        }
      } catch { /* retry */ }
    }
    const timer = window.setInterval(refresh, 2000); return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  async function operation(kind: "filterpump" | "heatpump" | "collector" | "sourcepump", action: string) {
    setBusy(true); setMessage(null);
    const transition: CollectorTransition = kind === "collector" ? (action === "open" ? "opening" : "closing") : null;
    const stoppingFilter = kind === "filterpump" && action === "off";
    const collectorWasOpen = stoppingFilter && (state.r7 || state.r8);
    if (transition) setCollectorTransition(transition);
    if (stoppingFilter) { setFilterStopping(true); if (collectorWasOpen) setCollectorTransition("closing"); }
    try { const response = await fetch(`/browser-api/operations/${kind}/${action}`, { method: "POST" }); const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Opdracht geweigerd"); setMessage(data.detail ?? "Opdracht verstuurd"); }
    catch (error) { if (transition || collectorWasOpen) setCollectorTransition(null); if (stoppingFilter) setFilterStopping(false); setMessage(error instanceof Error ? error.message : "Opdracht kon niet worden verstuurd"); }
    finally { setBusy(false); }
  }

  async function stop() {
    setBusy(true); setMessage(null); setCollectorTransition(null); setFilterStopping(false);
    try { const response = await fetch("/browser-api/stop", { method: "POST" }); const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "STOP kon niet worden verstuurd"); setMessage("STOP verstuurd · alle relais naar UIT"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "STOP kon niet worden verstuurd"); }
    finally { setBusy(false); }
  }

  const normal = mode.mode === "NORMAL";
  function isOn(key: string) { if (key === "filter") return state.r1; if (key === "heat") return state.r2; if (key === "collector") return state.r7 && state.r8; if (key === "source") return state.r3; return false; }
  function click(key: string, action: "on" | "off") { if (key === "filter") return operation("filterpump", action); if (key === "heat") return operation("heatpump", action); if (key === "collector") return operation("collector", action === "on" ? "open" : "close"); if (key === "source") return operation("sourcepump", action); }
  const transitionActive = collectorTransition !== null || filterStopping;

  return <>
    <style>{`@keyframes poolberryControlBlink { from { opacity: 1; } to { opacity: .28; } }`}</style>
    <section className="panel">
      <h2>Installatie</h2>
      <p className="cardMeta">Controller-modus: {mode.mode}. Operationele pomp- en collectorbediening is actief.</p>
      {message && <div className="panel warning" style={{ marginTop: 12 }}><p>{message}</p></div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, marginTop: 16 }}>
        {controls.map((control) => { const active = isOn(control.key); const clickable = control.enabled && normal && !busy && !transitionActive; const blinking = control.key === "collector" && collectorTransition === "opening"; return <button key={`${control.key}-on`} type="button" disabled={!clickable} onClick={() => click(control.key, "on")} style={{ ...base, background: `rgba(22, 163, 74, ${active || blinking ? "0.90" : "0.20"})`, cursor: clickable ? "pointer" : "not-allowed", ...(blinking ? blinkStyle : {}) }}><span style={{ display: "block" }}>{control.label}</span><span style={{ display: "block", marginTop: 4 }}>{control.on}</span></button>; })}
        {controls.map((control) => { const active = control.enabled && !isOn(control.key); const clickable = control.enabled && normal && !busy && !transitionActive; const blinking = (control.key === "collector" && collectorTransition === "closing") || (control.key === "filter" && filterStopping); return <button key={`${control.key}-off`} type="button" disabled={!clickable} onClick={() => click(control.key, "off")} style={{ ...base, background: `rgba(220, 38, 38, ${active || blinking ? "0.70" : "0.20"})`, cursor: clickable ? "pointer" : "not-allowed", ...(blinking ? blinkStyle : {}) }}><span style={{ display: "block" }}>{control.label}</span><span style={{ display: "block", marginTop: 4 }}>{control.off}</span></button>; })}
      </div>
      {!normal && <p className="cardMeta" style={{ marginTop: 12 }}>Operationele bediening is geblokkeerd zolang MANUAL actief is. STOP blijft wel beschikbaar.</p>}
    </section>
    <section className="panel"><h2>Programma&apos;s</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>{programs.map((program) => <button key={program} type="button" disabled style={{ ...base, background: "rgba(37, 99, 235, 0.20)", cursor: "not-allowed" }}><span style={{ display: "block" }}>{program}</span><span style={{ display: "block", marginTop: 4 }}>UIT</span></button>)}</div></section>
    <section className="panel warning"><h2>STOP</h2><p>STOP omzeilt de normale operationele voorwaarden en stuurt alle relais direct naar UIT/fail-safe.</p><button type="button" disabled={busy} onClick={stop} style={{ ...base, width: "100%", marginTop: 12, background: "rgba(220, 38, 38, 0.70)", cursor: busy ? "not-allowed" : "pointer" }}>STOP · alle relais UIT</button></section>
  </>;
}
