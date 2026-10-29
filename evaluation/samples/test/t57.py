from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Article, Order


@require_GET
def articles_by_author(request):
    author = request.GET.get("author", "")
    limit = min(int(request.GET.get("limit", 10)), 50)
    articles = Article.objects.filter(author=author).select_related("category")[:limit]
    return JsonResponse({"articles": [{"id": a.id, "title": a.title, "category": a.category.name} for a in articles]})


@require_GET
def article_count(request):
    with connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM blog_article WHERE author = %s", [request.GET.get("author", "")])
        (count,) = cur.fetchone()
    return JsonResponse({"count": count})


def order_summaries():
    return [
        {"id": o.id, "customer": o.customer.name, "total": o.total}
        for o in Order.objects.select_related("customer")
    ]
