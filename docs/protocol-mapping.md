# FLOP teaser profile mapping

## `flop-teaser-0.1`

Source: <https://flop.finance/teaser/>

Source version/status: `0.1` / `draft`

Source update date: 2026-08-26

Retrieval date: 2026-08-30

The teaser says its figures are provisional and the Yellow Paper is not final.
FlopBench therefore records these values as a sourced draft profile and does
not describe a readiness result as an official score or eligibility decision.

| Source wording | Normalized profile field | Stored value |
| --- | --- | ---: |
| 16 GB+ VRAM per unit | `miner.recommended_vram_bytes` | 17,179,869,184 bytes (16 GiB) |
| 8+ core CPU | `validator.recommended_cpu_cores` | 8 |
| 64 GB RAM | `validator.recommended_memory_bytes` | 68,719,476,736 bytes (64 GiB) |
| 2 TB NVMe | `validator.recommended_nvme_bytes` | 2,199,023,255,552 bytes (2 TiB) |
| 1 Gbps redundant connection | `validator.recommended_network_bits_per_second` | 1,000,000,000 bit/s |

RAM, VRAM, and storage recommendations are interpreted using binary capacity
units, consistent with the project charter. Network throughput is stored in
decimal bit/s. The original wording remains in the profile for auditability.
