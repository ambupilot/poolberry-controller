import Link from "next/link";
import ControlPanel from "./control-panel";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

type OutputState = {
  r1: boolean; r2: boolean; r3: boolean; r4: boolean;
  r5: boolean; r6: boolean; r7: boolean; r8: boolean;
  updated_at: string;
};

type ControllerMode = { mode: "NORMAL" | "MANUAL"; updated_at: string };

async function getOutputState(): Promise<OutputState | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/output-state`, { cache: "no-store" });
    return response.ok ? response.json() : null;
  } catch { return null; }
}

async function getMode(): Promise<ControllerMode | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/mode`, { cache: "no-store" });
    return response.ok ? response.json() : null;
  } catch { return null; }
}

export default async function ControlPage() {
  const [state, mode] = await Promise.all([getOutputState(), getMode()]);
  return (
    <main className="shell">
      <header className="topbar">
        <div><p className="eyebrow">PoolBerry Control</p><h1>Bediening</h1></div>
        <div className="topbarActions"><form method="post" action="/auth/logout"><button type="submit" className="logoutButton">Uitloggen</button></form></div>
      </header>

      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab" href="/">Dashboard</Link><Link className="tab active" href="/control">Bediening</Link><Link className="tab" href="/configuration">Configuratie</Link><span className="tab disabled">Programma&apos;s</span><Link className="tab" href="/hardware">Hardware</Link><span className="tab disabled">Historie</span><span className="tab disabled">Events</span><span className="tab disabled">Systeem</span>
      </nav>

      <section className="panel">
        <h2>Operationeel bedieningspaneel</h2>
        <p>Dit paneel geeft functionele opdrachten aan de controller. Het schakelt niet rechtstreeks individuele relais. Dezelfde opdrachten worden later gebruikt door het fysieke bedieningspaneel.</p>
      </section>

      {!state || !mode ? (
        <section className="panel warning"><h2>Controllerstatus niet beschikbaar</h2><p>De actuele outputstatus of controller-modus kon niet worden opgehaald.</p></section>
      ) : <ControlPanel initialState={state} initialMode={mode} />}
    </main>
  );
}
