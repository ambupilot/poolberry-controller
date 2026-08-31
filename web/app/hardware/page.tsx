import Link from "next/link";
import OutputPanel from "./output-panel";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

type OutputState = { device_id: string; r1: boolean; r2: boolean; r3: boolean; r4: boolean; r5: boolean; r6: boolean; r7: boolean; r8: boolean; updated_at: string; };
type ControllerMode = { device_id: string; mode: "NORMAL" | "MANUAL"; updated_at: string; };

async function getOutputState(): Promise<OutputState | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/output-state`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch { return null; }
}

async function getControllerMode(): Promise<ControllerMode | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/mode`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch { return null; }
}

export default async function HardwarePage() {
  const [state, mode] = await Promise.all([getOutputState(), getControllerMode()]);
  return (
    <main className="shell">
      <header className="topbar"><div><p className="eyebrow">PoolBerry Control · ADMIN</p><h1>Hardware / Manual</h1></div></header>
      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab" href="/">Dashboard</Link><Link className="tab" href="/configuration">Configuratie</Link>
        <span className="tab disabled">Programma&apos;s</span><Link className="tab active" href="/hardware">Hardware</Link>
        <span className="tab disabled">Historie</span><span className="tab disabled">Events</span><span className="tab disabled">Systeem</span>
      </nav>
      <section className="panel warning" style={{ marginBottom: 20 }}>
        <h2>MANUAL / SERVICE</h2>
        <p>In MANUAL worden R1–R8 rechtstreeks aangestuurd. Er worden bewust geen hydraulische interlocks of programmaregels toegepast. Onveilige relais- en klepcombinaties zijn mogelijk.</p>
        <p className="cardMeta">Alleen beschikbaar voor gebruikers met de rol ADMIN. Bij het beëindigen van MANUAL worden alle acht relais als veilige tussenstand naar UIT gestuurd.</p>
      </section>
      {!state || !mode ? (
        <section className="panel warning"><h2>Controllerstatus niet beschikbaar</h2><p>Outputstatus of controller-modus kon niet uit de PoolBerry API worden opgehaald.</p></section>
      ) : (
        <section className="panel">
          <h2>Directe relaisbediening</h2>
          <OutputPanel initialState={state} initialMode={mode} />
        </section>
      )}
    </main>
  );
}
