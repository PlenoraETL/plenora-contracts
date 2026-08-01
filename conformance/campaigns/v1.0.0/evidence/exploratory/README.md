# Exploratory evidence — not release qualification

`fase0-2026-08-01.json` is a byte-for-byte preserved exploratory observation
copied from the original dirty Contracts checkout on 2026-08-01.

It is admissible as a blocker report because it records a reproduced failure on
`plenora-data-tools` revision
`7a47504482569636b6c0e268477d155010d3b030`, but it is **not** clean-room,
same-SHA qualification evidence and must never be promoted as such.

The blocking observation is:

```text
CRS_TYPE_UNSUPPORTED: tipo PROJJSON BoundCRS non supportato
```

The canonical campaign must regenerate `crs_wkt_towgs84` from Contracts and
reproduce the result against immutable inputs. A repaired candidate requires a
new version/tag/SHA; `v1.0.0` must not be moved or silently replaced.
