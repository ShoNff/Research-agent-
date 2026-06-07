import LogoutButton from "@/components/LogoutButton";
import PocCard from "@/components/PocCard";
import { POCS } from "@/lib/pocs";

export default function LauncherPage() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="lead">
          <h1>POC Launcher</h1>
          <p>Everything running behind the research agent, in one place.</p>
        </div>
        <LogoutButton />
      </header>

      {POCS.length === 0 ? (
        <div className="empty">
          No POCs yet. Add one in <code>lib/pocs.ts</code>.
        </div>
      ) : (
        <section className="grid">
          {POCS.map((poc) => (
            <PocCard key={poc.id} poc={poc} />
          ))}
        </section>
      )}

      <footer className="footer">Research Agent · private</footer>
    </main>
  );
}
