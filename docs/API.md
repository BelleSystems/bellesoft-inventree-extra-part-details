# Interface and API Documentation

This document covers the plugin’s public interfaces: the backend plugin class and its methods, and the frontend entry points the host calls. It describes intent, caller responsibilities, return guarantees, and failure conditions.

---

## Why These Abstractions Exist

- **Backend:** InvenTree’s plugin system expects a single plugin class and specific mixin methods (`get_ui_panels`, `get_ui_dashboard_items`). The three data methods exist to keep aggregation logic testable and reusable and to supply a single context dict to the UI.
- **Frontend:** InvenTree loads plugin UI by script URL and calls a single exported function per view (panel, dashboard, settings). Those exports are the only contract between the host and the plugin UI.

**Stability expectations:**

- **Stable:** Plugin class name and entry point; names and signatures of the exported frontend functions (`renderPartTotalPricePanel`, etc.); the fact that context is a dict keyed by strings. Backend method *names* and the *shape* of the context dict (e.g. `total_price`, `locations_data`) should change only with a clear migration path for the frontend.
- **May change:** Internal implementation of the three data methods; exact keys inside `locations_data`; placeholder content of dashboard and settings; formatting and layout in the UI.

---

## Backend: `BellesoftExtraPartDetails`

Defined in `bellesoft_extra_part_details/core.py`. Subclasses `InvenTreePlugin` with `SettingsMixin` and `UserInterfaceMixin`.

---

### `part_total_purchase_cost(self, part_id: int)`

**Purpose:** Compute aggregate purchase cost for all stock items of the given part, split by status (OK vs damaged), and detect mixed currencies.

**Behavior:**

- Iterates over `StockItem` for `part_id`.
- Uses each item’s `purchase_price`. If missing and the part has internal price breaks, uses internal price (first break’s currency).
- Sums `price * quantity` per item; separates OK vs damaged via `StockStatus`.
- If any two items use different currencies, sets `mixed_currency` and returns partial sums (implementation stops accumulating on first mixed pair).

**Returns:** A 5-tuple:

- `total`: `Money` sum of all items, or `None` if no prices.
- `ok_total`: `Money` sum for status OK, or `None`.
- `damaged_total`: `Money` sum for status DAMAGED, or `None`.
- `currency`: currency code (e.g. from first `Money`), or `None`.
- `mixed_currency`: `True` if more than one currency was seen.

**Caller responsibilities:** Call only with a valid `part_id` that exists. Caller must handle `Part.DoesNotExist` if `Part.objects.get(id=part_id)` is used (currently the method does not catch it).

**Failure/errors:** `Part.DoesNotExist` if `part_id` is invalid. No explicit handling for missing or invalid `StockItem` or price data; missing prices are skipped.

---

### `part_total_stock(self, part_id: int)`

**Purpose:** Return total stock quantity for the part and the same quantity broken down by OK and damaged status.

**Behavior:** Uses Django aggregates on `part.stock_items` for `Sum("quantity")` with filters for `StockStatus.OK` and `StockStatus.DAMAGED`; reads `part.total_stock` for overall total.

**Returns:** A 3-tuple: `(total_stock, ok_stock, damaged_stock)`. Numeric; `None` from aggregate is converted to 0 for OK/damaged.

**Caller responsibilities:** Pass a valid `part_id`; handle `Part.DoesNotExist` if applicable.

**Failure/errors:** `Part.DoesNotExist` if part does not exist. No other exceptions documented.

---

### `part_stock_by_location(self, part_id: int)`

**Purpose:** Return per-location stock totals (total, OK, damaged) for the part, with location metadata (name, path).

**Behavior:**

- Annotates `part.stock_items` with `Sum` by `location` and status (OK/damaged).
- Merges duplicate location rows in Python (invariant: one entry per location in the result).
- Builds a dict keyed by location id (or `"no_location"` for null location). Each value includes `location_id`, `location_name`, `location_path`, `total`, `ok`, `damaged`. Missing locations are reported as `"Location {id} (deleted)"`.

**Returns:** `dict[str, dict]` — keys are string location id or `"no_location"`; values are the location payload dicts above.

**Caller responsibilities:** Pass a valid `part_id`. Handle deleted locations (name/path are replaced with a placeholder string).

**Failure/errors:** `Part.DoesNotExist` for invalid part. `StockLocation.DoesNotExist` is caught and replaced with a placeholder row.

---

### `get_ui_panels(self, request, context: dict, **kwargs)`

**Purpose:** Return the list of custom UI panels for the current request/context (e.g. Part detail page).

**Behavior:** If `context["target_model"] != "part"` or `context["target_id"]` is missing, returns `[]`. Otherwise computes part totals and stock/location data, then returns a one-element list describing the “Part Total Price” panel: key, title, description, icon, `source` (plugin static entry), and a `context` dict for the frontend.

**Returns:** List of panel descriptor dicts. Each has `key`, `title`, `description`, `icon`, `source`, `context`. The `context` dict includes `total_price`, `ok_total_price`, `damaged_total_price`, `total_stock`, `ok_stock`, `damaged_stock`, `currency`, `mixed_currency`, `locations_data`, `settings`.

**Caller responsibilities:** InvenTree calls this with the appropriate request and context. Plugin assumes `target_model` and `target_id` are set when the target is a part.

**Failure/errors:** Same as the three data methods (e.g. `Part.DoesNotExist`). No explicit try/except in `get_ui_panels`.

---

### `get_ui_dashboard_items(self, request, context: dict, **kwargs)`

**Purpose:** Return the list of custom dashboard items (e.g. for the home dashboard).

**Behavior:** If the user is not staff, returns `[]`. Otherwise returns a one-element list with key, title, description, icon, `source` (Dashboard.js entry), and `context` (currently only `settings`).

**Returns:** List of dashboard item descriptor dicts. Context does not include part-level data.

**Caller responsibilities:** InvenTree calls this; no specific caller contract beyond the usual request object.

**Failure/errors:** None documented; relies on request and optional `request.user`.

---

## Frontend: Entry Points

InvenTree loads the plugin’s JS and calls one function per view, passing a single argument: the **plugin context** (object with at least `context`, and possibly `plugin`, `user`, etc. as per InvenTree docs).

---

### `renderPartTotalPricePanel(context: InvenTreePluginContext)`

**Purpose:** Render the Part Total Price panel on the Part detail page.

**Behavior:** Calls `checkPluginVersion(context)`. Reads from `context.context`: `total_price`, `ok_total_price`, `damaged_total_price`, `currency`, `mixed_currency`, `total_stock`, `ok_stock`, `damaged_stock`, `locations_data`. Sorts locations (e.g. “No Location” last) and renders tables and alerts. No async or API calls.

**Caller responsibilities:** InvenTree must pass the context produced by `get_ui_panels()` for the Part Total Price panel. Context keys must match what the panel expects (see MODULES.md / core.py).

**Return guarantee:** Returns a React element (or fragment). No thrown errors documented; missing or malformed context may render “None” or empty values.

**Failure/errors:** If `checkPluginVersion` fails, behavior is defined by `@inventreedb/ui`. Missing keys in `context.context` may cause `undefined` display or runtime errors.

---

### `renderPartTotalPriceDashboardItem(context: InvenTreePluginContext)`

**Purpose:** Render the plugin’s dashboard widget.

**Behavior:** Calls `checkPluginVersion(context)` and renders a simple grid (placeholder: plugin name, username, counter). No part data.

**Caller responsibilities:** InvenTree passes dashboard context; no part-specific keys required.

**Return guarantee:** Returns a React element.

**Failure/errors:** Same as above for `checkPluginVersion` and missing context.

---

### `renderPluginSettings(context: InvenTreePluginContext)`

**Purpose:** Render the plugin’s custom settings block in the plugin admin UI.

**Behavior:** Renders a placeholder alert and button. No persistence.

**Caller responsibilities:** InvenTree passes settings context (e.g. from `get_settings_dict()` if used elsewhere).

**Return guarantee:** Returns a React element.

**Failure/errors:** No specific contract; depends on host-provided context.
