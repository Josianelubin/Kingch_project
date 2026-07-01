from .models import Notification


def global_context(request):
    ctx = {'whatsapp_number': '50938000000', 'unread_count': 0}
    if request.user.is_authenticated:
        try:
            ctx['unread_count'] = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
        except Exception:
            ctx['unread_count'] = 0
    return ctx
