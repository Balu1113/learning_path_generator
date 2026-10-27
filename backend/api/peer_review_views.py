from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    CodeReview, CodeReviewComment, MilestoneProject, 
    UserReputation, GroupMembership
)
from .views import _json_body


@require_GET
def pending_reviews(request):
    """Get projects pending peer review."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    user_groups = GroupMembership.objects.filter(user=request.user).values_list('group_id', flat=True)
    
    projects = MilestoneProject.objects.filter(
        status='submitted',
        user__group_memberships__group_id__in=user_groups
    ).exclude(user=request.user).distinct()
    
    result = []
    for project in projects[:20]:
        review_count = CodeReview.objects.filter(submission=project).count()
        result.append({
            "id": project.id,
            "title": project.title,
            "author": project.user.username,
            "phase": project.phase_title,
            "submission_url": project.submission_url,
            "review_count": review_count,
            "submitted_at": project.updated_at.isoformat(),
        })
    
    return JsonResponse({"projects": result})


@csrf_protect
@require_POST
def create_review(request, project_id):
    """Create a peer code review."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        project = MilestoneProject.objects.get(id=project_id)
    except MilestoneProject.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)
    
    if project.user == request.user:
        return JsonResponse({"error": "Cannot review own submission"}, status=400)
    
    existing = CodeReview.objects.filter(submission=project, reviewer=request.user).first()
    if existing:
        return JsonResponse({"error": "Already reviewed"}, status=400)
    
    data = _json_body(request)
    
    review = CodeReview.objects.create(
        submission=project,
        reviewer=request.user,
        status='in_progress',
        summary=data.get('summary', '')
    )
    
    return JsonResponse({
        "id": review.id,
        "status": review.status,
        "created_at": review.created_at.isoformat(),
    })


@csrf_protect
@require_POST
def add_review_comment(request, review_id):
    """Add a comment to a code review."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        review = CodeReview.objects.get(id=review_id)
    except CodeReview.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    
    if review.reviewer != request.user and review.submission.user != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    data = _json_body(request)
    
    comment = CodeReviewComment.objects.create(
        review=review,
        author=request.user,
        line_number=data.get('line_number', 0),
        code_snippet=data.get('code_snippet', ''),
        comment=data.get('comment', '')
    )
    
    return JsonResponse({
        "id": comment.id,
        "author": comment.author.username,
        "created_at": comment.created_at.isoformat(),
    })


@require_GET
def review_detail(request, review_id):
    """Get review details with all comments."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        review = CodeReview.objects.get(id=review_id)
    except CodeReview.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    
    if review.reviewer != request.user and review.submission.user != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    comments = CodeReviewComment.objects.filter(review=review).order_by('line_number', 'created_at')
    
    return JsonResponse({
        "id": review.id,
        "status": review.status,
        "reviewer": review.reviewer.username,
        "overall_rating": review.overall_rating,
        "summary": review.summary,
        "comments": [
            {
                "id": c.id,
                "line_number": c.line_number,
                "code_snippet": c.code_snippet,
                "comment": c.comment,
                "author": c.author.username,
                "created_at": c.created_at.isoformat(),
            }
            for c in comments
        ],
        "created_at": review.created_at.isoformat(),
    })


@csrf_protect
@require_POST
def submit_review(request, review_id):
    """Submit a completed review."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    try:
        review = CodeReview.objects.get(id=review_id)
    except CodeReview.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    
    if review.reviewer != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    data = _json_body(request)
    
    review.status = data.get('status', 'approved')
    review.overall_rating = data.get('rating', 0)
    review.summary = data.get('summary', '')
    review.updated_at = timezone.now()
    review.save()
    
    _update_reputation(request.user, review.status)
    
    return JsonResponse({
        "id": review.id,
        "status": review.status,
        "updated_at": review.updated_at.isoformat(),
    })


@require_GET
def user_reputation(request):
    """Get user's reputation/karma."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    rep, _ = UserReputation.objects.get_or_create(user=request.user)
    
    return JsonResponse({
        "total_karma": rep.total_karma,
        "reviews_given": rep.reviews_given,
        "reviews_helpful": rep.reviews_helpful,
        "reputation_level": _get_reputation_level(rep.total_karma),
    })


@require_GET
def my_reviews(request):
    """Get reviews given by user."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    
    reviews = CodeReview.objects.filter(reviewer=request.user).order_by('-created_at')[:20]
    
    return JsonResponse({
        "reviews": [
            {
                "id": r.id,
                "project_title": r.submission.title,
                "author": r.submission.user.username,
                "status": r.status,
                "rating": r.overall_rating,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ]
    })


def _update_reputation(user, review_status):
    """Update user reputation based on review."""
    rep, _ = UserReputation.objects.get_or_create(user=user)
    rep.reviews_given += 1
    
    if review_status in ['approved', 'changes_requested']:
        rep.reviews_helpful += 1
        rep.total_karma += 10
    
    rep.save()


def _get_reputation_level(karma):
    """Get reputation level based on karma."""
    if karma < 50:
        return "Novice"
    elif karma < 200:
        return "Contributor"
    elif karma < 500:
        return "Expert"
    else:
        return "Master"
