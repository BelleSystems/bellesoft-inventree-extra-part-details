# Architecture and Data Flow

This document describes the system’s major layers, dependency direction, typical request lifecycle, where state lives, and where side effects occur.

---

## Major Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  InvenTree host (Django app, plugin loader, UI shell)           │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         │ loads plugin                       │ serves static JS
         │ invokes get_ui_panels /            │ calls render*()
         │ get_ui_dashboard_items              │
         ▼                                    ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Plugin backend               │    │  Plugin frontend              │
│  bellesoft_extra_part_details │    │  frontend/src → static/       │
│  - BellesoftExtraPartDetails │    │  Panel, Dashboard, Settings   │
│  - part_total_* methods      │    │  (React, Mantine)             │
└──────────────────────────────┘    └──────────────────────────────┘
         │
         │ Django ORM
         ▼
┌──────────────────────────────┐
│  InvenTree / Django models    │
│  Part, StockItem, StockLocation│
└──────────────────────────────┘
```

- **Host:** InvenTree discovers the plugin via the `inventree_plugins` entry point, calls mixin methods with request/context, and serves plugin static assets. It also provides the React/Mantine runtime for the frontend.
- **Plugin backend:** Single plugin class; implements UI registration and three data methods. No HTTP views or URLs; no persistent state beyond what InvenTree and Django provide.
- **Plugin frontend:** React components built by Vite into the plugin’s `static/` directory. Renders only from context; no direct API calls for part totals.
- **Models:** All part/stock/location data comes from InvenTree’s Django models. The plugin does not define new models.

---

## Dependency Direction

- **InvenTree → Plugin backend:** Host imports the plugin class and calls `get_ui_panels`, `get_ui_dashboard_items`; backend uses InvenTree mixins and Django/InvenTree models.
- **InvenTree → Plugin frontend:** Host loads plugin JS and calls exported render functions with context. Frontend depends on `@inventreedb/ui` (context type, `checkPluginVersion`) and Mantine/React provided by the host.
- **Plugin backend → Frontend:** No Python→JS dependency. Backend only supplies a context dict and the name of the static entry (e.g. `Panel.js:renderPartTotalPricePanel`). Contract is the shape of the context and the export name.
- **Frontend → Backend:** No direct dependency. Data flows only via context passed by the host from backend to frontend.

No circular dependencies: host → backend → models; host → frontend (context from backend produced under host control).

---

## Typical Request / Event Lifecycle

**Part detail page (panel):**

1. User opens a Part detail page in InvenTree.
2. Host builds context (e.g. `target_model="part"`, `target_id=<id>`) and calls each plugin’s `get_ui_panels(request, context)`.
3. This plugin’s `get_ui_panels` checks `target_model == "part"` and `target_id`; then calls `part_total_purchase_cost(part_id)`, `part_total_stock(part_id)`, `part_stock_by_location(part_id)`.
4. Backend reads from Django ORM (Part, StockItem, StockLocation), builds the panel descriptor with a `context` dict, returns a one-element list.
5. Host renders the page; for this panel it loads the plugin’s Panel JS (from static) and calls `renderPartTotalPricePanel(pluginContext)` with the descriptor’s context.
6. React panel renders tables and alerts from context; no further requests.

**Dashboard:**

1. Staff user opens the dashboard. Host calls `get_ui_dashboard_items(request, context)`; plugin returns one item (source = Dashboard.js entry).
2. Host loads that entry and calls `renderPartTotalPriceDashboardItem(context)`. Frontend renders placeholder content. No part-specific data in context.

**Settings:**

1. Admin opens plugin settings. Host loads Settings.js and calls `renderPluginSettings(context)`. Placeholder UI only; no backend settings wired.

---

## Where State Lives

- **No plugin-owned persistent state.** The plugin does not add database tables or caches.
- **Request-scoped state:** The context dict built in `get_ui_panels` / `get_ui_dashboard_items` is created per request and passed to the frontend. The frontend may keep local React state (e.g. dashboard counter) but that is UI-only and not persisted.
- **Authoritative state:** Part, StockItem, StockLocation, and related data live in InvenTree’s database and are read through Django ORM. The plugin only reads; it does not write.

---

## Where Side Effects Occur

- **Backend:** Read-only ORM queries in the three `part_*` methods. No writes, no HTTP calls, no file I/O. `get_ui_panels` / `get_ui_dashboard_items` are pure given request/context (aside from DB reads).
- **Frontend:** Rendering only; no REST calls for part totals. User actions (e.g. settings button) may show notifications (Mantine) but do not call backend or persist settings in the current implementation.
- **Build time:** Vite writes JS and manifest into `bellesoft_extra_part_details/static/`. That is the only place the plugin “writes” outside of normal Django/InvenTree operation.

Summary: side effects are (1) DB reads in the plugin backend, and (2) static asset output from the frontend build. No plugin-initiated writes to DB or external services.
