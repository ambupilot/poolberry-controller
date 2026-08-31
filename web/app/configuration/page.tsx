import Link from "next/link";
import { revalidatePath } from "next/cache";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

type DeviceConfig = {
  device_id: string;
  flow_f1_pulses_per_liter: number;
  flow_f2_pulses_per_liter: number;
  updated_at: string;
};

async function getConfig(): Promise<DeviceConfig | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/config`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

async function saveConfig(formData: FormData) {
  "use server";

  const f1 = Number(formData.get("flow_f1_pulses_per_liter"));
  const f2 = Number(formData.get("flow_f2_pulses_per_liter"));

  if (!Number.isFinite(f1) || !Number.isFinite(f2) || f1 <= 0 || f2 <= 0) {
    return;
  }

  await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      flow_f1_pulses_per_liter: f1,
      flow_f2_pulses_per_liter: f2,
    }),
    cache: "no-store",
  });

  revalidatePath("/configuration");
  revalidatePath("/");
}

export default async function ConfigurationPage() {
  const config = await getConfig();

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PoolBerry Control</p>
          <h1>Configuratie</h1>
        </div>
        <div className="topbarActions">
          <form method="post" action="/auth/logout"><button type="submit" className="logoutButton">Uitloggen</button></form>
        </div>
      </header>

      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab" href="/">Dashboard</Link>
        <Link className="tab active" href="/configuration">Configuratie</Link>
        <span className="tab disabled">Programma&apos;s</span>
        <span className="tab disabled">Hardware</span>
        <span className="tab disabled">Historie</span>
        <span className="tab disabled">Events</span>
        <span className="tab disabled">Systeem</span>
      </nav>

      {!config ? (
        <section className="panel warning">
          <h2>Configuratie niet beschikbaar</h2>
          <p>De webapp kan de actuele controllerconfiguratie niet ophalen.</p>
        </section>
      ) : (
        <section className="panel">
          <h2>Flowmeters</h2>
          <p>Kalibratiefactor per flowmeter. De Pico haalt wijzigingen automatisch van de VPS op.</p>

          <form action={saveConfig} className="configForm">
            <label className="field">
              <span>F1 · pulsen per liter</span>
              <input
                type="number"
                name="flow_f1_pulses_per_liter"
                min="0.001"
                step="0.001"
                defaultValue={config.flow_f1_pulses_per_liter}
                required
              />
              <small>F1 gebruikt GP17. Testmeter: 420 p/L, definitieve meter: 27 p/L.</small>
            </label>

            <label className="field">
              <span>F2 · pulsen per liter</span>
              <input
                type="number"
                name="flow_f2_pulses_per_liter"
                min="0.001"
                step="0.001"
                defaultValue={config.flow_f2_pulses_per_liter}
                required
              />
              <small>F2 gebruikt GP27.</small>
            </label>

            <button type="submit" className="primaryButton">Configuratie opslaan</button>
          </form>
        </section>
      )}
    </main>
  );
}
