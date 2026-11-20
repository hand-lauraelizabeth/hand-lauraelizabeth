# Transit Simulation Lab

Open `index.html` for browser-local flight, train, and submarine teaching models. Switch profiles, adjust controls, run/step/reset. Optionally load attributed OSM geography. The CSV track reader accepts UTC `time_iso,latitude,longitude,altitude_m` and optional `groundspeed_mps,heading_deg`; it never verifies the origin of uploaded data. Every simulator labels its limitations.

Run: `node tests.js`. Full model scope, safety boundary, licensing and integration plans: [Simulation Lab README](../README.md).

## Physics lessons (illustrative)

The extended flight model adds constant hypothetical wind vectors, ground-speed/ground-track readings distinct from air-relative speed, and approximate equivalent airspeed. The railway advisor compares station distance with a simplified full-service-brake distance plus a hypothetical response interval and margin. The submarine's requested ballast trim is approached at an illustrative finite pump rate. Imported CSV samples can be replayed by their original timestamps at accelerated viewing speed; missing positions are not interpolated or presented as observations. None of these models is calibrated for operational use.

## WordPress publishing safeguard

WordPress auto-paragraph formatting can silently insert `<p>` tags into raw inline JavaScript and stop initialization. **Do not paste the engine/app/enhancement source into page content.** After updating these source files, run `python scripts/build_simulation_loader.py transit` at the repository root (`SIMULATOR` is `chess` or `transit`) and embed the resulting single-line script after the tool's HTML shell, replacing the previous loader. It decodes the exact UTF-8 source in the browser and does not require an external network service. Never keep a second executable copy of the modules on the WordPress page. Purge the page cache and verify in an actual browser that the chessboard contains 64 squares or that Start advances the transit model. A valid source test alone does not validate WordPress's rendered output.

## Guided missions

The optional navigation exercise computes spherical great-circle distance and initial true bearing toward JFK/LaGuardia reference points (with cited public reference coordinates) or a user-defined geographic point. A steady-wind vector calculation estimates the idealized heading and along-course speed; it is not an operational flight plan and excludes airspace and obstructions. The rail exercise measures position and speed against a hypothetical station stopping band and simplified braking margin. The submarine exercise assesses a chosen depth and vertical-speed target. All missions use local simulation state events, explicitly distinguish imported positions, and avoid presenting model outputs as observations. Run `node projects/transit-lab/mission-tests.js`.

## Experiment studio and telemetry

The Experiment Studio adds three starting scenarios per simulated vehicle, local single-series telemetry charts and CSV export (simulated data only). Optional proportional heading assistance, a constant-brake station-stop assistant, and depth-control ballast feedback demonstrate control-system concepts. They are **not** aircraft autopilots, signaling/ATP, or submarine operating systems. Manual bank, brake, throttle or ballast input disengages the respective assistant. The active experimental controller changes the documented model inputs and is visibly identified, never silently alters observations. `node projects/transit-lab/experiment-tests.js` validates formulas and boundaries.

## Visual instrument layer (November 2026)

`visuals.js` enhances all three conceptual viewports with responsive SVG instrumentation. It renders **true airspeed, estimated groundspeed, model altitude, heading, ground track, flight-path-angle proxy and computed vertical speed** for flight; **cab-perspective schematic, speed, grade, station distance and ideal stopping cue** for trains; and **scalable depth ruler, target depth, hydrostatic pressure, modeled ballast trim and vertical rate** for the submarine. The aircraft viewport deliberately does not purport to display body pitch, an actual primary flight display, or outside terrain. Rail imagery is not a real route, and the submarine has no mapped bathymetry. Fast-reset controls are local and disengage experimental assistance through the usual input handlers. The viewport text and SVG aria labels accompany the visuals. No images, tracking data, credentials, or third-party front-end dependencies are used.

WordPress deployment uses the protected one-line generator at `scripts/build_simulation_loader.py transit`. Do not paste the module's raw source into a WordPress page: auto-paragraph formatting has previously broken the simulation. Load `visuals.js` after experiments, then `data-lab.js` and `operations.js` last. Run the visual regression tests and inspect the hosted page before claiming production success.

## Data Integration Lab (November 2026)

The browser can read an OpenSky-format JSON state-vector export, normalize aircraft time/position/ground velocity, offer a CSV export and transfer it to the flight-track viewer. It can also load a GTFS Schedule `shapes.txt` or GeoJSON LineString for a separate geographic route reference. A submarine-mode button makes an **opt-in** GEBCO_2026 WMS image request. These features do not create a live API connection or make the simulation vehicle-specific. See [DATA_INTEGRATIONS.md](DATA_INTEGRATIONS.md) for provenance rules, provider/licensing requirements, server architecture and browser QA criteria. Run `node projects/transit-lab/data-tests.js` for adapter tests.

## Operator training console (20 November 2026)

`operations.js` adds self-guided objectives for all modes: hold a specified true heading at low bank with a generic stall-speed margin; stop at a hypothetical station within ±15 m and below 0.5 m/s; and stabilize modeled submarine depth within ±5 m and 0.15 m/s for five simulated seconds. The console presents calculated performance margins, contextual alerts, progress, event history, and a local text debrief. It pauses assessment when imported observations are selected. These model-derived cues are not operational safety or navigation advice. Focus the panel and use **P** to start/pause, **.** to advance one second, and **R** to reset when no form control has focus. Run `node projects/transit-lab/operations-tests.js` for unit tests.

The animation loop now uses wall-clock deltas capped after browser stalls, rather than treating delayed timers as full simulation time. Terminal rail boundary stops are flagged as forced model boundaries, not successful platform stops. After code changes, regenerate the protected WordPress loader; repository changes alone do not update a WordPress page.

## Geographic imagery, historic profiles and environments (20 November 2026)

The geographic viewer now supports user-selected **USGS aerial orthophotography**, **USGS topographic mapping**, and **NASA Blue Marble (August 2004)** in addition to attributed OpenStreetMap. These provider maps are requested only when the user explicitly loads the real map. USGS coverage and image dates vary by region; NASA Blue Marble is a historical 500 m global composite and pixelates at street scale. No map layer represents a live camera or a satellite tracking the modeled vehicle.

Imported GTFS `shapes.txt` and GeoJSON LineString geometries can be displayed on the map. The 10 km hypothetical train run is **projected proportionally** along the selected geometry, not derived from actual agency timetable, rail grades, or train GPS. A geographic path is not sufficient for real operational physics.

Historically sourced controls include the **Douglas DC-3** (Smithsonian gross mass and top speed, Museum of Flight wing area), **PRR GG1** (ASME power and passenger-service speed), **USS Harder (Gato class)**, and **USS Nautilus (SSN-571)** (U.S. Naval History and Heritage Command displacement and speed references). These input limits are historical; aerodynamic thrust/drag coefficients, locomotive traction/braking, and underwater dynamics remain simplified and are not certified vehicle-specific simulation models.

The flight panel can explicitly request NOAA/NWS **recent surface winds** for JFK, LaGuardia or Newark, with observation timestamp and meteorological FROM direction converted to model TOWARD direction. It never assumes surface wind equals wind aloft and handles missing/stale observations. The underwater panel adds hypothetical freshwater, brackish and seawater densities to explore buoyancy/pressure while holding displaced volume constant.

Original sources and access terms:
- USGS imagery: https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer ; https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map
- USGS Topo: https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer
- NASA GIBS: https://nasa-gibs.github.io/gibs-api-docs/
- MTA GTFS: https://catalog.data.gov/dataset/mta-general-transit-feed-specification-gtfs-static-data
- NOAA/NWS API: https://www.weather.gov/documentation/services-web-api
- Smithsonian DC-3: https://airandspace.si.edu/collection-objects/douglas-dc-3/nasm_A19530075000 ; Museum of Flight: https://www.museumofflight.org/exhibits-and-events/aircraft/douglas-dc-3
- PRR GG1: https://www.asme.org/about-asme/engineering-history/landmarks/83-penn-rr-gg1-electric-locomotive-4800
- USS Harder: https://www.history.navy.mil/research/histories/ship-histories/danfs/h/harder-i.html
- USS Nautilus: https://www.history.navy.mil/research/histories/ship-histories/danfs/n/nautilus-ssn-571-iv.html

Run all existing regressions plus `node projects/transit-lab/historical-tests.js` and `node projects/transit-lab/geographic-tests.js`. The WordPress page embeds separate protected JavaScript loaders: repository commits do not automatically update the hosted version. Hosted browser QA must be explicitly performed, not inferred from source tests.

## Real terrain and railway geography challenges (20 November 2026)

**Flight: USGS 3DEP Elevation Point Query Service.** In flight mode, select *Survey terrain* to request up to three isolated ground elevations: the model's present position, and locations 2 and 5 km ahead of its modeled heading. The [official EPQS](https://epqs.nationalmap.gov/v1/docs) returns elevation in meters plus optional original source-data acquisition date. Failed samples are reported rather than fabricated. A visual marker chart and geographic map markers distinguish those measurements from the model's altitude. A nearby-point classroom challenge checks whether the *nominal* model altitude is at least 300 m above a measured grid point, and becomes unavailable once no sample is within 1.8 km. **This does not sample the entire path, include buildings/obstacles, resolve altitude datum differences, or certify any flight clearance.** USGS coverage is primarily US territory; requests are explicit and may be slow or blocked.

**Submarine: NOAA NCEI ETOPO 2022 numerical bathymetry.** In submarine mode, select *Survey seafloor* to query the [NOAA ERDDAP global 60 arc-second grid](https://oceanwatch.pifsc.noaa.gov/erddap/griddap/ETOPO_2022_v1_60s.html) at a simulated position. The sample is a numerical elevation, where below-zero values indicate bathymetry. Its grid is on the EGM2008 vertical reference; zero and positive elevations indicate unsuitable/non-underwater sample cells. Nominal model depth is compared to the sampled seabed with a 100 m classroom target; assessments expire at 1.8 km from the point. **ETOPO is coarse terrain, not detailed soundings, currents, shoals, charted navigable depths, or a collision system.** NOAA data are public and may be redistributed with their accuracy disclaimer.

**Rail: New York MTA Subway Service Lines.** A new *Load official route shapes* button retrieves [NY Open Data's published MTA service line GeoJSON](https://data.ny.gov/d/s692-irgq) (dataset ID `s692-irgq`, last updated December 8, 2025). It labels each available service and draws the selected real line segment on the opt-in Leaflet map. For a branching route, the module explicitly uses the longest contiguous published segment; this may omit other branches. It projects the existing 10 km simulated train run onto the published geographic length for **visual reference only**. It does not import schedules, station stops, signals, gradients, speed restrictions or observed train locations. If a network request fails, the existing local GTFS/GeoJSON importer is unchanged.

All requests are initiated by the user. Simulated coordinates, not device location, are sent to the respective public service. No credentials or authenticated private records are requested. The model state is made available to late-loaded source modules so survey buttons work before the first simulation step. Run additional deterministic tests: `node projects/transit-lab/terrain-tests.js` and `node projects/transit-lab/mta-tests.js`; all previous test suites must continue to pass. Browser live-provider response/CORS verification is independent from source and unit tests.

## Measured MTA line distances and published station locations (20 November 2026)

Transit Lab can now run its **hypothetical railway dynamics over the measured length of a published MTA service-line polyline**, rather than stretching a 10 km schematic over it. The *Load route shapes and stations* action explicitly requests two New York State Open Data sources:

1. [MTA Subway Service Lines](https://data.ny.gov/d/s692-irgq), including geometric route coordinates (dataset updated December 8, 2025).
2. [MTA Subway Stations](https://data.ny.gov/d/39hk-dx4f), including GTFS Stop ID, stop name, published weekday daytime routes, geographic station-centroid coordinates and structure type (updated November 19, 2026).

The `rail-geometry.js` matcher computes polyline distance with a spherical geodesic approximation, projects station centroids onto nearby line segments, requires a matching published daytime-service token, rejects centroids farther than **220 m** from the segment, then sorts results by computed distance. It never substitutes an invented stop if no station can be matched. Some published lines have multiple disconnected/branching segments: the existing route adapter selects the longest contiguous segment, so station matching is limited to that segment and other branches may be missing. A station *near* a service-line geometry is not proof that a particular train stops there, or that the station is physically on that operational track.

In the Railway mode, the model route length, cumulative distance, next station positions and terminal limit now reflect the chosen mapped segment. Station-stop missions, teaching-console targets and the optional braking assistant all use the same station distances. A compact route schematic and the geographic viewer show mapped station positions; the actual train movement remains the **simplified model**, not observed MTA vehicle position. When a local GTFS shape or GeoJSON line is imported without matching station data, the model uses that geometry's measured length and offers the segment end as a geographic stop exercise. Use *Return to generic 10 km track* to restore the original model.

**Important boundaries:** Published polyline length is a geographic approximation, *not surveyed rail chainage*. The station marker is a centroid projected to the nearest mapped line, not surveyed platform stopping distance. Speed ceilings, traction, adhesion, brake curves, gradients, signal and block systems, dwelling, service patterns, timetable adherence, dispatch and temporary restrictions remain illustrative or unimplemented. The [MTA Subway Schedules: 2026](https://data.ny.gov/d/g8es-h7gb) dataset exists, but this feature deliberately does not apply schedule times to these unmatched geographic segments. Real train movements and operating limits must not be inferred from these classroom exercises.

The data requests are initiated by the learner. The station dataset is small enough for direct bounded API fetches, and network failure leaves the existing locally importable GTFS/GeoJSON route mode available. No user location or credentials are requested. Source terms are not presumed waived for noncommercial use; source links and attribution accompany the UI.

Run `node projects/transit-lab/rail-geometry-tests.js` and `node projects/transit-lab/rail-model-tests.js` in addition to existing suites. Eleven source-level model/adapter/mission test modules passed a JS test harness (152 assertions). Runtime access to the external API, browser cross-origin behavior and visual QA remain separate validation tasks.
