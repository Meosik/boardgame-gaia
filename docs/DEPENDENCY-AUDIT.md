# Dependency Audit Status

Audit date: 2026-08-19

- `npm audit --omit=dev`: **0 vulnerabilities** in frontend runtime dependencies.
- Full frontend audit: **8 development-tool findings** (1 low, 2 moderate, 4 high, 1 critical), primarily in the Vite/Vitest toolchain.
- npm reports that fully resolving the remaining development findings requires major-version upgrades of Vite and Vitest.

Those major upgrades were not applied as part of the legacy-removal pass because they require a separately reviewed migration and browser/tooling regression run. Do not expose the development server to untrusted networks. The production bundle and combined Docker image build successfully.
