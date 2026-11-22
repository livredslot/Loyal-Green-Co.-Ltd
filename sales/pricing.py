"""Which price applies: a customer's special price first, then their price group's."""

from datetime import date

from django.db.models import Q

from .models import Price


def _active(qs, on):
    return qs.filter(valid_from__lte=on).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on))


def _best(qs, qty):
    # The highest quantity break the order reaches, then the newest price
    return qs.filter(min_qty__lte=qty).order_by("-min_qty", "-valid_from", "-id").first()


def find_price(item, customer=None, price_group=None, unit="pkt", qty=1, on=None):
    """Return the Price that applies, or None. Quantity is in the same unit."""
    on = on or date.today()
    prices = _active(Price.objects.filter(item=item, unit=unit), on)
    if customer:
        special = _best(prices.filter(customer=customer), qty)
        if special:
            return special
        price_group = price_group or customer.price_group
    if price_group:
        return _best(prices.filter(price_group=price_group), qty)
    return None


def unit_price(item, customer=None, price_group=None, unit="pkt", qty=1, on=None):
    """Price in kyats per unit. A carton without its own price is the packet price × packets per carton."""
    found = find_price(item, customer, price_group, unit, qty, on)
    if found:
        return found.price
    if unit == "ctn" and item.pkt_per_ctn:
        per_pkt = find_price(item, customer, price_group, "pkt", qty * item.pkt_per_ctn, on)
        if per_pkt:
            return per_pkt.price * item.pkt_per_ctn
    return None


def current_group_prices(items, groups, on=None):
    """{(item_id, group_id): Price} of today's basic packet price (minimum quantity 1) for a price list grid."""
    on = on or date.today()
    rows = _active(Price.objects.filter(item__in=items, price_group__in=groups, unit="pkt", min_qty=1), on)
    result = {}
    for p in rows.order_by("valid_from", "id"):
        result[(p.item_id, p.price_group_id)] = p
    return result
