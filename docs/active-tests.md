# Active validator tests

Stage 4 active tests are opt-in. The CLI displays the exact disk limit, network
target, and data sent before asking for confirmation. `--approve` is the
non-interactive equivalent and still prints the plan before the operation
begins.

## Disk

- The default file size is 8 MiB and the hard maximum is 64 MiB.
- Runtime is limited to 30 seconds, with a 10-second default.
- A new `flopbench-*` temporary directory is created beneath the operating
  system temp directory or an explicitly selected parent.
- Symlink temp roots and paths that resolve outside the selected parent are
  rejected.
- The test file is opened exclusively and the whole directory is removed on
  success, error, duration limit, and cooperative cancellation.
- Throughput uses bytes per second. Latency p95 uses nearest rank.

## Network

The network adapter performs only bounded TCP connection setup to the exact
`host:port` supplied by the user. It sends no application payload, follows no
redirect, attempts at most 20 connections, and uses a maximum five-second
timeout per attempt. A completely unreachable target is `unknown`, not a fake
failure measurement. Jitter p95 uses nearest rank over adjacent successful
latency differences.

## Clock

The clock adapter sends one 48-byte UDP NTP query to the exact server selected
by the user. It does not retry or silently select another server. Missing,
short, or unreachable replies produce `unknown` rather than success.

Disk performance, jitter, packet-loss, and clock-offset classifications are
FlopBench community health guidance. They are not source-profile results or a
protocol score.
