# Transit Simulation Lab

Open `index.html` for browser-local flight, train, and submarine teaching models. Switch profiles, adjust controls, run/step/reset. Optionally load attributed OSM geography. The CSV track reader accepts UTC `time_iso,latitude,longitude,altitude_m` and optional `groundspeed_mps,heading_deg`; it never verifies the origin of uploaded data. Every simulator labels its limitations.

Run: `node tests.js`. Full model scope, safety boundary, licensing and integration plans: [Simulation Lab README](../README.md).

## Physics lessons (illustrative)

The extended flight model adds constant hypothetical wind vectors, ground-speed/ground-track readings distinct from air-relative speed, and approximate equivalent airspeed. The railway advisor compares station distance with a simplified full-service-brake distance plus a hypothetical response interval and margin. The submarine's requested ballast trim is approached at an illustrative finite pump rate. Imported CSV samples can be replayed by their original timestamps at accelerated viewing speed; missing positions are not interpolated or presented as observations. None of these models is calibrated for operational use.

## WordPress publishing safeguard

WordPress auto-paragraph formatting can silently insert `<p>` tags into raw inline JavaScript and stop initialization. **Do not paste the engine/app/enhancement source into page content.** After updating these source files, run `python scripts/build_simulation_loader.py transit` at the repository root (`SIMULATOR` is `chess` or `transit`) and embed the resulting single-line script after the tool's HTML shell, replacing the previous loader. It decodes the exact UTF-8 source in the browser and does not require an external network service. Never keep a second executable copy of the modules on the WordPress page. Purge the page cache and verify in an actual browser that the chessboard contains 64 squares or that Start advances the transit model. A valid source test alone does not validate WordPress's rendered output.
