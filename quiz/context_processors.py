from .models import Notification


def global_context(request):
    ctx = {'whatsapp_number': '50938000000'}
    if request.user.is_authenticated:
        ctx['unread_count'] = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    return ctx
