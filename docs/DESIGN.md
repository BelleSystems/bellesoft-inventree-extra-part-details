# Design Decisions and Tradeoffs

This document explains non-obvious or intentional design choices, constraints, tradeoffs, known limitations, and expectations for future changes.

---

## Constraints That Influenced the Design

1. **InvenTree plugin contract:** The plugin must register via `inventree_plugins` entry point, use specific mixins (`SettingsMixin`, `UserInterfaceMixin`), and expose UI via `get_ui_panels` / `get_ui_dashboard_items`. No custom URLs or views are required for the current feature set.
2. **Host-provided runtime:** Frontend runs inside InvenTree’s React/Mantine environment. React, ReactDOM, Mantine, and (optionally) Lingui must be externalized so the host supplies them at runtime; the plugin bundle must not ship its own copies.
3. **Context-only data flow:** The panel is designed to receive all data in the initial context from the backend. This avoids extra REST calls and keeps the host in control of when and how plugin UI is rendered.
4. **Single part scope:** The panel is tied to the Part detail page (`target_model="part"`, `target_id`). There is no “global” or multi-part view in the current design.

---

## Tradeoffs and Alternatives

**Computed data in backend vs REST API**

- **Chosen:** Backend computes totals and stock-by-location in `get_ui_panels` and passes a single context dict. Frontend only renders.
- **Alternative:** Expose a REST endpoint (e.g. `/api/plugin/part-total-price/<part_id>/`) and have the frontend fetch when the panel mounts.
- **Reason:** Context-injection keeps the host’s rendering model simple (one pass, no async loading for this panel), avoids CORS and auth concerns for a separate API, and matches the pattern used by the InvenTree plugin UI docs. Tradeoff: panel data is fixed at page load; refreshing requires reloading the page.

**Merge duplicate locations in Python vs SQL**

- **Chosen:** `part_stock_by_location` uses Django `annotate`/`Sum` then merges duplicate location rows in Python (see comment in `core.py` about “multiple rows per location due to joins/annotations upstream”).
- **Alternative:** More complex SQL or subqueries to guarantee one row per location.
- **Reason:** Correctness and maintainability were prioritized; the current approach explicitly documents the duplication and centralizes the merge in one place. Tradeoff: slightly more memory and CPU for large part/location sets.

**Mixed-currency handling**

- **Chosen:** When multiple currencies appear across stock items, the backend sets `mixed_currency=True` and stops accumulating (partial sums may be returned). Frontend shows a “Mixed currencies detected” message.
- **Alternative:** Convert all to a base currency using a rate table; or sum per currency and show a breakdown.
- **Reason:** Avoids implicit conversion and wrong totals without a defined policy. Tradeoff: user does not get a single total when currencies are mixed; they must fix data or accept partial/separate display.

**Dashboard and settings as placeholders**

- **Chosen:** Dashboard and settings components are implemented but show placeholder content (counter, “Hello World”). No part-level data in dashboard context; no plugin settings persisted.
- **Alternative:** Omit dashboard/settings until needed; or implement full behavior from the start.
- **Reason:** Plugin template/structure supports all three UI extension points; keeping placeholders allows consistent build and registration while deferring product decisions (e.g. what the dashboard should show, what settings to expose).

---

## Risks and Known Limitations

1. **No `Part.DoesNotExist` handling in data methods:** `part_total_purchase_cost`, `part_total_stock`, and `part_stock_by_location` use `Part.objects.get(id=part_id)`. Invalid `part_id` raises `Part.DoesNotExist`. Callers (`get_ui_panels`) do not catch it; a bad or stale context could yield a 500. **Mitigation:** Ensure the host only calls with valid part IDs, or add try/except and return empty/safe context.
2. **Locale loading not wired:** `frontend/src/locale.tsx` imports `./locales/${locale}/messages.ts`. The repo has no `locales/` directory, so any component that uses this will fail at runtime until locales are added or the import is removed/guarded.
3. **Panel data is snapshot-only:** Totals and stock-by-location reflect the moment the page was loaded. If stock or prices change (e.g. another user or an external system), the user must reload the Part page to see updates.
4. **Externalized frontend deps:** Correct behavior depends on the host providing compatible versions of React, Mantine, and `@inventreedb/ui`. Version skew could cause runtime errors; `checkPluginVersion` is intended to help but may not cover all cases.

---

## Future Refactoring Expectations

- **Backend:** The three data methods are good candidates for unit tests and, if needed, for extraction into a small “service” or helper module to keep `core.py` focused on plugin registration and UI wiring. Any new REST endpoints would be a separate, intentional addition.
- **Frontend:** Panel context shape is the main contract. If new fields are added (e.g. extra breakdowns), they should be backward-compatible (optional keys) or versioned so old builds still work with newer backends.
- **Dashboard/Settings:** When requirements are clear, dashboard context could be extended (e.g. global or filtered part summaries), and settings could be wired to `SETTINGS` and `get_settings_dict()` with corresponding UI.
- **Locales:** Either add `frontend/src/locales/` and message files, or remove/guard the dynamic import in `locale.tsx` to avoid runtime errors.

---

## Assumptions Stated Explicitly

- InvenTree’s `Part`, `StockItem`, and `StockLocation` models (and their relations and fields) behave as used in the code; e.g. `part.stock_items`, `item.purchase_price`, `part.internal_price_breaks`, `part.total_stock`, and `StockStatus` values are as expected.
- The host always passes a dict-like `context` with `target_model` and `target_id` when rendering the Part detail page; `target_id` is the part primary key.
- `djmoney` is available and `Money` and currency handling are as used (e.g. `price.currency`, `price * quantity`).
- Plugin static files are served under the plugin’s static URL path and the host can load and execute the built JS and call the exported functions with the given names.
- The repository name “PartTotalPrice” and the plugin title “Bellesoft Extra Part Details” both refer to the same deliverable; “Bellesoft AMS” is the intended deployment context.
