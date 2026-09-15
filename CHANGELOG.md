# Changelog

All notable changes to PharmStock are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project uses date-based entries.

## [Unreleased]

## 2026-08-19 — Dispensing Integration Layer
### Added
- Read-only integration layer for ingesting dispense events and stock snapshots from external dispensing systems (TouchStore Rx / MPS)
- CSV import pipeline with schema validation, `event_id` deduplication, and quarantine of malformed rows
- Reconciliation engine comparing system on-hand vs source snapshots with configurable tolerance
- Data freshness / sync-status endpoint with staleness warning
- Import audit logging and quarantined-record review
- Frontend Data Import page (upload, import history, reconciliation, quarantined tabs)

## 2026-08-18 — Controlled Drugs Register, Reorder Engine & Risk Detection
### Added
- Pack-level stock tracking: `PackInstance` model with sealed/open/empty lifecycle
- FEFO dispensing service and `DispenseTransaction` model
- Write-off system with controlled-drug countersign workflow
- TouchStore Rx import and reconciliation endpoints
- Controlled Drugs Register (append-only entries, correction chain, running balance)
- Duty Register and CD destruction records with witness re-authentication and digital signature
- CD anomaly detection (dispensing spikes, repeated corrections, high supply ratios)
- Reorder recommendation engine (demand + safety stock, supplier grouping, CSV export)
- Dead-stock and demand-anomaly detection
- Stock value breakdown by category
- Frontend pages: Pack Inventory, Write-Offs, Reorder Recommendations, CD Register, Duty Register, CD Destruction
### Changed
- Prediction engine now uses pack-level on-hand quantities
- Merged pack expiry alerts into the Expiry Tracking page
- Predictions page lazy-loads with caching to avoid timeouts

## 2026-08-17 — User Authentication
### Added
- JWT-based authentication with bcrypt password hashing
- User roles: admin, staff, viewer
- Login page, protected routes, and auth context on the frontend
- All API routes gated behind a Bearer-token dependency

## Initial
### Added
- Core pharmacy stock prediction system: medicines, batches, sales, stock, expiry, predictions, alerts
- FastAPI backend with SQLAlchemy + SQLite
- React + Vite + Tailwind dashboard
