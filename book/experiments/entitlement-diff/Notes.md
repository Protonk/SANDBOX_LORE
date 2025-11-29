# Entitlement Diff – Notes

Use this file for dated, concise notes on signing, profile extraction, and probe runs.

## 2026-01-XX

- Added sample program `entitlement_sample.c` (binds to 127.0.0.1:56789) and built binaries `entitlement_sample` and `entitlement_sample_unsigned`.
- Created entitlements: `entitlements/network_server.plist` and `entitlements/none.plist`.
- Codesigned both binaries ad-hoc with respective entitlements (`codesign -s - --entitlements ...` succeeded).
- Extracted entitlements to `out/entitlement_sample.entitlements.plist` (contains `com.apple.security.network.server` true) and `out/entitlement_sample_unsigned.entitlements.plist` (empty dict).
- Runtime profile extraction and behavior probes not yet attempted; need to decide how to derive compiled profiles tied to these entitlements (app sandbox template or other pipeline) and a harness that can apply them.
