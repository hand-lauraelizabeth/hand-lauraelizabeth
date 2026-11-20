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
