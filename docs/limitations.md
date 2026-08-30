# Limitations

FlopBench is an independent community project and is not an official FLOP Labs or Flop Foundation product.

At the Stage 4 candidate:

- miner and validator readiness uses only the selected versioned source profile and explicitly labeled community checks;
- validator-doctor network tests measure TCP connection latency, jitter, and connection loss, not bandwidth;
- NTP and network results depend on the explicitly selected target and are not run by default;
- disk media type remains `unknown` when the operating system cannot provide a reliable answer;
- live AMD identification has a safe fallback; a native AMD provider is not yet implemented;
- no inference benchmark runs;
- no report, signature, DID receipt, or PoUI simulation is produced;
- no FLOP testnet or mainnet request is supported;
- no eligibility, airdrop score, token amount, reward, ROI, stake, wallet, claim, or real slashing behavior is provided.

The FLOP teaser is a draft and its parameters are provisional. The
`flop-teaser-0.1` profile records its source URL, retrieval date, status, and
raw-file content hash; this does not turn the values into official eligibility
criteria. Published contracts distinguish measured, reported, derived,
estimated, and simulated data. The Stage 3 runtime produces a local readiness
comparison, not a protocol participation or reward determination.
