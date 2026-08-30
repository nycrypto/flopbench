# ADR 0005: User-selected dashboard theme

- Status: Accepted
- Date: 2026-08-31

## Decision

The functional Stage 7 dashboard will not begin with an automatically selected
visual theme or a generic generated dashboard template. Before visual design
work starts, the project owner will choose the theme direction from deliberate,
clearly differentiated options. Implementation will follow that choice while
preserving accessibility, responsive layout, and local-only security
requirements.

## Consequence

Stage 4–6 may define data and API behavior but must not silently lock in the
dashboard's visual language. Theme selection is a Stage 7 entry decision.
