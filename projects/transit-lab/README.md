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

WordPress deployment uses the protected one-line generator at `scripts/build_simulation_loader.py transit`. Do not paste the module's raw source into a WordPress page: auto-paragraph formatting has previously broken the simulation. Add `visuals.js` last, after experiments. Run the visual regression tests and inspect the hosted page before claiming production success.
