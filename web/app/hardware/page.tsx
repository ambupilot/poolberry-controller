import Link from "next/link";
import OutputPanel from "./output-panel";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

type OutputState = { device_id: string; r1: boolean; r2: boolean; r3: boolean; r4: boolean; r5: boolean; r6: boolean; r7: boolean; r8: boolean; updated_at: string; };

async function getOutputState(): Promise<OutputState | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/output-state`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch { return null; }
}

export default async function HardwarePage() {
  const state = await getOutputState();
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
        <p>Deze pagina stuurt R1–R8 rechtstreeks aan. Er worden hier bewust geen hydraulische interlocks of programmaregels toegepast. Onveilige relais- en klepcombinaties zijn mogelijk.</p>
        <p className="cardMeta">Alleen beschikbaar voor gebruikers met de rol ADMIN.</p>
      </section>
      {!state ? (
        <section className="panel warning"><h2>Outputstatus niet beschikbaar</h2><p>De hoofdcontroller heeft nog geen actuele outputstatus naar de VPS gestuurd.</p></section>
      ) : (
        <section className="panel">
          <h2>Directe relaisbediening</h2>
          <OutputPanel initialState={state} />
        </section>
      )}
    </main>
  );
}
