# Local API composition root

The Stage 7 FastAPI composition root lives in `src/flopbench/webapp.py` so it is
included in the Python package. Domain models and services remain in their
existing `src/flopbench` modules. This directory documents the boundary; API
wiring is limited to loopback security controls and static dashboard
integration.
