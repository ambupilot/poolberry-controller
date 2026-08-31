type LoginPageProps = {
  searchParams: Promise<{ error?: string; next?: string }>;
};

function safeNext(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const nextPath = safeNext(params.next);
  const hasCredentialError = params.error === "credentials";
  const hasConfigError = params.error === "config";

  return (
    <main className="loginShell">
      <section className="loginCard">
        <div>
          <p className="eyebrow">PoolBerry Control</p>
          <h1 className="loginTitle">Inloggen</h1>
          <p className="loginIntro">Log in om het PoolBerry-dashboard te openen.</p>
        </div>

        {hasCredentialError ? (
          <div className="loginError" role="alert">Gebruikersnaam of wachtwoord is onjuist.</div>
        ) : null}

        {hasConfigError ? (
          <div className="loginError" role="alert">Authenticatie is nog niet correct geconfigureerd op de server.</div>
        ) : null}

        <form method="post" action="/auth/login" className="loginForm">
          <input type="hidden" name="next" value={nextPath} />

          <label className="field">
            <span>Gebruikersnaam</span>
            <input
              type="text"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
              autoFocus
            />
          </label>

          <label className="field">
            <span>Wachtwoord</span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" className="primaryButton loginButton">Inloggen</button>
        </form>
      </section>
    </main>
  );
}
