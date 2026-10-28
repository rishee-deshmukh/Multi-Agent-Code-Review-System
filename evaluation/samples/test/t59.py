from .models import Order


def order_summaries():
    summaries = []
    for order in Order.objects.all():
        summaries.append({
            "id": order.id,
            "customer": order.customer.name,
            "total": order.total,
        })
    return summaries
