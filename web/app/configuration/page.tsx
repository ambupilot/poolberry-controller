import Link from "next/link";
import { revalidatePath } from "next/cache";

const API_URL = process.env.POOLBERRY_API_INTERNAL_URL ?? "http://api:8000";
const DEVICE_ID = process.env.POOLBERRY_DEVICE_ID ?? "poolberry-main-001";

type DeviceConfig = {
  device_id: string;
  flow_f1_pulses_per_liter: number;
  flow_f2_pulses_per_liter: number;
  filter_flow_safety_bypass: boolean;
  filter_min_flow_lph: number;
  filter_flow_grace_seconds: number;
  updated_at: string;
};

async function getConfig(): Promise<DeviceConfig | null> {
  try {
    const response = await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/config`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch { return null; }
}

async function saveConfig(formData: FormData) {
  "use server";
  const f1 = Number(formData.get("flow_f1_pulses_per_liter"));
  const f2 = Number(formData.get("flow_f2_pulses_per_liter"));
  const minFlow = Number(formData.get("filter_min_flow_lph"));
  const grace = Number(formData.get("filter_flow_grace_seconds"));
  const bypass = formData.get("filter_flow_safety_bypass") === "on";
  if (!Number.isFinite(f1) || !Number.isFinite(f2) || f1 <= 0 || f2 <= 0) return;
  if (!Number.isFinite(minFlow) || minFlow < 0 || !Number.isFinite(grace) || grace < 1) return;
  await fetch(`${API_URL}/internal/v1/devices/${DEVICE_ID}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      flow_f1_pulses_per_liter: f1,
      flow_f2_pulses_per_liter: f2,
      filter_flow_safety_bypass: bypass,
      filter_min_flow_lph: minFlow,
      filter_flow_grace_seconds: grace,
    }),
    cache: "no-store",
  });
  revalidatePath("/configuration"); revalidatePath("/");
}

export default async function ConfigurationPage() {
  const config = await getConfig();
  return (
    <main className="shell">
      <header className="topbar"><div><p className="eyebrow">PoolBerry Control</p><h1>Configuratie</h1></div><div className="topbarActions"><form method="post" action="/auth/logout"><button type="submit" className="logoutButton">Uitloggen</button></form></div></header>
      <nav className="tabs" aria-label="PoolBerry secties">
        <Link className="tab" href="/">Dashboard</Link><Link className="tab" href="/control">Bediening</Link><Link className="tab active" href="/configuration">Configuratie</Link><span className="tab disabled">Programma&apos;s</span><Link className="tab" href="/hardware">Hardware</Link><span className="tab disabled">Historie</span><span className="tab disabled">Events</span><span className="tab disabled">Systeem</span>
      </nav>
      {!config ? <section className="panel warning"><h2>Configuratie niet beschikbaar</h2><p>De webapp kan de actuele controllerconfiguratie niet ophalen.</p></section> : (
        <form action={saveConfig} className="configForm">
          <section className="panel">
            <h2>Flowmeters</h2>
            <p>Kalibratiefactor per flowmeter. De Pico haalt wijzigingen automatisch van de VPS op.</p>
            <label className="field"><span>F1 · pulsen per liter</span><input type="number" name="flow_f1_pulses_per_liter" min="0.001" step="0.001" defaultValue={config.flow_f1_pulses_per_liter} required /><small>F1 gebruikt GP17. Testmeter: 420 p/L, definitieve meter: 27 p/L.</small></label>
            <label className="field"><span>F2 · pulsen per liter</span><input type="number" name="flow_f2_pulses_per_liter" min="0.001" step="0.001" defaultValue={config.flow_f2_pulses_per_liter} required /><small>F2 gebruikt GP27.</small></label>
          </section>

          <section className="panel">
            <h2>Filterpomp · flowbeveiliging</h2>
            <p>Bij operationeel starten van de filterpomp controleert de Pico na de aanlooptijd de totale flow F1 + F2. Bij te weinig flow valt de volledige installatie lokaal terug naar fail-safe.</p>
            <label className="field" style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 12 }}>
              <input type="checkbox" name="filter_flow_safety_bypass" defaultChecked={config.filter_flow_safety_bypass} style={{ width: 18, height: 18 }} />
              <span>Flowbeveiliging OVERRIDE · testopstelling zonder waterflow</span>
            </label>
            <p className="cardMeta">LET OP: aangevinkt betekent dat de automatische flow-stop bewust is uitgeschakeld.</p>
            <label className="field"><span>Minimale totale flow F1 + F2</span><input type="number" name="filter_min_flow_lph" min="0" step="10" defaultValue={config.filter_min_flow_lph} required /><small>L/h. Wordt alleen toegepast wanneer de override uit staat.</small></label>
            <label className="field"><span>Aanlooptijd voor flowcontrole</span><input type="number" name="filter_flow_grace_seconds" min="1" max="120" step="1" defaultValue={config.filter_flow_grace_seconds} required /><small>Seconden na FILTERPOMP AAN voordat onvoldoende flow tot fail-safe leidt.</small></label>
          </section>

          <button type="submit" className="primaryButton">Configuratie opslaan</button>
        </form>
      )}
    </main>
  );
}
