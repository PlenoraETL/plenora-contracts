# Qualified-release campaign evidence

These reports were produced from immutable component release revisions pinned by
`execution.json`. “Qualified” describes the component inputs; it does **not**
mean that every system-level gate is satisfied.

## Results

- isolated component checks: 90/90;
- IO → Data → Database observer chain: 30/30;
- IO → Data and Data → IO pairwise rewrite orders: 30/30;
- EPSG:3003/TOWGS84 canonical and GeoArrow variants: pass;
- required conflicting-CRS transitions: observed with no residual loss.
- live PostgreSQL → Database → Data → IO read/export chain: pass within its
  declared non-persistence scope;
- read-only Plenora ↔ Data filter/reprojection comparison: pass with declared
  physical Arrow differences.

## Boundary

Database `inspect-dataset` is a contract observer. It does not demonstrate
prepare/write/commit/durability/readback. Native Windows and live database
provider persistence is not established by the isolated reports. The separate
live PostgreSQL report proves read/export and rewrite, not database write or
durable readback. The Plenora comparison proves only the two named common
operations, not provider or operational parity. Those gaps remain
machine-readable in the reports, `2026-08-01-provenance.json`, and the campaign
manifest.

The runner snapshot and report SHA-256 digests are recorded in the provenance
file. The reports are preserved byte-for-byte from the container output.
