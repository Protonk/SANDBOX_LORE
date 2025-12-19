EntitlementJail.app

This directory contains a notarized macOS application bundle used to run a command under the App Sandbox. The sandbox restriction comes from the parent app’s `com.apple.security.app-sandbox = true` entitlement & subprocesses inherit those sandbox restrictions.

How to run:
  ./EntitlementJail.app/Contents/MacOS/entitlement-jail <command> [args...]

Notes:
- This bundle is a build artifact. Source + build/sign/notarize steps live in the [entitlement-jail repo](https://github.com/Protonk/entitlement-jail).
