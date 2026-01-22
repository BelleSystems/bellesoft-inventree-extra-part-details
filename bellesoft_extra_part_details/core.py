"""Shows the part's price total."""

import logging
from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from djmoney.money import Money
from plugin import InvenTreePlugin
from plugin.mixins import SettingsMixin, UserInterfaceMixin
from stock.models import StockItem
from stock.status_codes import StockStatus

from . import PLUGIN_VERSION

logger = logging.getLogger(__name__)


class BellesoftExtraPartDetails(SettingsMixin, UserInterfaceMixin, InvenTreePlugin):
    """Bellesoft Extra Part Details - custom InvenTree plugin."""

    # Plugin metadata
    TITLE = "Bellesoft Extra Part Details"
    NAME = "BellesoftExtraPartDetails"
    SLUG = "bellesoft-extra-part-details"
    DESCRIPTION = "Shows extra part details for Bellesoft AMS."
    VERSION = PLUGIN_VERSION

    # Additional project information
    AUTHOR = "Bellesoft Systems Inc."

    LICENSE = "MIT"

    # Optionally specify supported InvenTree versions
    # MIN_VERSION = '0.18.0'
    # MAX_VERSION = '2.0.0'

    # Render custom UI elements to the plugin settings page
    ADMIN_SOURCE = "Settings.js:renderPluginSettings"

    # Plugin settings (from SettingsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/settings/
    SETTINGS = {}

    def part_total_purchase_cost(self, part_id: int):
        from part.models import Part

        part = Part.objects.get(id=part_id)
        total, ok_total, damaged_total = None, None, None
        currency = None
        mixed_currency = False

        for item in StockItem.objects.filter(part_id=part_id):
            price = item.purchase_price

            # Fallback to internal price if purchase_price is not set
            if not price and part.has_internal_price_breaks:
                internal_price_decimal = part.get_internal_price(item.quantity)
                if internal_price_decimal:
                    first_break = part.internal_price_breaks.first()
                    if first_break and first_break.price:
                        price = Money(
                            internal_price_decimal,
                            first_break.price.currency,
                        )

            if not price:
                continue

            if currency is None:
                currency = price.currency
                total = Money(0, currency)
                ok_total = Money(0, currency)
                damaged_total = Money(0, currency)

            if currency != price.currency:
                mixed_currency = True
                break

            if item.status == StockStatus.OK.value:
                ok_total += price * item.quantity
            elif item.status == StockStatus.DAMAGED.value:
                damaged_total += price * item.quantity

            total += price * item.quantity

        return total, ok_total, damaged_total, currency, mixed_currency

    def part_total_stock(self, part_id: int):
        from part.models import Part

        part = Part.objects.get(id=part_id)

        # Get stock counts by status
        ok_stock = (
            part.stock_items.filter(status=StockStatus.OK.value).aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )

        damaged_stock = (
            part.stock_items.filter(status=StockStatus.DAMAGED.value).aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )

        total_stock = part.total_stock

        return total_stock, ok_stock, damaged_stock

    def part_stock_by_location(self, part_id: int):
        from part.models import Part
        from stock.models import StockLocation

        part = Part.objects.get(id=part_id)
        stock_items = part.stock_items.all()

        # Raw DB aggregation (can produce multiple rows per location due to joins/annotations upstream)
        location_totals = list(
            stock_items.values("location").annotate(
                total_qty=Coalesce(Sum("quantity"), Decimal("0")),
                ok_qty=Coalesce(
                    Sum("quantity", filter=Q(status=StockStatus.OK.value)), Decimal("0")
                ),
                damaged_qty=Coalesce(
                    Sum("quantity", filter=Q(status=StockStatus.DAMAGED.value)),
                    Decimal("0"),
                ),
            )
        )

        # 1) Merge duplicates per location in Python
        per_location = {}
        for row in location_totals:
            loc = row["location"]
            data = per_location.setdefault(
                loc,
                {
                    "total_qty": Decimal("0"),
                    "ok_qty": Decimal("0"),
                    "damaged_qty": Decimal("0"),
                },
            )
            data["total_qty"] += row["total_qty"]
            data["ok_qty"] += row["ok_qty"]
            data["damaged_qty"] += row["damaged_qty"]

        # 2) Build final location_data dict
        location_data: dict[str, dict] = {}

        for location_id, agg in per_location.items():
            if location_id:
                try:
                    location = StockLocation.objects.get(id=location_id)
                    location_name = location.name
                    location_path = location.pathstring or location.name
                except StockLocation.DoesNotExist:
                    location_name = f"Location {location_id} (deleted)"
                    location_path = location_name
            else:
                location_name = "No Location"
                location_path = "No Location"

            dict_key = str(location_id) if location_id is not None else "no_location"

            location_data[dict_key] = {
                "location_id": location_id,
                "location_name": location_name,
                "location_path": location_path,
                "total": agg["total_qty"],
                "ok": agg["ok_qty"],
                "damaged": agg["damaged_qty"],
            }

        return location_data

    # User interface elements (from UserInterfaceMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/ui/

    # Custom UI panels
    def get_ui_panels(self, request, context: dict, **kwargs):  # noqa: ARG002
        """Return a list of custom panels to be rendered in the InvenTree user interface."""
        if context.get("target_model") != "part":
            return []
        part = context.get("target_id")
        if not part:
            return []

        total, ok_total, damaged_total, currency, mixed = self.part_total_purchase_cost(
            part
        )
        total_stock, ok_stock, damaged_stock = self.part_total_stock(part)

        return [
            {
                "key": "part-total-price-panel",
                "title": "Part Total Price",
                "description": "Custom panel description",
                "icon": "ti:mood-smile:outline",
                "source": self.plugin_static_file("Panel.js:renderPartTotalPricePanel"),
                "context": {
                    "settings": self.get_settings_dict(),
                    "locations_data": self.part_stock_by_location(part),
                    "total_price": str(total.amount) if total else None,
                    "ok_total_price": str(ok_total.amount) if ok_total else None,
                    "damaged_total_price": (
                        str(damaged_total.amount) if damaged_total else None
                    ),
                    "total_stock": total_stock if total_stock is not None else None,
                    "ok_stock": ok_stock if ok_stock is not None else None,
                    "damaged_stock": (
                        damaged_stock if damaged_stock is not None else None
                    ),
                    "currency": str(currency) if currency else None,
                    "mixed_currency": mixed,
                },
            }
        ]

    def get_ui_dashboard_items(self, request, context: dict, **kwargs):  # noqa: ARG002
        """Return a list of custom dashboard items to be rendered in the InvenTree user interface."""
        if not request.user or not request.user.is_staff:
            return []

        return [
            {
                "key": "part-total-price-dashboard",
                "title": "Part Total Price Dashboard Item",
                "description": "Custom dashboard item",
                "icon": "ti:dashboard:outline",
                "source": self.plugin_static_file(
                    "Dashboard.js:renderPartTotalPriceDashboardItem"
                ),
                "context": {"settings": self.get_settings_dict()},
            }
        ]
