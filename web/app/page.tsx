import Link from "next/link";

type DeviceStatus = {
  device_id: string;
  firmware_version: string;
  first_seen: string;
  last_seen: string;
  uptime_seconds: number;
  wifi_connected: boolean;
  status: "online" | "offline";
};

type Telemetry = {
  device_id: string;
  recorded_at: string;
  temperature_t1_c: number | null;
  temperature_t2_c: number | null;
  temperature_t3_c: number | null;
  temperature_t4_c: number | null;
  temperature_t5_c: number | null;
  temperature_t6_c: number | null;
  flow_f1_lph: number | null;
  flow_f2_lph: number | null;
};

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

const temperatureSensors = [
  { key: "temperature_t1_c" as const, id: "T1", role: "Buiten" },
  { key: "temperature_t2_c" as const, id: "T2", role: "Zwembad" },
  { key: "temperature_t3_c" as const, id: "T3", role: "Warmtepomp" },
  { key: "temperature_t4_c" as const, id: "T4", role: "Collector" },
  { key: "temperature_t5_c" as const, id: "T5", role: "Zwembad in" },
  { key: "temperature_t6_c" as const, id: "T6", role: "Binnen" },
];

function formatUptime(totalSeconds: number) {
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts = [];
  if (days) parts.push(`${days}d`);
  if (hours || days) parts.push(`${hours}u`);
  if (minutes || hours || days) parts.push(`${minutes}m`);
  parts.push(`${seconds}s`);
  return parts.join(" ");
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("nl-NL", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Europe/Amsterdam",
  }).format(new Date(value));
}

async function getDeviceStatus(): Promise<DeviceStatus | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch { return null; }
}

async function getLatestTelemetry(): Promise<Telemetry | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/telemetry/latest`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch { return null; }
}

export default async function Home() {
  const [device, telemetry] = await Promise.all([getDeviceStatus(), getLatestTelemetry()]);

  return (
    <main className="shell">
      <header className="topbar">
        <div><p className="eyebrow">PoolBerry Control</p><h1>Dashboard</h1></div>
        <div className="topbarActions">
          <div className={`statusBadge ${device?.status === "online" ? "online" : "offline"}`}>
            <span className="statusDot" />{device?.status === "online" ? "Online" : "Offline"}
          </div>
          <form method="post" action="/auth/logout"><button type="submit" className="logoutButton">Uitloggen</button></form>
        </div>
      </header>

      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab active" href="/">Dashboard</Link>
        <Link className="tab" href="/configuration">Configuratie</Link>
        <span className="tab disabled">Programma&apos;s</span>
        <span className="tab disabled">Hardware</span>
        <span className="tab disabled">Historie</span>
        <span className="tab disabled">Events</span>
        <span className="tab disabled">Systeem</span>
      </nav>

      {!device ? (
        <section className="panel warning"><h2>Controllerstatus niet beschikbaar</h2><p>De webapp kan momenteel geen actuele status ophalen uit de PoolBerry API.</p></section>
      ) : (
        <>
          <section className="grid">
            <article className="card primaryCard"><div className="cardLabel">Controller</div><div className="cardValue">{device.device_id}</div><div className="cardMeta">Hoofdcontroller</div></article>
            <article className="card"><div className="cardLabel">Firmware</div><div className="cardValue">{device.firmware_version}</div><div className="cardMeta">MicroPython edge firmware</div></article>
            <article className="card"><div className="cardLabel">Uptime</div><div className="cardValue">{formatUptime(device.uptime_seconds)}</div><div className="cardMeta">Sinds laatste herstart</div></article>
            <article className="card"><div className="cardLabel">WiFi</div><div className="cardValue">{device.wifi_connected ? "Verbonden" : "Niet verbonden"}</div><div className="cardMeta">Status volgens laatste heartbeat</div></article>
            <article className="card wide"><div className="cardLabel">Laatste heartbeat</div><div className="cardValue compact">{formatDateTime(device.last_seen)}</div><div className="cardMeta">Automatisch bijgewerkt door de hoofd-Pico</div></article>
          </section>

          <section className="panel">
            <h2>Temperaturen</h2>
            <p className="cardMeta">{telemetry ? `Laatste meting ${formatDateTime(telemetry.recorded_at)}` : "Nog geen temperatuurtelemetrie ontvangen"}</p>
            <div className="grid">
              {temperatureSensors.map((sensor) => {
                const value = telemetry?.[sensor.key] ?? null;
                return <article className="card" key={sensor.id}><div className="cardLabel">{sensor.id} · {sensor.role}</div><div className="cardValue">{value === null ? "—" : `${value.toFixed(1)} °C`}</div><div className="cardMeta">{value === null ? "Sensor niet aanwezig / geen geldige meting" : "Actuele 1-Wire meting"}</div></article>;
              })}
            </div>
          </section>

          <section className="panel">
            <h2>Flow</h2>
            <div className="grid">
              <article className="card"><div className="cardLabel">F1 · Flowmeter</div><div className="cardValue">{telemetry?.flow_f1_lph == null ? "—" : `${telemetry.flow_f1_lph.toFixed(0)} L/h`}</div><div className="cardMeta">GP17 · gekalibreerd via configuratie</div></article>
              <article className="card"><div className="cardLabel">F2 · Flowmeter</div><div className="cardValue">{telemetry?.flow_f2_lph == null ? "—" : `${telemetry.flow_f2_lph.toFixed(0)} L/h`}</div><div className="cardMeta">GP27 · gekalibreerd via configuratie</div></article>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
