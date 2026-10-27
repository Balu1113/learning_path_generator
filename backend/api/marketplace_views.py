import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .models import CustomPath, PathPurchase, PathReview
from .views import _json_body


@require_GET
def marketplace_browse(request):
    """Browse published custom paths in marketplace."""
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', '-featured')
    page = int(request.GET.get('page', 1))
    limit = 20
    offset = (page - 1) * limit

    query = CustomPath.objects.filter(status='published')
    
    if category:
        query = query.filter(path_data__contains={'domain': category})
    
    total = query.count()
    paths = query.order_by(sort)[offset:offset + limit]

    result = []
    for path in paths:
        purchased = False
        if request.user.is_authenticated:
            purchased = PathPurchase.objects.filter(
                user=request.user, custom_path=path
            ).exists()

        result.append({
            'id': path.id,
            'title': path.title,
            'description': path.description[:200],
            'creator': path.creator.username,
            'price': float(path.price),
            'rating': path.rating,
            'rating_count': path.rating_count,
            'purchase_count': path.purchase_count,
            'featured': path.featured,
            'thumbnail_url': path.thumbnail_url,
            'purchased': purchased,
        })

    return JsonResponse({
        'paths': result,
        'total': total,
        'page': page,
        'pages': (total + limit - 1) // limit,
    })


@require_GET
def path_detail(request, path_id):
    """Get custom path details."""
    try:
        path = CustomPath.objects.get(id=path_id, status='published')
    except CustomPath.DoesNotExist:
        return JsonResponse({'error': 'Path not found'}, status=404)

    reviews = PathReview.objects.filter(custom_path=path).order_by('-created_at')[:10]

    purchased = False
    if request.user.is_authenticated:
        purchased = PathPurchase.objects.filter(
            user=request.user, custom_path=path
        ).exists()

    return JsonResponse({
        'id': path.id,
        'title': path.title,
        'description': path.description,
        'creator': path.creator.username,
        'price': float(path.price),
        'rating': path.rating,
        'rating_count': path.rating_count,
        'purchase_count': path.purchase_count,
        'thumbnail_url': path.thumbnail_url,
        'path_data': path.path_data,
        'purchased': purchased,
        'reviews': [
            {
                'author': r.user.username,
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at.isoformat(),
            }
            for r in reviews
        ],
    })


@csrf_protect
@require_POST
def purchase_path(request, path_id):
    """Purchase a custom path."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        path = CustomPath.objects.get(id=path_id, status='published')
    except CustomPath.DoesNotExist:
        return JsonResponse({'error': 'Path not found'}, status=404)

    if PathPurchase.objects.filter(user=request.user, custom_path=path).exists():
        return JsonResponse({'error': 'Already purchased'}, status=400)

    purchase = PathPurchase.objects.create(
        user=request.user,
        custom_path=path,
        amount_paid=path.price,
    )

    path.purchase_count += 1
    path.save()

    return JsonResponse({
        'id': purchase.id,
        'purchased_at': purchase.purchased_at.isoformat(),
        'path_data': path.path_data,
    })


@require_GET
def my_purchases(request):
    """Get user's purchased paths."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    purchases = PathPurchase.objects.filter(user=request.user).select_related('custom_path').order_by('-purchased_at')

    return JsonResponse({
        'purchases': [
            {
                'id': p.custom_path.id,
                'title': p.custom_path.title,
                'creator': p.custom_path.creator.username,
                'price': float(p.amount_paid),
                'purchased_at': p.purchased_at.isoformat(),
            }
            for p in purchases
        ]
    })


@require_GET
def my_created_paths(request):
    """Get paths created by user."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    paths = CustomPath.objects.filter(creator=request.user).order_by('-created_at')

    return JsonResponse({
        'paths': [
            {
                'id': p.id,
                'title': p.title,
                'status': p.status,
                'price': float(p.price),
                'rating': p.rating,
                'purchase_count': p.purchase_count,
                'featured': p.featured,
                'created_at': p.created_at.isoformat(),
            }
            for p in paths
        ]
    })


@csrf_protect
@require_POST
def create_custom_path(request):
    """Create a new custom path."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    data = _json_body(request)

    path = CustomPath.objects.create(
        creator=request.user,
        title=data.get('title', 'Untitled Path'),
        description=data.get('description', ''),
        thumbnail_url=data.get('thumbnail_url', ''),
        path_data=data.get('path_data', {}),
        price=float(data.get('price', 0)),
        status='draft',
    )

    return JsonResponse({
        'id': path.id,
        'status': path.status,
        'created_at': path.created_at.isoformat(),
    })


@csrf_protect
@require_POST
def update_custom_path(request, path_id):
    """Update custom path."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        path = CustomPath.objects.get(id=path_id, creator=request.user)
    except CustomPath.DoesNotExist:
        return JsonResponse({'error': 'Path not found'}, status=404)

    data = _json_body(request)

    path.title = data.get('title', path.title)
    path.description = data.get('description', path.description)
    path.thumbnail_url = data.get('thumbnail_url', path.thumbnail_url)
    path.path_data = data.get('path_data', path.path_data)
    path.price = float(data.get('price', path.price))
    path.status = data.get('status', path.status)
    path.save()

    return JsonResponse({
        'id': path.id,
        'status': path.status,
        'updated_at': path.updated_at.isoformat(),
    })


@csrf_protect
@require_POST
def review_path(request, path_id):
    """Review a purchased path."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        path = CustomPath.objects.get(id=path_id, status='published')
    except CustomPath.DoesNotExist:
        return JsonResponse({'error': 'Path not found'}, status=404)

    if not PathPurchase.objects.filter(user=request.user, custom_path=path).exists():
        return JsonResponse({'error': 'Must purchase path first'}, status=403)

    data = _json_body(request)
    rating = int(data.get('rating', 5))

    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Rating must be 1-5'}, status=400)

    review, created = PathReview.objects.update_or_create(
        custom_path=path,
        user=request.user,
        defaults={
            'rating': rating,
            'comment': data.get('comment', ''),
        }
    )

    if created:
        path.rating_count += 1
    
    all_reviews = PathReview.objects.filter(custom_path=path)
    avg_rating = all_reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    path.rating = round(avg_rating, 1)
    path.save()

    return JsonResponse({
        'id': review.id,
        'rating': review.rating,
        'created_at': review.created_at.isoformat(),
    })


@require_GET
def featured_paths(request):
    """Get featured paths."""
    paths = CustomPath.objects.filter(
        status='published',
        featured=True
    ).order_by('-rating')[:10]

    return JsonResponse({
        'paths': [
            {
                'id': p.id,
                'title': p.title,
                'creator': p.creator.username,
                'price': float(p.price),
                'rating': p.rating,
                'purchase_count': p.purchase_count,
                'thumbnail_url': p.thumbnail_url,
            }
            for p in paths
        ]
    })
