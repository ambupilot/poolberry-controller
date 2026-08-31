import Link from "next/link";

const installationControls = [
  { label: "FILTERPOMP", on: "AAN", off: "UIT" },
  { label: "WARMTEPOMP", on: "AAN", off: "UIT" },
  { label: "COLLECTOR", on: "OPEN", off: "DICHT" },
  { label: "BRONPOMP", on: "AAN", off: "UIT" },
];

const programs = ["AUTO", "SPOELEN", "SPROEIEN"];

const controlButtonBase = {
  minHeight: 72,
  border: 0,
  borderRadius: 10,
  color: "white",
  fontWeight: 700,
  fontSize: 15,
  lineHeight: 1.2,
  letterSpacing: "0.02em",
  cursor: "not-allowed",
} as const;

export default function ControlPage() {
  return (
    <main className="shell">
      <header className="topbar">
        <div><p className="eyebrow">PoolBerry Control</p><h1>Bediening</h1></div>
        <div className="topbarActions">
          <form method="post" action="/auth/logout"><button type="submit" className="logoutButton">Uitloggen</button></form>
        </div>
      </header>

      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab" href="/">Dashboard</Link>
        <Link className="tab active" href="/control">Bediening</Link>
        <Link className="tab" href="/configuration">Configuratie</Link>
        <span className="tab disabled">Programma&apos;s</span>
        <Link className="tab" href="/hardware">Hardware</Link>
        <span className="tab disabled">Historie</span>
        <span className="tab disabled">Events</span>
        <span className="tab disabled">Systeem</span>
      </nav>

      <section className="panel">
        <h2>Operationeel bedieningspaneel</h2>
        <p>Dit paneel geeft functionele opdrachten aan de controller. Het schakelt niet rechtstreeks individuele relais. Dezelfde opdrachten worden later gebruikt door het fysieke bedieningspaneel.</p>
        <p className="cardMeta">De bedieningsknoppen zijn in deze eerste stap alleen als interface aangebracht. De operationele commandolaag wordt hierna per functie aangesloten.</p>
      </section>

      <section className="panel">
        <h2>Installatie</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
          {installationControls.map((control) => (
            <button key={`${control.label}-on`} type="button" disabled style={{ ...controlButtonBase, background: "rgba(22, 163, 74, 0.35)" }}>
              <span style={{ display: "block" }}>{control.label}</span>
              <span style={{ display: "block", marginTop: 4 }}>{control.on}</span>
            </button>
          ))}
          {installationControls.map((control) => (
            <button key={`${control.label}-off`} type="button" disabled style={{ ...controlButtonBase, background: "rgba(220, 38, 38, 0.35)" }}>
              <span style={{ display: "block" }}>{control.label}</span>
              <span style={{ display: "block", marginTop: 4 }}>{control.off}</span>
            </button>
          ))}
        </div>
        <p className="cardMeta" style={{ marginTop: 12 }}>Gedimd groen/rood = niet actief. De actieve toestand wordt later met de duidelijkere 70%-kleur weergegeven.</p>
      </section>

      <section className="panel">
        <h2>Programma&apos;s</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
          {programs.map((program) => (
            <button key={program} type="button" disabled style={{ ...controlButtonBase, background: "rgba(37, 99, 235, 0.35)" }}>
              <span style={{ display: "block" }}>{program}</span>
              <span style={{ display: "block", marginTop: 4 }}>UIT</span>
            </button>
          ))}
        </div>
        <p className="cardMeta" style={{ marginTop: 12 }}>Gedimd blauw = programma UIT. Wanneer een programma actief is wordt de duidelijkere 70%-kleur gebruikt en toont de knop AAN.</p>
      </section>

      <section className="panel warning">
        <h2>STOP</h2>
        <p>STOP schakelt alle acht relais via het bestaande centrale STOP-command uit. Deze functie blijft onafhankelijk van de normale operationele opdrachten beschikbaar.</p>
        <p className="cardMeta">De STOP-knop wordt in de volgende stap aangesloten op dezelfde softwarematige STOP-functie die al op Hardware / Manual wordt gebruikt.</p>
        <button type="button" disabled style={{ ...controlButtonBase, width: "100%", marginTop: 12, background: "rgba(220, 38, 38, 0.70)" }}>STOP · alle relais UIT</button>
      </section>
    </main>
  );
}
