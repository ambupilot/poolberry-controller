import Link from "next/link";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

type OutputState = {
  device_id: string;
  r1: boolean;
  r2: boolean;
  r3: boolean;
  r4: boolean;
  r5: boolean;
  r6: boolean;
  r7: boolean;
  r8: boolean;
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
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Europe/Amsterdam",
  }).format(new Date(value));
}

async function getOutputState(): Promise<OutputState | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/output-state`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export default async function HardwarePage() {
  const state = await getOutputState();

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PoolBerry Control</p>
          <h1>Hardware</h1>
        </div>
      </header>

      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab" href="/">Dashboard</Link>
        <Link className="tab" href="/configuration">Configuratie</Link>
        <span className="tab disabled">Programma&apos;s</span>
        <Link className="tab active" href="/hardware">Hardware</Link>
        <span className="tab disabled">Historie</span>
        <span className="tab disabled">Events</span>
        <span className="tab disabled">Systeem</span>
      </nav>

      {!state ? (
        <section className="panel warning">
          <h2>Outputstatus niet beschikbaar</h2>
          <p>De hoofdcontroller heeft nog geen actuele outputstatus naar de VPS gestuurd.</p>
        </section>
      ) : (
        <section className="panel">
          <h2>Relais / outputs</h2>
          <p className="cardMeta">Laatste synchronisatie {formatDateTime(state.updated_at)}</p>
          <p className="cardMeta">Dit zijn de door de Pico aangestuurde logische states. De fysieke COM/NO-contactwerking van de testrelais wordt nog afzonderlijk gevalideerd voordat belastingen worden aangesloten.</p>

          <div className="grid" style={{ marginTop: 20 }}>
            {outputs.map((output) => {
              const active = state[output.key];
              return (
                <article className={`card ${active ? "primaryCard" : ""}`} key={output.id}>
                  <div className="cardLabel">{output.id} · {output.gpio}</div>
                  <div className="cardValue">{active ? "AAN" : "UIT"}</div>
                  <div className="cardMeta">{output.role}</div>
                  <div className="cardMeta">{output.type}</div>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}
