import { Poc, isLive } from "@/lib/pocs";

export default function PocCard({ poc }: { poc: Poc }) {
  const live = isLive(poc);

  const inner = (
    <>
      <div className="badge">{poc.emoji ?? "🚀"}</div>
      <h3>{poc.title}</h3>
      <p>{poc.description}</p>
      <span className={`pill ${live ? "live" : "soon"}`}>
        {live ? "Open ↗" : "Coming soon"}
      </span>
    </>
  );

  if (live) {
    return (
      <a className="card live" href={poc.href} target="_blank" rel="noreferrer">
        {inner}
      </a>
    );
  }

  return <div className="card disabled">{inner}</div>;
}
