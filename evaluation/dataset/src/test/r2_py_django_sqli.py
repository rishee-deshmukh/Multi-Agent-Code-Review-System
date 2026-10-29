from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Article


@require_GET
def articles_by_author(request):
    author = request.GET.get("author", "")
    limit = min(int(request.GET.get("limit", 10)), 50)
    articles = Article.objects.raw(
        f"SELECT id, title, published FROM blog_article WHERE author = '{author}' ORDER BY published DESC LIMIT {limit}"  # @label sql_injection critical
    )
    payload = [{"id": a.id, "title": a.title, "published": a.published.isoformat()} for a in articles]
    return JsonResponse({"articles": payload})
