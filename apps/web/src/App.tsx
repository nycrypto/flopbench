const plannedCapabilities = [
  "Readiness probe",
  "Inference benchmark",
  "Validator doctor",
  "Verifiable reports",
  "PoUI simulator",
] as const;

export function App() {
  return (
    <main>
      <p className="eyebrow">Stage 0 · Foundation</p>
      <h1>FlopBench</h1>
      <p className="lede">
        A local-first readiness and benchmarking workbench for future FLOP participants.
      </p>
      <aside aria-label="Project status">
        <strong>Independent community project.</strong> FlopBench is not an official FLOP
        Labs or Flop Foundation product, miner, validator client, eligibility checker, or
        claim tool.
      </aside>
      <section aria-labelledby="planned-heading">
        <h2 id="planned-heading">Planned capabilities</h2>
        <ul>
          {plannedCapabilities.map((capability) => (
            <li key={capability}>{capability}</li>
          ))}
        </ul>
      </section>
      <p className="status">No system scan or network request runs in this stage.</p>
    </main>
  );
}
