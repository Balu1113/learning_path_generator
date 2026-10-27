import re
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from .models import VideoResource, VideoProgress, VideoNote, Resource
from .views import _json_body


def _extract_video_id(url):
    """Extract video ID from YouTube or Vimeo URL."""
    youtube_regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)'
    vimeo_regex = r'vimeo\.com\/(\d+)'
    
    youtube_match = re.search(youtube_regex, url)
    if youtube_match:
        return 'youtube', youtube_match.group(1)
    
    vimeo_match = re.search(vimeo_regex, url)
    if vimeo_match:
        return 'vimeo', vimeo_match.group(1)
    
    return None, None


@require_GET
def video_detail(request, video_id):
    """Get video details and user's progress."""
    try:
        video = VideoResource.objects.get(id=video_id)
    except VideoResource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)

    progress = None
    notes = []
    
    if request.user.is_authenticated:
        progress_obj, _ = VideoProgress.objects.get_or_create(
            user=request.user, video=video
        )
        progress = {
            'seconds_watched': progress_obj.seconds_watched,
            'completed': progress_obj.completed,
            'last_watched': progress_obj.last_watched_at.isoformat(),
        }
        
        notes = VideoNote.objects.filter(user=request.user, video=video).order_by('timestamp_seconds')

    return JsonResponse({
        'id': video.id,
        'title': video.resource.name,
        'description': video.resource.description,
        'platform': video.platform,
        'video_id': video.video_id,
        'duration_seconds': video.duration_seconds,
        'transcript': video.transcript if video.transcript_searchable else '',
        'progress': progress,
        'notes': [
            {
                'id': n.id,
                'timestamp': n.timestamp_seconds,
                'note': n.note,
                'created_at': n.created_at.isoformat(),
            }
            for n in notes
        ],
    })


@csrf_protect
@require_POST
def update_video_progress(request, video_id):
    """Update user's video watching progress."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        video = VideoResource.objects.get(id=video_id)
    except VideoResource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)

    data = _json_body(request)
    seconds_watched = int(data.get('seconds_watched', 0))
    
    progress, _ = VideoProgress.objects.get_or_create(user=request.user, video=video)
    progress.seconds_watched = max(progress.seconds_watched, seconds_watched)
    
    if seconds_watched >= video.duration_seconds * 0.9:
        progress.completed = True
    
    progress.last_watched_at = timezone.now()
    progress.save()

    return JsonResponse({
        'seconds_watched': progress.seconds_watched,
        'completed': progress.completed,
    })


@csrf_protect
@require_POST
def add_video_note(request, video_id):
    """Add a timestamped note to a video."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        video = VideoResource.objects.get(id=video_id)
    except VideoResource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)

    data = _json_body(request)
    timestamp = int(data.get('timestamp_seconds', 0))
    note_text = data.get('note', '').strip()

    if not note_text:
        return JsonResponse({'error': 'Note cannot be empty'}, status=400)

    note = VideoNote.objects.create(
        user=request.user,
        video=video,
        timestamp_seconds=timestamp,
        note=note_text,
    )

    return JsonResponse({
        'id': note.id,
        'timestamp': note.timestamp_seconds,
        'note': note.note,
        'created_at': note.created_at.isoformat(),
    })


@require_GET
def search_transcript(request, video_id):
    """Search video transcript."""
    query = request.GET.get('q', '').lower()
    
    if not query:
        return JsonResponse({'error': 'Query required'}, status=400)

    try:
        video = VideoResource.objects.get(id=video_id)
    except VideoResource.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)

    if not video.transcript_searchable or not video.transcript:
        return JsonResponse({'results': []})

    lines = video.transcript.split('\n')
    results = []
    
    for i, line in enumerate(lines):
        if query in line.lower():
            results.append({
                'line_number': i,
                'text': line,
                'timestamp': i * 10,
            })

    return JsonResponse({'results': results[:20]})


@require_GET
def my_video_progress(request):
    """Get user's video watching progress."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    progress = VideoProgress.objects.filter(user=request.user).select_related('video').order_by('-last_watched_at')

    return JsonResponse({
        'videos': [
            {
                'id': p.video.id,
                'title': p.video.resource.name,
                'seconds_watched': p.seconds_watched,
                'duration_seconds': p.video.duration_seconds,
                'completed': p.completed,
                'progress_percent': int((p.seconds_watched / p.video.duration_seconds) * 100),
                'last_watched': p.last_watched_at.isoformat(),
            }
            for p in progress
        ]
    })


@csrf_protect
@require_POST
def create_video_resource(request):
    """Create a new video resource (admin only)."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin only'}, status=403)

    data = _json_body(request)
    url = data.get('url', '')
    
    platform, video_id = _extract_video_id(url)
    if not platform:
        return JsonResponse({'error': 'Invalid video URL'}, status=400)

    resource = Resource.objects.create(
        url=url,
        name=data.get('title', 'Video'),
        type='video',
        level=data.get('level', 'beginner'),
        cost=data.get('cost', 'free'),
        duration_hours=float(data.get('duration_hours', 0)),
        domain=data.get('domain', ''),
        description=data.get('description', ''),
        content_source='curated',
        url_health='ok',
    )

    video = VideoResource.objects.create(
        resource=resource,
        platform=platform,
        video_id=video_id,
        duration_seconds=int(data.get('duration_seconds', 0)),
        transcript=data.get('transcript', ''),
        transcript_searchable=bool(data.get('transcript', '')),
    )

    return JsonResponse({
        'id': video.id,
        'platform': video.platform,
        'video_id': video.video_id,
        'created_at': video.created_at.isoformat(),
    })


@require_GET
def video_recommendations(request, path_id):
    """Get video recommendations for a path."""
    from .models import Resource
    
    resources = Resource.objects.filter(
        type='video',
        content_source='curated',
        url_health='ok'
    ).order_by('-community_rating')[:20]

    videos = []
    for resource in resources:
        try:
            video = resource.video
            videos.append({
                'id': video.id,
                'title': resource.name,
                'description': resource.description,
                'platform': video.platform,
                'duration_seconds': video.duration_seconds,
                'rating': resource.community_rating or 0,
                'rating_count': resource.rating_count,
            })
        except:
            pass

    return JsonResponse({'videos': videos})
