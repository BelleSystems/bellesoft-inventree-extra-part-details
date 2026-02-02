# Bellesoft Extra Part Details

An **InvenTree** plugin that surfaces extra part details for Bellesoft AMS: aggregate purchase cost and stock quantities by status (OK / damaged) and by location, shown in a Part-detail panel and an optional dashboard item.

---

## What This Project Solves

InvenTree does not natively show, per part:

- **Total purchase cost** across all stock items (with optional fallback to internal price breaks)
- **Stock totals by status** (OK vs damaged)
- **Stock totals by location** (with OK/damaged breakdown per location)

This plugin computes those aggregates and exposes them in the InvenTree UI so operators and planners can see part-level totals without leaving the Part detail view.

---

## Intended Users and Systems

- **Users:** Operators and planners using InvenTree in a Bellesoft AMS context who need part-level cost and stock summaries.
- **System:** Runs inside an existing **InvenTree** instance as a plugin. Depends on InvenTree’s plugin framework, Django ORM, and frontend plugin UI contract.

---

## Installation

### InvenTree Plugin Manager

- Navigate to your InvenTree's **Admin Center** and go to the **Plugin Settings** view.
- Select **Install Plugin**
- Fill in the form and install.  
  **Package Name:** `bellesoft-extra-part-details`  
  **Source URL:** `git+https://github.com/BelleSystems/bellesoft-inventree-extra-part-details`
- Enable the plugin once installed.

### Command line

You may also install via terminal inside the InvenTree instance. 

```bash
pip install git+https://github.com/BelleSystems/bellesoft-inventree-extra-part-details
```

InvenTree will automatically detect it and show the plugin in the **Plugin Settings** view. Enable the plugin. No extra configuration is required for basic use.

---

## High-Level Architecture

| Layer | Responsibility |
|-------|----------------|
| **Plugin core** (`bellesoft_extra_part_details/core.py`) | InvenTree plugin class: mixins, settings, UI registration; computes part totals and stock/location data; builds panel and dashboard context. |
| **Frontend** (`frontend/`) | React/TypeScript UI: Part panel, dashboard item, settings page. Built with Vite; output is static JS in `bellesoft_extra_part_details/static/`. |
| **Static assets** (`bellesoft_extra_part_details/static/`) | Built JS/CSS and Vite manifest; served by InvenTree when loading plugin UI. |

**Boundary:** The backend owns all data and business logic (cost, stock, locations). The frontend only renders data passed in plugin context; it does not call InvenTree REST APIs for this feature.

---

## Main Execution and Data Flow

1. **Part detail page load**  
   InvenTree calls the plugin’s `get_ui_panels()` with `target_model="part"` and `target_id=<part_id>`.
2. **Backend computes context**  
   Plugin uses `part_total_purchase_cost()`, `part_total_stock()`, and `part_stock_by_location()` against Django ORM (Part, StockItem, StockLocation). It builds a single panel descriptor with a `context` dict (totals, currency, mixed-currency flag, locations_data).
3. **Frontend render**  
   InvenTree loads the plugin’s Panel entry from static (e.g. `Panel.js:renderPartTotalPricePanel`) and calls it with that context. The React panel renders tables and alerts; no further API calls.
4. **Dashboard**  
   For staff users, `get_ui_dashboard_items()` registers a dashboard widget; its React component currently shows placeholder content (counter, username).

---

## Key External Dependencies

| Dependency | Role |
|------------|------|
| **InvenTree** | Host app; plugin API, UI mixins, request/context. |
| **Django** | ORM (Part, StockItem, StockLocation, etc.). |
| **django-money (djmoney)** | `Money` type and currency for purchase/internal prices. |
| **@inventreedb/ui** | Frontend: `InvenTreePluginContext`, `checkPluginVersion`. |
| **React / Mantine** | UI framework and components; provided by InvenTree at runtime, not bundled. |
| **Vite** | Builds frontend to plugin `static/` with externals and entry-point exports. |

---

## Suggested Reading Order for New Developers

1. **README.md** (this file) — Problem, users, architecture, and flow.
2. **docs/ARCHITECTURE.md** — Layers, dependency direction, request lifecycle, where state and side effects live.
3. **docs/MODULES.md** — Why each package/module exists, what it owns vs delegates, how others use it.
4. **bellesoft_extra_part_details/core.py** — Plugin class and the three data methods; then `get_ui_panels` / `get_ui_dashboard_items`.
5. **docs/API.md** — Public methods and frontend entry points: purpose, caller responsibilities, guarantees, errors.
6. **frontend/vite.config.ts** and **frontend/src/Panel.tsx** — How the build is wired and how the panel consumes context.
7. **docs/DESIGN.md** — Constraints, tradeoffs, and known limitations.
8. [The InvenTree documentation](https://docs.inventree.org/en/stable/)
