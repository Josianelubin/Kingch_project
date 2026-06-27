from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse, path
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.db.models import Sum
from .models import UserProfile, DailyQuestion, UserAnswer, Certificate, Notification
import datetime

# Jazzmin handles site_header/title via settings.py — do NOT set them here.


# ── Inlines ────────────────────────────────────────────────────────────────────
class UserProfileInline(admin.StackedInline):
    model              = UserProfile
    can_delete         = False
    verbose_name_plural = "Profil"
    fields             = ('phone', 'whatsapp', 'bio', 'total_points', 'is_blocked', 'blocked_reason', 'avatar')
    readonly_fields    = ('total_points',)


class CertificateInline(admin.TabularInline):
    """Voir les certificats envoyes depuis la fiche utilisateur."""
    model            = Certificate
    fk_name          = 'user'
    extra            = 1          # 1 ligne vide pour ajouter directement
    readonly_fields  = ('issued_at', 'cert_preview')
    fields           = ('title', 'description', 'points_required', 'certificate_image', 'cert_preview', 'issued_at')
    show_change_link = True

    def cert_preview(self, obj):
        if obj.certificate_image:
            return format_html(
                '<img src="{}" style="max-height:80px; max-width:120px; '
                'border-radius:6px; border:1px solid rgba(212,160,23,.4);" />',
                obj.certificate_image.url
            )
        return format_html('<span style="color:#8892A4;font-size:11px;">Aucune image</span>')
    cert_preview.short_description = "Apercu"


# ── CustomUserAdmin ────────────────────────────────────────────────────────────
class CustomUserAdmin(UserAdmin):
    inlines       = (UserProfileInline, CertificateInline)
    list_display  = ('username_display', 'full_name', 'email',
                     'points_display', 'status_display', 'date_joined', 'admin_actions')
    list_filter   = ('is_active', 'is_staff', 'profile__is_blocked', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 25
    actions       = ['bulk_block', 'bulk_unblock', 'bulk_clear_history',
                     'bulk_reset_points', 'reset_points_ALL']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/block/',        self.admin_site.admin_view(self.v_block),        name='user_block'),
            path('<int:pk>/unblock/',      self.admin_site.admin_view(self.v_unblock),      name='user_unblock'),
            path('<int:pk>/add-points/',   self.admin_site.admin_view(self.v_add_pts),      name='user_add_points'),
            path('<int:pk>/rem-points/',   self.admin_site.admin_view(self.v_rem_pts),      name='user_rem_points'),
            path('<int:pk>/reset-points/', self.admin_site.admin_view(self.v_reset_pts),    name='user_reset_points'),
            path('<int:pk>/del-history/',  self.admin_site.admin_view(self.v_del_history),  name='user_del_history'),
            path('<int:pk>/del-account/',  self.admin_site.admin_view(self.v_del_account),  name='user_del_account'),
            path('reset-all-points/',      self.admin_site.admin_view(self.v_reset_all),    name='reset_all_points'),
        ]
        return custom + urls

    # ─── Custom views ──────────────────────────────────────────────────────────
    def v_block(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        try:
            u.profile.is_blocked = True
            u.profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=u, is_blocked=True)
        messages.success(request, f"Compte '{u.username}' bloque.")
        return redirect('admin:auth_user_changelist')

    def v_unblock(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        try:
            u.profile.is_blocked = False
            u.profile.blocked_reason = ''
            u.profile.save()
        except UserProfile.DoesNotExist:
            pass
        messages.success(request, f"Compte '{u.username}' debloque.")
        return redirect('admin:auth_user_changelist')

    def v_add_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        profile, _ = UserProfile.objects.get_or_create(user=u)
        if request.method == 'POST':
            try:
                pts = max(0, int(request.POST.get('points', 0)))
                if pts > 0:
                    profile.total_points += pts
                    profile.save()
                    Notification.objects.create(
                        user=u,
                        message=f"L'administrateur a ajoute {pts} points a votre compte. "
                                f"Nouveau total : {profile.total_points} pts"
                    )
                    messages.success(request, f"+{pts} pts ajoutes a '{u.username}'. Total : {profile.total_points} pts")
                else:
                    messages.warning(request, "Entrez un nombre positif.")
            except ValueError:
                messages.error(request, "Valeur invalide.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/points_form.html', {
            'title':        f'Ajouter des points — {u.username}',
            'subtitle':     f'Points actuels : {profile.total_points}',
            'action_label': 'Ajouter',
            'user_obj':     u,
            'form_url':     reverse('admin:user_add_points', args=[pk]),
            'btn_color':    'success',
            'opts':         self.model._meta,
        })

    def v_rem_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        profile, _ = UserProfile.objects.get_or_create(user=u)
        if request.method == 'POST':
            try:
                pts = max(0, int(request.POST.get('points', 0)))
                if pts > 0:
                    profile.total_points = max(0, profile.total_points - pts)
                    profile.save()
                    Notification.objects.create(
                        user=u,
                        message=f"L'administrateur a retire {pts} points de votre compte. "
                                f"Nouveau total : {profile.total_points} pts"
                    )
                    messages.success(request, f"-{pts} pts retires de '{u.username}'. Total : {profile.total_points} pts")
                else:
                    messages.warning(request, "Entrez un nombre positif.")
            except ValueError:
                messages.error(request, "Valeur invalide.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/points_form.html', {
            'title':        f'Retirer des points — {u.username}',
            'subtitle':     f'Points actuels : {profile.total_points}',
            'action_label': 'Retirer',
            'user_obj':     u,
            'form_url':     reverse('admin:user_rem_points', args=[pk]),
            'btn_color':    'danger',
            'opts':         self.model._meta,
        })

    def v_reset_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        profile, _ = UserProfile.objects.get_or_create(user=u)
        before = profile.total_points
        profile.total_points = 0
        profile.save()
        Notification.objects.create(
            user=u,
            message="Vos points ont ete reinitialises a 0 par l'administrateur."
        )
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
                name = u.username
                u.delete()
                messages.success(request, f"Compte '{name}' supprime definitivement.")
            else:
                messages.error(request, "Confirmation incorrecte. Compte non supprime.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/confirm_delete_account.html', {
            'user_obj': u,
            'form_url': reverse('admin:user_del_account', args=[pk]),
            'opts':     self.model._meta,
        })

    def v_reset_all(self, request):
        if request.method == 'POST':
            if request.POST.get('confirm', '') == 'REINITIALISER':
                affected = list(UserProfile.objects.exclude(total_points=0))
                for p in affected:
                    Notification.objects.create(
                        user=p.user,
                        message="Reinitialisation globale : vos points ont ete remis a 0 par l'administrateur."
                    )
                count = len(affected)
                UserProfile.objects.all().update(total_points=0)
                messages.success(request, f"Points reinitialises pour tous les utilisateurs ({count} affectes).")
            else:
                messages.error(request, "Confirmation incorrecte. Action annulee.")
            return redirect('admin:auth_user_changelist')

        total_pts   = UserProfile.objects.aggregate(t=Sum('total_points'))['t'] or 0
        total_users = UserProfile.objects.count()
        return render(request, 'admin/reset_all_points.html', {
            'total_users': total_users,
            'total_pts':   total_pts,
            'form_url':    reverse('admin:reset_all_points'),
            'opts':        self.model._meta,
        })

    # ─── Display columns ───────────────────────────────────────────────────────
    def username_display(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.pk])
        return format_html('<a href="{}" style="font-weight:700;color:#D4A017;">{}</a>', url, obj.username)
    username_display.short_description = "Utilisateur"

    def full_name(self, obj):
        n = f"{obj.first_name} {obj.last_name}".strip()
        return format_html('<span style="color:#E8E8F0;">{}</span>', n or '—')
    full_name.short_description = "Nom"

    def points_display(self, obj):
        try:
            pts = obj.profile.total_points
        except Exception:
            pts = 0
        color = '#2ecc71' if pts >= 50 else '#f39c12' if pts >= 20 else '#8892A4'
        return format_html('<strong style="color:{};font-size:13px;">{} pts</strong>', color, pts)
    points_display.short_description = "Points"

    def status_display(self, obj):
        try:
            blocked = obj.profile.is_blocked
        except Exception:
            blocked = False
        if blocked:
            return format_html(
                '<span style="background:rgba(231,76,60,.2);color:#e74c3c;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;border:1px solid rgba(231,76,60,.3);">BLOQUE</span>'
            )
        return format_html(
            '<span style="background:rgba(46,204,113,.2);color:#2ecc71;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;border:1px solid rgba(46,204,113,.3);">ACTIF</span>'
        )
    status_display.short_description = "Statut"

    def admin_actions(self, obj):
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
            f'<a href="{ub_url}" class="action-btn action-btn-unblock">Debloquer</a>'
            if blocked else
            f'<a href="{b_url}" class="action-btn action-btn-block">Bloquer</a>'
        )

        return format_html(
            '{}'
            '<a href="{}" class="action-btn action-btn-pts-add">+Pts</a>'
            '<a href="{}" class="action-btn action-btn-pts-rem">-Pts</a>'
            '<a href="{}" class="action-btn action-btn-reset"'
            ' onclick="return confirm(\'Reinitialiser les points de {} ?\')">ResetPts</a>'
            '<a href="{}" class="action-btn action-btn-cert">Certificat</a>'
            '<a href="{}" class="action-btn action-btn-hist"'
            ' onclick="return confirm(\'Supprimer l\\\'historique de {} ?\')">Historique</a>'
            '<a href="{}" class="action-btn action-btn-delete">Supprimer</a>',
            format_html(toggle),
            ap_url, rp_url,
            rs_url, obj.username,
            ct_url,
            dh_url, obj.username,
            da_url,
        )
    admin_actions.short_description = "Actions rapides"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['reset_all_url'] = reverse('admin:reset_all_points')
        return super().changelist_view(request, extra_context=extra_context)

    # ─── Bulk actions ──────────────────────────────────────────────────────────
    def bulk_block(self, request, queryset):
        for u in queryset:
            try:
                u.profile.is_blocked = True; u.profile.save()
            except Exception:
                pass
        messages.success(request, f"{queryset.count()} compte(s) bloque(s).")
    bulk_block.short_description = "Bloquer les comptes selectionnes"

    def bulk_unblock(self, request, queryset):
        for u in queryset:
            try:
                u.profile.is_blocked = False; u.profile.blocked_reason = ''; u.profile.save()
            except Exception:
                pass
        messages.success(request, f"{queryset.count()} compte(s) debloque(s).")
    bulk_unblock.short_description = "Debloquer les comptes selectionnes"

    def bulk_clear_history(self, request, queryset):
        total = 0
        for u in queryset:
            c = UserAnswer.objects.filter(user=u).count()
            UserAnswer.objects.filter(user=u).delete()
            total += c
        messages.success(request, f"Historique supprime pour {queryset.count()} utilisateur(s) ({total} reponses).")
    bulk_clear_history.short_description = "Supprimer l'historique des selectionnes"

    def bulk_reset_points(self, request, queryset):
        count = 0
        for u in queryset:
            try:
                if u.profile.total_points > 0:
                    u.profile.total_points = 0; u.profile.save()
                    Notification.objects.create(user=u, message="Vos points ont ete reinitialises a 0 par l'administrateur.")
                    count += 1
            except Exception:
                pass
        messages.success(request, f"Points reinitialises pour {count} utilisateur(s).")
    bulk_reset_points.short_description = "Reinitialiser les points des selectionnes"

    def reset_points_ALL(self, request, queryset):
        return redirect(reverse('admin:reset_all_points'))
    reset_points_ALL.short_description = "Reinitialiser les points de TOUS les utilisateurs"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ── UserProfile ────────────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user_link', 'points_col', 'status_col', 'phone', 'wa_link', 'created_at')
    list_filter   = ('is_blocked',)
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('created_at', 'pwd_display')
    list_per_page = 25
    actions = ['block_sel', 'unblock_sel', 'reset_pts_sel']

    fieldsets = (
        ('Utilisateur', {'fields': ('user', 'avatar', 'bio', 'phone', 'whatsapp')}),
        ('Points',      {'fields': ('total_points',)}),
        ('Compte',      {'fields': ('is_blocked', 'blocked_reason'), 'classes': ('collapse',)}),
        ('Securite',    {'fields': ('pwd_display',), 'classes': ('collapse',)}),
        ('Date',        {'fields': ('created_at',),  'classes': ('collapse',)}),
    )

    def pwd_display(self, obj):
        return format_html(
            '<code style="background:#0D0D14;color:#D4A017;padding:10px 14px;border-radius:8px;'
            'display:block;word-break:break-all;font-size:11px;line-height:1.6;">{}</code>',
            obj.user.password
        )
    pwd_display.short_description = "Hash du mot de passe"

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="color:#D4A017;font-weight:700;">{}</a>', url, obj.user.username)
    user_link.short_description = "Utilisateur"

    def points_col(self, obj):
        c = '#2ecc71' if obj.total_points >= 50 else '#f39c12' if obj.total_points >= 20 else '#8892A4'
        return format_html('<strong style="color:{};">{} pts</strong>', c, obj.total_points)
    points_col.short_description = "Points"

    def status_col(self, obj):
        if obj.is_blocked:
            return format_html('<span style="color:#e74c3c;font-weight:700;">BLOQUE</span>')
        return format_html('<span style="color:#2ecc71;font-weight:700;">ACTIF</span>')
    status_col.short_description = "Statut"

    def wa_link(self, obj):
        if obj.whatsapp:
            clean = obj.whatsapp.replace('+', '').replace(' ', '')
            return format_html('<a href="https://wa.me/{}" target="_blank" style="color:#25D366;font-weight:700;">WhatsApp</a>', clean)
        return '—'
    wa_link.short_description = "WhatsApp"

    def block_sel(self, request, queryset):
        queryset.update(is_blocked=True)
        messages.success(request, f"{queryset.count()} compte(s) bloque(s).")
    block_sel.short_description = "Bloquer"

    def unblock_sel(self, request, queryset):
        queryset.update(is_blocked=False, blocked_reason='')
        messages.success(request, f"{queryset.count()} compte(s) debloque(s).")
    unblock_sel.short_description = "Debloquer"

    def reset_pts_sel(self, request, queryset):
        queryset.update(total_points=0)
        messages.success(request, f"Points reinitialises pour {queryset.count()} profil(s).")
    reset_pts_sel.short_description = "Reinitialiser les points"


# ── DailyQuestion ──────────────────────────────────────────────────────────────
@admin.register(DailyQuestion)
class DailyQuestionAdmin(admin.ModelAdmin):
    list_display   = ('q_preview', 'date_col', 'category', 'answers_preview',
                      'correct_col', 'points', 'is_active', 'stats_col', 'del_btn')
    list_filter    = ('is_active', 'category', 'date')
    search_fields  = ('question_text', 'option_a', 'option_b', 'option_c', 'option_d')
    date_hierarchy = 'date'
    list_per_page  = 15
    actions        = ['delete_past', 'activate_sel', 'deactivate_sel']

    fieldsets = (
        ('Question', {
            'fields': ('question_text', 'category', 'date', 'points', 'is_active', 'created_by'),
            'description': 'Saisissez la question et ses parametres.',
        }),
        ('Les 4 reponses', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'),
            'description': (
                'Remplissez les 4 reponses A, B, C et D. '
                'Puis selectionnez la lettre de la bonne reponse.'
            ),
        }),
    )

    def q_preview(self, obj):
        t = obj.question_text
        return format_html('<span style="font-weight:600;color:#E8E8F0;">{}</span>',
                           t[:70] + '...' if len(t) > 70 else t)
    q_preview.short_description = "Question"

    def answers_preview(self, obj):
        def tag(letter, text):
            s = text[:26] + '…' if len(text) > 26 else text
            return (f'<span style="display:inline-block;background:rgba(212,160,23,.1);'
                    f'border:1px solid rgba(212,160,23,.2);border-radius:5px;'
                    f'padding:1px 6px;margin:2px;font-size:11px;">'
                    f'<strong style="color:#D4A017;">{letter}</strong> {s}</span>')
        return format_html(
            '<div style="line-height:2;">{}{}{}{}</div>',
            format_html(tag('A', obj.option_a)),
            format_html(tag('B', obj.option_b)),
            format_html(tag('C', obj.option_c)),
            format_html(tag('D', obj.option_d)),
        )
    answers_preview.short_description = "Reponses A / B / C / D"

    def correct_col(self, obj):
        mapping = {'A': obj.option_a, 'B': obj.option_b, 'C': obj.option_c, 'D': obj.option_d}
        text  = mapping.get(obj.correct_answer, '')
        short = text[:22] + '…' if len(text) > 22 else text
        return format_html(
            '<span style="background:rgba(46,204,113,.15);color:#2ecc71;'
            'border:1px solid rgba(46,204,113,.3);border-radius:7px;'
            'padding:2px 8px;font-size:11px;font-weight:700;">{} — {}</span>',
            obj.correct_answer, short
        )
    correct_col.short_description = "Bonne reponse"

    def date_col(self, obj):
        today = datetime.date.today()
        if obj.date == today:
            return format_html("<strong style='color:#D4A017;'>{} (Auj.)</strong>", obj.date)
        if obj.date < today:
            return format_html("<span style='color:#8892A4;'>{}</span>", obj.date)
        return format_html("<span style='color:#3498db;'>{}</span>", obj.date)
    date_col.short_description = "Date"

    def stats_col(self, obj):
        total   = obj.user_answers.count()
        correct = obj.user_answers.filter(is_correct=True).count()
        pct     = round(correct / total * 100) if total else 0
        return format_html(
            "<span style='color:#8892A4;font-size:11px;'>{} rep. </span>"
            "<span style='color:#2ecc71;font-size:11px;'>{} OK ({}%)</span>",
            total, correct, pct
        )
    stats_col.short_description = "Stats"

    def del_btn(self, obj):
        if obj.date < datetime.date.today():
            url = reverse('admin:quiz_dailyquestion_delete', args=[obj.pk])
            return format_html(
                "<a href='{}' class='action-btn action-btn-delete' "
                "onclick=\"return confirm('Supprimer cette question passee ?')\">Supprimer</a>", url
            )
        return format_html("<span style='color:#8892A4;font-size:11px;'>Active</span>")
    del_btn.short_description = "Suppr."

    def delete_past(self, request, queryset):
        past = queryset.filter(date__lt=datetime.date.today())
        c = past.count(); past.delete()
        messages.success(request, f"{c} question(s) passee(s) supprimee(s).")
    delete_past.short_description = "Supprimer les questions passees"

    def activate_sel(self, request, queryset):
        queryset.update(is_active=True)
        messages.success(request, f"{queryset.count()} question(s) activee(s).")
    activate_sel.short_description = "Activer"

    def deactivate_sel(self, request, queryset):
        queryset.update(is_active=False)
        messages.success(request, f"{queryset.count()} question(s) desactivee(s).")
    deactivate_sel.short_description = "Desactiver"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ── UserAnswer ─────────────────────────────────────────────────────────────────
@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display    = ('user', 'q_short', 'selected_col', 'correct_col', 'points_earned', 'answered_at')
    list_filter     = ('is_correct', 'answered_at', 'selected_answer')
    search_fields   = ('user__username', 'question__question_text')
    readonly_fields = ('user', 'question', 'selected_answer', 'is_correct', 'points_earned', 'answered_at')
    list_per_page   = 30
    date_hierarchy  = 'answered_at'

    def q_short(self, obj):
        return obj.question.question_text[:55] + '...'
    q_short.short_description = "Question"

    def selected_col(self, obj):
        mapping = {
            'A': obj.question.option_a, 'B': obj.question.option_b,
            'C': obj.question.option_c, 'D': obj.question.option_d,
        }
        text  = mapping.get(obj.selected_answer, '')
        short = text[:22] + '…' if len(text) > 22 else text
        return format_html(
            '<span style="background:rgba(52,152,219,.12);color:#3498db;padding:2px 8px;'
            'border-radius:6px;font-size:11px;font-weight:700;">{} — {}</span>',
            obj.selected_answer, short
        )
    selected_col.short_description = "Reponse choisie"

    def correct_col(self, obj):
        if obj.is_correct:
            return format_html('<span style="color:#2ecc71;font-weight:700;">Correct</span>')
        return format_html('<span style="color:#e74c3c;font-weight:700;">Incorrect</span>')
    correct_col.short_description = "Resultat"


# ── Certificate ────────────────────────────────────────────────────────────────
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display  = ('user_col', 'title', 'points_required', 'image_preview',
                     'issued_at', 'issued_by_col', 'download_link')
    list_filter   = ('issued_at',)
    search_fields = ('user__username', 'title')
    list_per_page = 20
    readonly_fields = ('issued_at', 'issued_by', 'image_preview_large')
    actions = ['notify_selected']

    fieldsets = (
        ('Destinataire', {
            'fields': ('user', 'issued_by'),
            'description': 'Selectionnez l\'utilisateur qui recevra ce certificat.',
        }),
        ('Contenu du certificat', {
            'fields': ('title', 'description', 'points_required'),
            'description': 'Titre et description du certificat.',
        }),
        ('Photo / Image du certificat', {
            'fields': ('certificate_image', 'image_preview_large'),
            'description': (
                'Uploadez la photo ou l\'image du certificat depuis votre stockage local. '
                'Formats acceptes : JPG, PNG, GIF, WEBP. '
                'L\'utilisateur pourra voir et telecharger cette image depuis son profil.'
            ),
        }),
        ('Date d\'emission', {
            'fields': ('issued_at',),
            'classes': ('collapse',),
        }),
    )

    def user_col(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="color:#D4A017;font-weight:700;">{}</a>', url, obj.user.username)
    user_col.short_description = "Utilisateur"

    def issued_by_col(self, obj):
        if obj.issued_by:
            return format_html('<span style="color:#8892A4;">{}</span>', obj.issued_by.username)
        return '—'
    issued_by_col.short_description = "Emis par"

    def image_preview(self, obj):
        """Small thumbnail in list view."""
        if obj.certificate_image:
            return format_html(
                '<img src="{}" style="height:48px;width:auto;border-radius:6px;'
                'border:1px solid rgba(212,160,23,.4);object-fit:cover;" />',
                obj.certificate_image.url
            )
        return format_html('<span style="color:#8892A4;font-size:11px;">Aucune image</span>')
    image_preview.short_description = "Apercu"

    def image_preview_large(self, obj):
        """Large preview in detail view."""
        if obj.certificate_image:
            return format_html(
                '<div style="margin-top:8px;">'
                '<img src="{}" style="max-width:400px;max-height:280px;border-radius:10px;'
                'border:2px solid rgba(212,160,23,.4);display:block;" />'
                '<div style="color:#8892A4;font-size:11px;margin-top:6px;">'
                'Fichier : {}</div></div>',
                obj.certificate_image.url,
                obj.certificate_image.name
            )
        return format_html(
            '<span style="color:#8892A4;font-size:12px;">'
            'Aucune image uploadee. Utilisez le champ ci-dessus pour uploader une photo.</span>'
        )
    image_preview_large.short_description = "Apercu de l'image"

    def download_link(self, obj):
        if obj.certificate_image:
            return format_html(
                '<a href="{}" target="_blank" download '
                'style="color:#3498db;font-weight:600;font-size:12px;">'
                'Telecharger</a>',
                obj.certificate_image.url
            )
        return format_html('<span style="color:#8892A4;font-size:11px;">—</span>')
    download_link.short_description = "Telecharger"

    def notify_selected(self, request, queryset):
        count = 0
        for cert in queryset:
            Notification.objects.create(
                user=cert.user,
                message=f"Vous avez recu un certificat : '{cert.title}'. "
                        f"Consultez votre profil pour voir et telecharger votre image."
            )
            count += 1
        messages.success(request, f"Notifications envoyees pour {count} certificat(s).")
    notify_selected.short_description = "Envoyer notification certificat"

    def save_model(self, request, obj, form, change):
        # Auto-set issued_by on creation
        if not change and not obj.issued_by_id:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)
        # Send automatic notification on creation
        if not change:
            msg = f"Felicitations ! Vous avez recu un certificat : '{obj.title}'."
            if obj.certificate_image:
                msg += " Consultez votre profil pour voir et telecharger votre image de certificat."
            Notification.objects.create(user=obj.user, message=msg)


# ── Notification ───────────────────────────────────────────────────────────────
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'msg_short', 'is_read', 'created_at')
    list_filter   = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    list_per_page = 30
    actions       = ['mark_read', 'mark_unread']

    def msg_short(self, obj):
        return obj.message[:90] + '...' if len(obj.message) > 90 else obj.message
    msg_short.short_description = "Message"

    def mark_read(self, request, queryset):
        queryset.update(is_read=True)
        messages.success(request, f"{queryset.count()} notification(s) marquee(s) comme lues.")
    mark_read.short_description = "Marquer comme lu"

    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)
        messages.success(request, f"{queryset.count()} notification(s) marquee(s) comme non lues.")
    mark_unread.short_description = "Marquer comme non lu"
