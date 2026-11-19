# Data integrations — provenance, security, and release gates

The Transit Simulation Lab now has a separate **Data Integration Lab** with no always-on remote connections. This document differentiates implemented imports from planned provider connectors.

## Integration status (19 November 2026)

| Source | Implemented now | Still required |
| --- | --- | --- |
| OpenSky Network REST | Browser-local import of one or several OpenSky-format JSON snapshots, selection by ICAO24, timestamp normalization, altitude type disclosure, optional conversion to the existing flight-track reader and CSV export | Authenticated server adapter using OAuth2 client credentials; usage authorization and limits; request caching, stale-data handling, per-aircraft sequencing and audited server logs |
| Flightradar24 API | Documented provider path and normalized track schema shared with other aircraft providers | Paid/licensed API access; server-kept token; permitted caching/display, attribution, terms review and reliable error states |
| GTFS Schedule / GeoJSON | Browser-local GTFS `shapes.txt` and GeoJSON LineString import, route selection, geographic geometry/length rendering | Agency-sourced feeds, stop-to-shape matching, validated train speed profiles, route grades, signaling and platform coordinates |
| GTFS Realtime | Reference to VehiclePositions protobuf fields and data-age requirements | Authorized feed, server-side protobuf decoding, source version validation, stop/shape correlation, timestamps and operator attribution |
| GEBCO_2026 WMS | Explicit, opt-in WMS GetMap of shaded regional bathymetry, with source link and caution | If used for interaction, sampled numeric depth coverage, resolution/source-quality metadata and validated collision logic — not provided by a WMS image |
| Google Maps Tiles / Photorealistic 3D | Roadmap references only | Billing, restricted project credentials, compliant 3D Tiles renderer, geographic coverage checks, per-tile attribution aggregation, usage limits and terms review |

## Browser UX: provenance boundaries

1. **Observed reference**: Input data stays in the browser until the user explicitly elects to load a third-party map. Files are not uploaded. The original filename alone does not prove provider origin.
2. **Calculated**: Haversine route distance and normalization of WGS84 latitude/longitude. Route distance approximates geometry and is not train odometry or verified geographic clearance.
3. **Simulated**: All aircraft, train and submarine motion derived from generic vehicle models. Using an imported flight location initializes a new hypothetical trajectory. An imported ground-velocity report is not treated as airspeed.
4. **External geographic imagery**: GEBCO WMS is a real map image, not a depth reading. It must not be used to assess safe submarine depth or collision clearance. There is no imagery fetch before user action.

## Normalized data contract for a future backend

A server adapter should return JSON with a stable schema, for example:

```json
{
  "kind": "aircraft_position",
  "source": "opensky",
  "source_version": "api-v1.4",
  "license_ref": "provider-terms-link",
  "observed_at": "2026-11-19T19:00:00Z",
  "received_at": "2026-11-19T19:00:03Z",
  "position": { "latitude_deg": 40.7, "longitude_deg": -73.9, "altitude_m": 1280, "altitude_type": "geometric" },
  "velocity": { "groundspeed_mps": 94, "ground_track_deg": 75 },
  "quality": { "verified_provider": true, "stale": false, "has_position": true }
}
```

The values above are synthetic schema examples, not observations. The backend must never invent missing values or silently convert barometric to geometric altitude, a ground track to a heading, or ground velocity to true airspeed.

### Server-side architecture (proposed, not deployed)

- Keep OpenSky OAuth2 client ID/secret and Flightradar24 API token in server-side secrets, **never** WordPress HTML, GitHub commits, JavaScript bundle, local storage, or browser URLs.
- Add one authenticated or rate-limited WordPress/serverless endpoint with strict geographic bounding boxes, rate limiting, per-source caching, and explicit failure responses: no token (disabled), 401/403 (auth), 429 (quota), provider timeout, stale result.
- Use provider-specific server adapters that emit the normalized contract and attach source attribution and allowed-use metadata.
- Respect provider API policies on caching, republication, and historical retention. Refresh observed data according to provider limits; no automatic public live refresh until the terms are verified.
- Validate observed and received timestamps; mark data **stale** rather than displaying it as a live state. For GTFS Realtime, follow best practices: vehicle positions are expected to be recent (typically under 90 seconds) and feed refresh around 30 seconds.
- Separate model time from wall-clock observation time. If the user hands off from an observation to a model, the label immediately changes to “simulated from a reference point.”
- Log only aggregate technical failures by default, not entire personal tracks, imported files, or private credentials.
- For 3D Tiles, use a licensed renderer that meets Google's attribution requirements; do not scrape or embed Google Earth imagery.

## Browser integration tests

```bash
node projects/transit-lab/tests.js
node projects/transit-lab/mission-tests.js
node projects/transit-lab/experiment-tests.js
node projects/transit-lab/visual-tests.js
node projects/transit-lab/data-tests.js
```

Also test in a hosted mobile browser: (1) viewport and Start/Pause, (2) a valid multi-snapshot OpenSky-format JSON and a malformed file, (3) one-snapshot handoff, (4) GTFS shapes and GeoJSON, (5) opt-in GEBCO map and provider failure, (6) switching modes without losing simulation controls, (7) CSV export, (8) no outbound requests before requesting the external map. Do not claim this browser QA is complete until actually performed.

## Sources and terms reviewed

- OpenSky REST API: https://openskynetwork.github.io/opensky-api/rest.html
- Flightradar24 API: https://fr24api.flightradar24.com/docs/getting-started
- GTFS Schedule reference: https://gtfs.org/documentation/schedule/reference/
- GTFS Realtime reference and best practices: https://gtfs.org/documentation/realtime/reference/ and https://gtfs.org/documentation/realtime/realtime-best-practices/
- GEBCO WMS: https://www.gebco.net/data-products/gebco-web-services/web-map-service
- Google Maps Tiles API: https://developers.google.com/maps/documentation/tile/
