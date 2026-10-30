# Parameterized scenic ribbon

Approved scope: extend the existing scenic-grid layout with bounded data parameters, implement the same contract in author tooling, provide a Ribbon example matching the reviewed prototype, and open paired implementation PRs. Do not add theme-specific branches or arbitrary author positioning/transforms. The user approved the parameter approach and requested implementation and both PRs on 2026-10-30.

## Contract

An optional `layout.ribbon` object is accepted only for fixed-column scenic-grid (`allowColumnOverride:false`). The compiler adds `ribbon-layout-v1`; the descriptor validator requires capability/options pairing. Existing themes without the object retain exact existing geometry and behavior. No component version bump is selected in an implementation PR. Capability negotiation rejects unsupported runtimes independently of the version floor.

Numeric fields (finite, integer except skewDeg and iconScale): left 64–640 (default112); right32–320 (112); bottom0–200 (162); cardHeight96–240 (128); gap0–64 (24); skewDeg -18–18 (0); focusLift0–64 (0); iconScale0.4–1 (1, fractional allowed). Enums: shortcuts header/bottom-left (header), edgeNavigation wrap/shortcuts (wrap), labels below/focused-above (below). showClock is boolean (true). Unknown fields reject. Below captions require bottom>=64. Bottom-left shortcuts require left>=340. The computed card width must be at least64. The geometry reserves the absolute horizontal skew extent at the largest focused height on both sides, caps card width at360, and derives all layout/hit areas from that same data.

The first Ribbon example uses left340,right84,bottom0,cardHeight180,gap0,skewDeg-13,focusLift36,iconScale0.65,shortcuts bottom-left,edgeNavigation shortcuts,labels focused-above,showClock false,columns8. The selected card grows by the lift amount and raises by the same amount. Its bottom remains aligned. Icons counter-skew without replacing image bytes. Focused captions remain visible. No webOS logo is included.

## Interaction and lifecycle

With edgeNavigation shortcuts, Left at app index0 selects Settings and resets the row to its start; successive Left selects Wi-Fi and Inputs. Right from Settings returns app0. Other ribbons preserve wrap. Inputs popup stays on screen above bottom controls. Pointer and wheel, app order, hold/reorder, settings suspension, theme reset and rollback remain functional. Native Home/emergency delivery and key-up handlers remain untouched.

## Tooling and installation

The toolkit verifies its exported runtime declares the new capability before compiling new options and verifies options/capability survive compilation. Stable runtime lock remains pinned to reviewed provenance. Explicit PR candidate exports are marked candidate and are never advertised as a stable runtime.

Installing a descriptor with ribbon-layout-v1 on a Home that supports themes but not this capability must fail descriptor validation before theme cache writes or selection/application. Existing installed theme and saved selection remain unchanged. A downgraded Home booting an already-selected unsupported theme follows its existing Classic recovery path. These are different cases and must be documented separately.

## Validation

Unit tests cover option bounds, capability pairing, default preservation and atomic state. Browser tests cover both editions, arbitrary alternate parameters, bounds and focus, shortcut/pointer/wheel navigation, reorder, overlays/suspension/reset and no page errors. Test an actual pre-change policy/data/manager with the new descriptor for URL and LAN installation: no store writes or visual/selection changes. Run repository regression script and toolkit suite. Record actual environment limits. No physical-TV acceptance is implied or performed by this task.
