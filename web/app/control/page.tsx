import Link from "next/link";

const commands = [
  { group: "Filterpomp", items: ["FILTERPOMP AAN", "FILTERPOMP UIT"] },
  { group: "Warmtepomp", items: ["WARMTEPOMP AAN", "WARMTEPOMP UIT"] },
  { group: "Collector", items: ["COLLECTOR OPEN", "COLLECTOR DICHT"] },
  { group: "Bronpomp", items: ["BRONPOMP AAN", "BRONPOMP UIT"] },
];

const programs = ["AUTO", "SPOELEN", "SPROEIEN"];

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
        <div className="grid">
          {commands.map((group) => (
            <article className="card" key={group.group}>
              <div className="cardLabel">{group.group}</div>
              <div style={{ display: "grid", gap: 10, marginTop: 16 }}>
                {group.items.map((command) => <button key={command} type="button" className="primaryButton" disabled>{command}</button>)}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Programma&apos;s</h2>
        <div className="grid">
          {programs.map((program) => (
            <article className="card" key={program}>
              <div className="cardLabel">Programma</div>
              <div className="cardValue">{program}</div>
              <button type="button" className="primaryButton" style={{ marginTop: 16 }} disabled>{program} starten</button>
            </article>
          ))}
        </div>
      </section>

      <section className="panel warning">
        <h2>STOP</h2>
        <p>STOP schakelt alle acht relais via het bestaande centrale STOP-command uit. Deze functie blijft onafhankelijk van de normale operationele opdrachten beschikbaar.</p>
        <p className="cardMeta">De STOP-knop wordt in de volgende stap aangesloten op dezelfde softwarematige STOP-functie die al op Hardware / Manual wordt gebruikt.</p>
        <button type="button" className="primaryButton" style={{ marginTop: 12 }} disabled>STOP · alle relais UIT</button>
      </section>
    </main>
  );
}
