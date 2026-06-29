"""
KING CH Admin — compatible Python 3.14 + Django 4.x + Jazzmin
Root-cause fix: format_html() never receives pre-formatted strings.
All dynamic HTML is built with mark_safe() or plain string concatenation,
then passed to format_html as a single safe argument.
"""
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html, mark_safe, escape
from django.urls import reverse, path
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.db.models import Sum
from .models import UserProfile, DailyQuestion, UserAnswer, Certificate, Notification, Referral
import datetime


# ── helpers ────────────────────────────────────────────────────────────────────
def _badge(text, bg, color, border):
    """Return a styled badge as a safe string."""
    style = (
        f"background:{bg};color:{color};border:1px solid {border};"
        "padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;"
        "display:inline-block;"
    )
    return mark_safe(f'<span style="{style}">{text}</span>')


def _action_btn(url, label, cls, confirm=None):
    """Return a styled action-button anchor as a safe string."""
    confirm_attr = f' onclick="return confirm(\'{confirm}\')"' if confirm else ''
    return mark_safe(
        f'<a href="{url}" class="action-btn {cls}"{confirm_attr}>{label}</a>'
    )


# ── Inlines ────────────────────────────────────────────────────────────────────
class UserProfileInline(admin.StackedInline):
    model               = UserProfile
    fk_name             = 'user'   # fix E202: UserProfile has 2 FKs to User (user + referred_by)
    can_delete          = False
    verbose_name_plural = "Profil"
    fields              = ('phone', 'whatsapp', 'bio', 'total_points',
                           'is_blocked', 'blocked_reason', 'avatar', 'referral_code')
    readonly_fields     = ('total_points', 'referral_code')


class CertificateInline(admin.TabularInline):
    model            = Certificate
    fk_name          = 'user'
    extra            = 1
    readonly_fields  = ('issued_at', 'cert_thumb')
    fields           = ('title', 'description', 'points_required',
                        'certificate_image', 'cert_thumb', 'issued_at')
    show_change_link = True

    def cert_thumb(self, obj):
        if obj.pk and obj.certificate_image:
            return format_html(
                '<img src="{}" style="max-height:60px;border-radius:6px;'
                'border:1px solid rgba(212,160,23,.4);" />',
                obj.certificate_image.url,
            )
        return mark_safe('<span style="color:#8892A4;font-size:11px;">—</span>')
    cert_thumb.short_description = "Apercu"


# ── CustomUserAdmin ────────────────────────────────────────────────────────────
class CustomUserAdmin(UserAdmin):
    inlines       = (UserProfileInline, CertificateInline)
    list_display  = ('col_username', 'col_fullname', 'email',
                     'col_points', 'col_status', 'date_joined', 'col_actions')
    list_filter   = ('is_active', 'is_staff', 'profile__is_blocked', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 25
    actions       = ['bulk_block', 'bulk_unblock', 'bulk_clear_history',
                     'bulk_reset_points', 'action_reset_points_ALL']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('reset-all-points/',       self.admin_site.admin_view(self.v_reset_all),    name='user_reset_all_points'),
            path('reset-today-points/',     self.admin_site.admin_view(self.v_reset_today),  name='user_reset_today_points'),
            path('<int:pk>/block/',         self.admin_site.admin_view(self.v_block),         name='user_block'),
            path('<int:pk>/unblock/',       self.admin_site.admin_view(self.v_unblock),       name='user_unblock'),
            path('<int:pk>/add-points/',    self.admin_site.admin_view(self.v_add_pts),       name='user_add_points'),
            path('<int:pk>/rem-points/',    self.admin_site.admin_view(self.v_rem_pts),       name='user_rem_points'),
            path('<int:pk>/reset-points/',  self.admin_site.admin_view(self.v_reset_pts),     name='user_reset_points'),
            path('<int:pk>/del-history/',   self.admin_site.admin_view(self.v_del_history),   name='user_del_history'),
            path('<int:pk>/del-account/',   self.admin_site.admin_view(self.v_del_account),   name='user_del_account'),
            path('cert/<int:pk>/delete/',      self.admin_site.admin_view(self.v_del_cert),       name='cert_delete'),
        ]
        return custom + urls

    # ─── views ────────────────────────────────────────────────────────────────
    def v_block(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        p, _ = UserProfile.objects.get_or_create(user=u)
        p.is_blocked = True; p.save()
        messages.success(request, f"Compte '{u.username}' bloque.")
        return redirect('admin:auth_user_changelist')

    def v_unblock(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        p, _ = UserProfile.objects.get_or_create(user=u)
        p.is_blocked = False; p.blocked_reason = ''; p.save()
        messages.success(request, f"Compte '{u.username}' debloque.")
        return redirect('admin:auth_user_changelist')

    def v_add_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        p, _ = UserProfile.objects.get_or_create(user=u)
        if request.method == 'POST':
            try:
                pts = max(0, int(request.POST.get('points', 0)))
                if pts > 0:
                    p.total_points += pts; p.save()
                    Notification.objects.create(user=u,
                        message=f"L'admin a ajoute {pts} points. Total : {p.total_points} pts")
                    messages.success(request, f"+{pts} pts ajoutes a '{u.username}'.")
            except ValueError:
                messages.error(request, "Valeur invalide.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/points_form.html', {
            'title': f'Ajouter des points — {u.username}',
            'subtitle': f'Points actuels : {p.total_points}',
            'action_label': 'Ajouter', 'user_obj': u,
            'form_url': reverse('admin:user_add_points', args=[pk]),
            'btn_color': 'success', 'opts': self.model._meta,
        })

    def v_rem_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        p, _ = UserProfile.objects.get_or_create(user=u)
        if request.method == 'POST':
            try:
                pts = max(0, int(request.POST.get('points', 0)))
                if pts > 0:
                    p.total_points = max(0, p.total_points - pts); p.save()
                    Notification.objects.create(user=u,
                        message=f"L'admin a retire {pts} points. Total : {p.total_points} pts")
                    messages.success(request, f"-{pts} pts retires de '{u.username}'.")
            except ValueError:
                messages.error(request, "Valeur invalide.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/points_form.html', {
            'title': f'Retirer des points — {u.username}',
            'subtitle': f'Points actuels : {p.total_points}',
            'action_label': 'Retirer', 'user_obj': u,
            'form_url': reverse('admin:user_rem_points', args=[pk]),
            'btn_color': 'danger', 'opts': self.model._meta,
        })

    def v_reset_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        p, _ = UserProfile.objects.get_or_create(user=u)
        before = p.total_points; p.total_points = 0; p.save()
        Notification.objects.create(user=u, message="Vos points ont ete reinitialises a 0 par l'admin.")
        messages.success(request, f"Points de '{u.username}' reinitialises (etaient : {before} pts).")
        return redirect('admin:auth_user_changelist')

    def v_del_history(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        count = UserAnswer.objects.filter(user=u).count()
        UserAnswer.objects.filter(user=u).delete()
        messages.success(request, f"Historique de '{u.username}' supprime ({count} reponse(s)).")
        return redirect('admin:auth_user_changelist')

    def v_del_account(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            if request.POST.get('confirm', '') == u.username:
                name = u.username; u.delete()
                messages.success(request, f"Compte '{name}' supprime definitivement.")
            else:
                messages.error(request, "Confirmation incorrecte.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/confirm_delete_account.html', {
            'user_obj': u,
            'form_url': reverse('admin:user_del_account', args=[pk]),
            'opts': self.model._meta,
        })

    def v_del_cert(self, request, pk):
        """Delete a single certificate and notify the user."""
        from .models import Certificate
        cert = get_object_or_404(Certificate, pk=pk)
        user = cert.user
        title = cert.title
        # Delete the image file from storage if it exists
        if cert.certificate_image:
            try:
                import os
                if os.path.isfile(cert.certificate_image.path):
                    os.remove(cert.certificate_image.path)
            except Exception:
                pass
        cert.delete()
        Notification.objects.create(
            user=user,
            message=f"Votre certificat '{title}' a ete supprime par l'administrateur."
        )
        messages.success(request, f"Certificat '{title}' de '{user.username}' supprime.")
        return redirect('admin:quiz_certificate_changelist')

    def v_reset_all(self, request):
        """Reset TOTAL points for ALL users."""
        if request.method == 'POST':
            if request.POST.get('confirm', '') == 'REINITIALISER':
                affected = list(UserProfile.objects.exclude(total_points=0))
                for p in affected:
                    Notification.objects.create(user=p.user,
                        message="Reinitialisation globale : vos points totaux ont ete remis a 0.")
                count = len(affected)
                UserProfile.objects.all().update(total_points=0)
                messages.success(request, f"Points totaux reinitialises pour {count} utilisateur(s).")
            else:
                messages.error(request, "Confirmation incorrecte.")
            return redirect('admin:auth_user_changelist')
        total_pts   = UserProfile.objects.aggregate(t=Sum('total_points'))['t'] or 0
        total_users = UserProfile.objects.count()
        return render(request, 'admin/reset_all_points.html', {
            'reset_type':  'total',
            'total_users': total_users,
            'total_pts':   total_pts,
            'form_url':    reverse('admin:user_reset_all_points'),
            'opts':        self.model._meta,
        })

    def v_reset_today(self, request):
        """Reset TODAY's points for ALL users (delete today's answers + recalculate)."""
        today = datetime.date.today()
        if request.method == 'POST':
            if request.POST.get('confirm', '') == 'REINITIALISER':
                answers_today = UserAnswer.objects.filter(question__date=today)
                # Subtract today's points from each user
                affected_users = set()
                for ans in answers_today:
                    if ans.is_correct:
                        try:
                            ans.user.profile.total_points = max(0, ans.user.profile.total_points - ans.points_earned)
                            ans.user.profile.save()
                            affected_users.add(ans.user.pk)
                        except Exception:
                            pass
                count = answers_today.count()
                answers_today.delete()
                # Notify affected users
                for uid in affected_users:
                    try:
                        u = User.objects.get(pk=uid)
                        Notification.objects.create(user=u,
                            message=f"Les points du jour ({today}) ont ete reinitialises par l'admin.")
                    except Exception:
                        pass
                messages.success(request, f"Points du jour reinitialises : {count} reponse(s) supprimee(s), {len(affected_users)} utilisateur(s) affecte(s).")
            else:
                messages.error(request, "Confirmation incorrecte.")
            return redirect('admin:auth_user_changelist')
        count_today = UserAnswer.objects.filter(question__date=today).count()
        pts_today   = UserAnswer.objects.filter(question__date=today, is_correct=True).aggregate(t=Sum('points_earned'))['t'] or 0
        return render(request, 'admin/reset_today_points.html', {
            'today':       today,
            'count_today': count_today,
            'pts_today':   pts_today,
            'form_url':    reverse('admin:user_reset_today_points'),
            'opts':        self.model._meta,
        })

    # ─── display columns ──────────────────────────────────────────────────────
    def col_username(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.pk])
        return format_html('<a href="{}" style="font-weight:700;color:#D4A017;">{}</a>', url, obj.username)
    col_username.short_description = "Utilisateur"

    def col_fullname(self, obj):
        n = escape(f"{obj.first_name} {obj.last_name}".strip())
        return mark_safe(f'<span style="color:#E8E8F0;">{n or "—"}</span>')
    col_fullname.short_description = "Nom"

    def col_points(self, obj):
        try:
            pts = obj.profile.total_points
        except Exception:
            pts = 0
        color = '#2ecc71' if pts >= 50 else '#f39c12' if pts >= 20 else '#8892A4'
        return mark_safe(f'<strong style="color:{color};font-size:13px;">{pts} pts</strong>')
    col_points.short_description = "Points"

    def col_status(self, obj):
        try:
            blocked = obj.profile.is_blocked
        except Exception:
            blocked = False
        if blocked:
            return _badge('BLOQUE', 'rgba(231,76,60,.2)', '#e74c3c', 'rgba(231,76,60,.3)')
        return _badge('ACTIF', 'rgba(46,204,113,.2)', '#2ecc71', 'rgba(46,204,113,.3)')
    col_status.short_description = "Statut"

    def col_actions(self, obj):
        try:
            blocked = obj.profile.is_blocked
        except Exception:
            blocked = False

        b_url  = reverse('admin:user_block',        args=[obj.pk])
        ub_url = reverse('admin:user_unblock',      args=[obj.pk])
        ap_url = reverse('admin:user_add_points',   args=[obj.pk])
        rp_url = reverse('admin:user_rem_points',   args=[obj.pk])
        rs_url = reverse('admin:user_reset_points', args=[obj.pk])
        dh_url = reverse('admin:user_del_history',  args=[obj.pk])
        da_url = reverse('admin:user_del_account',  args=[obj.pk])
        ct_url = f"/admin/quiz/certificate/add/?user={obj.pk}"

        toggle = (
            _action_btn(ub_url, 'Debloquer', 'action-btn-unblock')
            if blocked else
            _action_btn(b_url,  'Bloquer',   'action-btn-block')
        )

        parts = [
            toggle,
            _action_btn(ap_url, '+Pts',      'action-btn-pts-add'),
            _action_btn(rp_url, '-Pts',      'action-btn-pts-rem'),
            _action_btn(rs_url, 'ResetPts',  'action-btn-reset',
                        confirm=f'Reinitialiser les points de {obj.username} ?'),
            _action_btn(ct_url, 'Certificat','action-btn-cert'),
            _action_btn(dh_url, 'Historique','action-btn-hist',
                        confirm=f'Supprimer l\'historique de {obj.username} ?'),
            _action_btn(da_url, 'Supprimer', 'action-btn-delete'),
        ]
        return mark_safe(' '.join(str(p) for p in parts))
    col_actions.short_description = "Actions"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['reset_all_url']   = reverse('admin:user_reset_all_points')
        extra_context['reset_today_url'] = reverse('admin:user_reset_today_points')
        return super().changelist_view(request, extra_context=extra_context)

    # ─── bulk actions ─────────────────────────────────────────────────────────
    def bulk_block(self, request, queryset):
        for u in queryset:
            try: u.profile.is_blocked = True; u.profile.save()
            except Exception: pass
        messages.success(request, f"{queryset.count()} compte(s) bloque(s).")
    bulk_block.short_description = "Bloquer les comptes selectionnes"

    def bulk_unblock(self, request, queryset):
        for u in queryset:
            try: u.profile.is_blocked = False; u.profile.blocked_reason = ''; u.profile.save()
            except Exception: pass
        messages.success(request, f"{queryset.count()} compte(s) debloque(s).")
    bulk_unblock.short_description = "Debloquer les comptes selectionnes"

    def bulk_clear_history(self, request, queryset):
        total = sum(UserAnswer.objects.filter(user=u).count() for u in queryset)
        for u in queryset:
            UserAnswer.objects.filter(user=u).delete()
        messages.success(request, f"Historique supprime ({total} reponses).")
    bulk_clear_history.short_description = "Supprimer l'historique des selectionnes"

    def bulk_reset_points(self, request, queryset):
        c = 0
        for u in queryset:
            try:
                if u.profile.total_points > 0:
                    u.profile.total_points = 0; u.profile.save()
                    Notification.objects.create(user=u,
                        message="Vos points ont ete reinitialises a 0 par l'admin.")
                    c += 1
            except Exception: pass
        messages.success(request, f"Points reinitialises pour {c} utilisateur(s).")
    bulk_reset_points.short_description = "Reinitialiser les points des selectionnes"

    def action_reset_points_ALL(self, request, queryset):
        return redirect(reverse('admin:user_reset_all_points'))
    action_reset_points_ALL.short_description = "Reinitialiser les points TOTAUX de TOUS"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ── UserProfile ────────────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('col_user', 'col_pts', 'col_status', 'phone', 'col_wa', 'referral_code', 'col_referrals', 'created_at')
    list_filter   = ('is_blocked',)
    search_fields = ('user__username', 'user__email', 'phone', 'referral_code')
    readonly_fields = ('created_at', 'col_pwd', 'referral_code', 'col_referrals')
    list_per_page = 25
    actions = ['block_sel', 'unblock_sel', 'reset_pts_sel']
    fieldsets = (
        ('Utilisateur',     {'fields': ('user', 'avatar', 'bio', 'phone', 'whatsapp')}),
        ('Points',          {'fields': ('total_points', 'referral_points_earned')}),
        ('Parrainage',      {'fields': ('referral_code', 'referred_by', 'col_referrals')}),
        ('Compte',          {'fields': ('is_blocked', 'blocked_reason'), 'classes': ('collapse',)}),
        ('Securite',        {'fields': ('col_pwd',), 'classes': ('collapse',)}),
        ('Date',            {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def col_pwd(self, obj):
        return format_html(
            '<code style="background:#0D0D14;color:#D4A017;padding:10px;border-radius:8px;'
            'display:block;word-break:break-all;font-size:11px;">{}</code>',
            obj.user.password,
        )
    col_pwd.short_description = "Hash du mot de passe"

    def col_user(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="color:#D4A017;font-weight:700;">{}</a>', url, obj.user.username)
    col_user.short_description = "Utilisateur"

    def col_pts(self, obj):
        c = '#2ecc71' if obj.total_points >= 50 else '#f39c12' if obj.total_points >= 20 else '#8892A4'
        return mark_safe(f'<strong style="color:{c};">{obj.total_points} pts</strong>')
    col_pts.short_description = "Points"

    def col_status(self, obj):
        if obj.is_blocked:
            return mark_safe('<span style="color:#e74c3c;font-weight:700;">BLOQUE</span>')
        return mark_safe('<span style="color:#2ecc71;font-weight:700;">ACTIF</span>')
    col_status.short_description = "Statut"

    def col_wa(self, obj):
        if obj.whatsapp:
            c = obj.whatsapp.replace('+', '').replace(' ', '')
            return format_html('<a href="https://wa.me/{}" target="_blank" style="color:#25D366;font-weight:700;">WhatsApp</a>', c)
        return '—'
    col_wa.short_description = "WhatsApp"

    def col_referrals(self, obj):
        count = Referral.objects.filter(referrer=obj.user).count()
        return mark_safe(f'<strong style="color:#D4A017;">{count} ami(s) invites</strong>')
    col_referrals.short_description = "Parrainages"

    def block_sel(self, request, qs):
        qs.update(is_blocked=True)
        messages.success(request, f"{qs.count()} bloque(s).")
    block_sel.short_description = "Bloquer"

    def unblock_sel(self, request, qs):
        qs.update(is_blocked=False, blocked_reason='')
        messages.success(request, f"{qs.count()} debloque(s).")
    unblock_sel.short_description = "Debloquer"

    def reset_pts_sel(self, request, qs):
        qs.update(total_points=0)
        messages.success(request, f"Points reinitialises pour {qs.count()} profil(s).")
    reset_pts_sel.short_description = "Reinitialiser les points"


# ── DailyQuestion ──────────────────────────────────────────────────────────────
@admin.register(DailyQuestion)
class DailyQuestionAdmin(admin.ModelAdmin):
    list_display   = ('col_q', 'col_date', 'category', 'col_answers',
                      'col_correct', 'points', 'is_active', 'col_stats', 'col_del')
    list_filter    = ('is_active', 'category', 'date')
    search_fields  = ('question_text', 'option_a', 'option_b', 'option_c', 'option_d')
    date_hierarchy = 'date'
    list_per_page  = 15
    actions        = ['delete_past', 'activate_sel', 'deactivate_sel']
    # ── Clean fieldsets — only real model fields ──────────────────────────────
    fieldsets = (
        ('Question', {
            'fields': ('question_text', 'category', 'date', 'points', 'is_active', 'created_by'),
        }),
        ('Les 4 reponses (A, B, C, D)', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'),
            'description': 'Remplissez les 4 reponses, puis selectionnez la lettre correcte.',
        }),
    )

    def col_q(self, obj):
        t = obj.question_text
        s = escape(t[:70] + '...' if len(t) > 70 else t)
        return mark_safe(f'<span style="font-weight:600;color:#E8E8F0;">{s}</span>')
    col_q.short_description = "Question"

    def col_answers(self, obj):
        def tag(letter, text):
            s = escape(text[:24] + '…' if len(text) > 24 else text)
            return (
                f'<span style="display:inline-block;background:rgba(212,160,23,.1);'
                f'border:1px solid rgba(212,160,23,.2);border-radius:5px;'
                f'padding:1px 6px;margin:2px;font-size:11px;white-space:nowrap;">'
                f'<b style="color:#D4A017;">{letter}</b> {s}</span>'
            )
        html = tag('A', obj.option_a) + tag('B', obj.option_b) + tag('C', obj.option_c) + tag('D', obj.option_d)
        return mark_safe(f'<div style="line-height:2;">{html}</div>')
    col_answers.short_description = "Reponses A / B / C / D"

    def col_correct(self, obj):
        mapping = {'A': obj.option_a, 'B': obj.option_b, 'C': obj.option_c, 'D': obj.option_d}
        text  = mapping.get(obj.correct_answer, '')
        short = text[:22] + '…' if len(text) > 22 else text
        html = (
            f'<span style="background:rgba(46,204,113,.15);color:#2ecc71;'
            f'border:1px solid rgba(46,204,113,.3);border-radius:7px;'
            f'padding:2px 8px;font-size:11px;font-weight:700;">'
            f'{obj.correct_answer} — {short}</span>'
        )
        return mark_safe(html)
    col_correct.short_description = "Bonne reponse"

    def col_date(self, obj):
        today = datetime.date.today()
        if obj.date == today:
            return mark_safe(f"<strong style='color:#D4A017;'>{obj.date} (Auj.)</strong>")
        if obj.date < today:
            return mark_safe(f"<span style='color:#8892A4;'>{obj.date}</span>")
        return mark_safe(f"<span style='color:#3498db;'>{obj.date}</span>")
    col_date.short_description = "Date"

    def col_stats(self, obj):
        total   = obj.user_answers.count()
        correct = obj.user_answers.filter(is_correct=True).count()
        pct     = round(correct / total * 100) if total else 0
        return mark_safe(
            f"<span style='color:#8892A4;font-size:11px;'>{total} rep. </span>"
            f"<span style='color:#2ecc71;font-size:11px;'>{correct} OK ({pct}%)</span>"
        )
    col_stats.short_description = "Stats"

    def col_del(self, obj):
        if obj.date < datetime.date.today():
            url = reverse('admin:quiz_dailyquestion_delete', args=[obj.pk])
            return mark_safe(
                f"<a href='{url}' class='action-btn action-btn-delete' "
                f"onclick=\"return confirm('Supprimer cette question ?')\">Supprimer</a>"
            )
        return mark_safe("<span style='color:#8892A4;font-size:11px;'>Active</span>")
    col_del.short_description = "Suppr."

    def delete_past(self, request, queryset):
        past = queryset.filter(date__lt=datetime.date.today())
        c = past.count(); past.delete()
        messages.success(request, f"{c} question(s) passee(s) supprimee(s).")
    delete_past.short_description = "Supprimer les questions passees"

    def activate_sel(self, request, queryset):
        queryset.update(is_active=True)
    activate_sel.short_description = "Activer"

    def deactivate_sel(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_sel.short_description = "Desactiver"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ── UserAnswer ─────────────────────────────────────────────────────────────────
@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display    = ('user', 'col_q', 'col_selected', 'col_result', 'points_earned', 'answered_at')
    list_filter     = ('is_correct', 'answered_at', 'selected_answer')
    search_fields   = ('user__username', 'question__question_text')
    readonly_fields = ('user', 'question', 'selected_answer', 'is_correct', 'points_earned', 'answered_at')
    list_per_page   = 30
    date_hierarchy  = 'answered_at'

    def col_q(self, obj):
        return obj.question.question_text[:55] + '...'
    col_q.short_description = "Question"

    def col_selected(self, obj):
        mapping = {'A': obj.question.option_a, 'B': obj.question.option_b,
                   'C': obj.question.option_c, 'D': obj.question.option_d}
        text  = mapping.get(obj.selected_answer, '')
        short = text[:22] + '…' if len(text) > 22 else text
        return mark_safe(
            f'<span style="background:rgba(52,152,219,.12);color:#3498db;padding:2px 8px;'
            f'border-radius:6px;font-size:11px;font-weight:700;">{obj.selected_answer} — {short}</span>'
        )
    col_selected.short_description = "Reponse choisie"

    def col_result(self, obj):
        if obj.is_correct:
            return mark_safe('<span style="color:#2ecc71;font-weight:700;">Correct</span>')
        return mark_safe('<span style="color:#e74c3c;font-weight:700;">Incorrect</span>')
    col_result.short_description = "Resultat"


# ── Certificate ────────────────────────────────────────────────────────────────
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display  = ('col_user', 'title', 'points_required', 'col_thumb', 'issued_at', 'col_download', 'col_delete')
    list_filter   = ('issued_at',)
    search_fields = ('user__username', 'title')
    list_per_page = 20
    readonly_fields = ('issued_at', 'issued_by', 'col_preview')
    actions = ['notify_selected', 'delete_selected_certs']
    fieldsets = (
        ('Destinataire', {
            'fields': ('user', 'issued_by'),
        }),
        ('Contenu', {
            'fields': ('title', 'description', 'points_required'),
        }),
        ('Photo / Image du certificat', {
            'fields': ('certificate_image', 'col_preview'),
            'description': (
                'Uploadez la photo depuis votre stockage local. '
                'Formats acceptes : JPG, PNG, WEBP, GIF.'
            ),
        }),
        ('Date', {
            'fields': ('issued_at',),
            'classes': ('collapse',),
        }),
    )

    def col_user(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="color:#D4A017;font-weight:700;">{}</a>', url, obj.user.username)
    col_user.short_description = "Utilisateur"

    def col_thumb(self, obj):
        if obj.certificate_image:
            return format_html(
                '<img src="{}" style="height:48px;width:auto;border-radius:6px;'
                'border:1px solid rgba(212,160,23,.4);object-fit:cover;" />',
                obj.certificate_image.url,
            )
        return mark_safe('<span style="color:#8892A4;font-size:11px;">—</span>')
    col_thumb.short_description = "Apercu"

    def col_preview(self, obj):
        if obj.pk and obj.certificate_image:
            return format_html(
                '<img src="{}" style="max-width:380px;max-height:260px;border-radius:10px;'
                'border:2px solid rgba(212,160,23,.4);display:block;margin-top:8px;" />'
                '<div style="color:#8892A4;font-size:11px;margin-top:6px;">Fichier : {}</div>',
                obj.certificate_image.url,
                obj.certificate_image.name,
            )
        return mark_safe('<span style="color:#8892A4;font-size:12px;">Uploadez une image ci-dessus.</span>')
    col_preview.short_description = "Apercu de l'image"

    def col_download(self, obj):
        if obj.certificate_image:
            return format_html(
                '<a href="{}" target="_blank" download style="color:#3498db;font-weight:600;font-size:12px;">Telecharger</a>',
                obj.certificate_image.url,
            )
        return mark_safe('<span style="color:#8892A4;font-size:11px;">—</span>')
    col_download.short_description = "Telecharger"

    def col_delete(self, obj):
        url = reverse('admin:cert_delete', args=[obj.pk])
        return mark_safe(
            f'<a href="{url}" class="action-btn action-btn-delete" '
            f'onclick="return confirm(\'Supprimer ce certificat de {obj.user.username} ?\')">Supprimer</a>'
        )
    col_delete.short_description = "Supprimer"

    def notify_selected(self, request, queryset):
        for cert in queryset:
            Notification.objects.create(
                user=cert.user,
                message=f"Vous avez recu un certificat : '{cert.title}'. Consultez votre profil."
            )
        messages.success(request, f"Notifications envoyees pour {queryset.count()} certificat(s).")
    notify_selected.short_description = "Envoyer notification"

    def delete_selected_certs(self, request, queryset):
        import os
        count = queryset.count()
        for cert in queryset:
            if cert.certificate_image:
                try:
                    if os.path.isfile(cert.certificate_image.path):
                        os.remove(cert.certificate_image.path)
                except Exception:
                    pass
            Notification.objects.create(
                user=cert.user,
                message=f"Votre certificat '{cert.title}' a ete supprime par l'administrateur."
            )
        queryset.delete()
        messages.success(request, f"{count} certificat(s) supprime(s).")
    delete_selected_certs.short_description = "Supprimer les certificats selectionnes (avec image)"

    def save_model(self, request, obj, form, change):
        if not change and not obj.issued_by_id:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            msg = f"Felicitations ! Vous avez recu un certificat : '{obj.title}'."
            if obj.certificate_image:
                msg += " Consultez votre profil pour telecharger votre image."
            Notification.objects.create(user=obj.user, message=msg)


# ── Notification ───────────────────────────────────────────────────────────────
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'col_msg', 'is_read', 'created_at')
    list_filter   = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    list_per_page = 30
    actions       = ['mark_read', 'mark_unread']

    def col_msg(self, obj):
        return obj.message[:90] + '...' if len(obj.message) > 90 else obj.message
    col_msg.short_description = "Message"

    def mark_read(self, request, qs):
        qs.update(is_read=True)
    mark_read.short_description = "Marquer comme lu"

    def mark_unread(self, request, qs):
        qs.update(is_read=False)
    mark_unread.short_description = "Marquer comme non lu"


# ── Referral ───────────────────────────────────────────────────────────────────
@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display  = ('col_referrer', 'col_referred', 'points_given', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('referrer__username', 'referred_user__username')
    readonly_fields = ('referrer', 'referred_user', 'points_given', 'created_at')
    list_per_page = 30

    def col_referrer(self, obj):
        return format_html('<strong style="color:#D4A017;">{}</strong>', obj.referrer.username)
    col_referrer.short_description = "Parrain"

    def col_referred(self, obj):
        return format_html('<span style="color:#E8E8F0;">{}</span>', obj.referred_user.username)
    col_referred.short_description = "Ami invite"
