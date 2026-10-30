# Legacy TV WebSocket client

Vendored from the npm `ws@6.2.4` archive (MIT), SHA-1
`d80bd7adbe495d8f4ff55d3a23a274740fcfc903`. This branch includes upstream
payload, fragment and buffered-chunk limits. Helper selects it below Node 10;
the modern path continues to use ws 8.21.0.

Local changes:

- `lib/validation.js` comes from `ws@7.5.11` (MIT, SHA-1
  `9460daf1812bb81a423c5b9eac746941a86310fa`), preserving pure JavaScript UTF-8
  validation when the optional native addon is absent.
- `async-limiter@1.0.1` (MIT, SHA-1
  `dd379e94f0db8310b08291f9d64c3209766617fd`) is vendored as
  `lib/async-limiter.js`; its import is relative and its license is included.
- Import `events.EventEmitter` explicitly: Node 0.10 exports an object rather
  than the constructor directly. Skip optional `cork`/`uncork` write batching on
  Node 0.10 TLS streams, retaining both writes and the completion callback.

Upstream targets newer Node. Our Node 0.10.25+ compatibility comes from the Helper
Babel/core-js/safe-buffer build and runtime regression, not an upstream claim.
SSAP clients disable compression and enforce payload/handshake limits. They
connect only to the TV's own LAN addresses. No WebSocket server is started by
Helper; the server export is exercised by the local protocol regression only.
