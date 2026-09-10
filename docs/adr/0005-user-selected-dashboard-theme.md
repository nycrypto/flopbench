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

## Selected direction

The project owner selected a calm, concise working surface on 2026-09-10 and
subsequently chose Dashmin as a structural reference:

- light mode is the default and dark mode remains an explicit saved preference;
- one restrained orange family provides product identity, while green, amber,
  and red are reserved for semantic status;
- a compact left navigation, quiet top bar, pale canvas, and simple metric
  surfaces adapt the reference's useful hierarchy without copying its code,
  assets, or product-specific content;
- layouts favor a small number of clear surfaces, short labels, and information
  that is available without deep navigation;
- warnings state the affected resource and required action in one or two short
  sentences;
- decorative AI imagery, excessive gradients, and multi-color dashboard chrome
  are excluded.
- Turkish and English are first-class interface languages; the browser language
  selects the first visit and the user's explicit choice is saved locally.
