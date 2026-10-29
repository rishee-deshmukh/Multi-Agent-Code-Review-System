from .models import Order


def order_summaries():
    summaries = []
    for order in Order.objects.all():
        summaries.append({
            "id": order.id,
            "customer": order.customer.name,  # @label io_in_loop high -- lazy foreign-key fetch: one query per order
            "total": order.total,
        })
    return summaries
