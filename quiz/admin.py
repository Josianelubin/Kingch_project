from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse, path
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.db.models import Sum, Count
from .models import UserProfile, DailyQuestion, UserAnswer, Certificate, Notification
import datetime

# ─── site config ──────────────────────────────────────────────────────────────
admin.site.site_header = "KING CH"
admin.site.site_title  = "KING CH Admin"
admin.site.index_title = "Tableau de bord"


# ─── Inlines ──────────────────────────────────────────────────────────────────
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profil & Securite"
    fields = ('phone', 'whatsapp', 'bio', 'total_points', 'is_blocked', 'blocked_reason', 'avatar')
    readonly_fields = ('total_points',)


class CertificateInline(admin.TabularInline):
    model = Certificate
    fk_name = 'user'
    extra = 0
    readonly_fields = ('issued_at', 'issued_by')
    fields = ('title', 'description', 'points_required', 'certificate_file', 'issued_at')
    show_change_link = True


# ─── CustomUserAdmin ──────────────────────────────────────────────────────────
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, CertificateInline)
    list_display = (
        'username_display', 'full_name', 'email',
        'points_display', 'status_display',
        'date_joined', 'admin_actions',
    )
    list_filter   = ('is_active', 'is_staff', 'profile__is_blocked', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 25
    actions = ['block_users', 'unblock_users', 'clear_history_bulk',
               'reset_points_selected', 'reset_points_ALL']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/block/',         self.admin_site.admin_view(self.view_block),       name='user_block'),
            path('<int:pk>/unblock/',       self.admin_site.admin_view(self.view_unblock),     name='user_unblock'),
            path('<int:pk>/add-points/',    self.admin_site.admin_view(self.view_add_pts),     name='user_add_points'),
            path('<int:pk>/rem-points/',    self.admin_site.admin_view(self.view_rem_pts),     name='user_rem_points'),
            path('<int:pk>/reset-points/',  self.admin_site.admin_view(self.view_reset_pts),   name='user_reset_points'),
            path('<int:pk>/del-history/',   self.admin_site.admin_view(self.view_del_history), name='user_del_history'),
            path('<int:pk>/del-account/',   self.admin_site.admin_view(self.view_del_account), name='user_del_account'),
            path('reset-all-points/',       self.admin_site.admin_view(self.view_reset_all),   name='reset_all_points'),
        ]
        return custom + urls

    # ── VIEWS ──────────────────────────────────────────────────────────────────
    def view_block(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        u.profile.is_blocked = True
        u.profile.save()
        messages.success(request, f"Compte '{u.username}' bloque.")
        return redirect('admin:auth_user_changelist')

    def view_unblock(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        u.profile.is_blocked = False
        u.profile.blocked_reason = ''
        u.profile.save()
        messages.success(request, f"Compte '{u.username}' debloque.")
        return redirect('admin:auth_user_changelist')

    def view_add_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            try:
                pts = max(0, int(request.POST.get('points', 0)))
                if pts > 0:
                    u.profile.total_points += pts
                    u.profile.save()
                    Notification.objects.create(
                        user=u,
                        message=f"L'administrateur a ajoute {pts} points a votre compte. Total: {u.profile.total_points} pts"
                    )
                    messages.success(request, f"+{pts} points ajoutes a {u.username}. Total: {u.profile.total_points} pts")
            except ValueError:
                messages.error(request, "Valeur invalide.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/points_form.html', {
            'title': f'Ajouter des points - {u.username}',
            'subtitle': f'Points actuels: {u.profile.total_points}',
            'action_label': 'Ajouter',
            'user_obj': u,
            'form_url': reverse('admin:user_add_points', args=[pk]),
            'btn_color': 'success',
            'opts': self.model._meta,
        })

    def view_rem_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            try:
                pts = max(0, int(request.POST.get('points', 0)))
                if pts > 0:
                    before = u.profile.total_points
                    u.profile.total_points = max(0, before - pts)
                    u.profile.save()
                    Notification.objects.create(
                        user=u,
                        message=f"L'administrateur a retire {pts} points de votre compte. Total: {u.profile.total_points} pts"
                    )
                    messages.success(request, f"-{pts} points retires de {u.username}. Total: {u.profile.total_points} pts")
            except ValueError:
                messages.error(request, "Valeur invalide.")
            return redirect('admin:auth_user_changelist')
        return render(request, 'admin/points_form.html', {
            'title': f'Retirer des points - {u.username}',
            'subtitle': f'Points actuels: {u.profile.total_points}',
            'action_label': 'Retirer',
            'user_obj': u,
            'form_url': reverse('admin:user_rem_points', args=[pk]),
            'btn_color': 'danger',
            'opts': self.model._meta,
        })

    def view_reset_pts(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        before = u.profile.total_points
        u.profile.total_points = 0
        u.profile.save()
        Notification.objects.create(
            user=u,
            message="Vos points ont ete reinitialises a 0 par l'administrateur."
        )
        messages.success(request, f"Points de '{u.username}' reinitialises (etaient: {before}).")
        return redirect('admin:auth_user_changelist')

    def view_del_history(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        count = UserAnswer.objects.filter(user=u).count()
        UserAnswer.objects.filter(user=u).delete()
        messages.success(request, f"Historique de '{u.username}' supprime ({count} reponses).")
        return redirect('admin:auth_user_changelist')

    def view_del_account(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            confirm = request.POST.get('confirm', '')
            if confirm == u.username:
                username = u.username
                u.delete()
                messages.success(request, f"Compte '{username}' supprime definitivement.")
                return redirect('admin:auth_user_changelist')
            else:
                messages.error(request, "Confirmation incorrecte. Compte non supprime.")
                return redirect('admin:auth_user_changelist')
        return render(request, 'admin/confirm_delete_account.html', {
            'user_obj': u,
            'form_url': reverse('admin:user_del_account', args=[pk]),
            'opts': self.model._meta,
        })

    def view_reset_all(self, request):
        """Reinitialiser les points de TOUS les utilisateurs"""
        if request.method == 'POST':
            confirm = request.POST.get('confirm', '')
            if confirm == 'REINITIALISER':
                count = UserProfile.objects.exclude(total_points=0).count()
                # Notify all before reset
                for profile in UserProfile.objects.all():
                    if profile.total_points > 0:
                        Notification.objects.create(
                            user=profile.user,
                            message="Reinitialisation globale: vos points ont ete remis a 0 par l'administrateur."
                        )
                UserProfile.objects.all().update(total_points=0)
                messages.success(request, f"Points reinitialises pour tous les utilisateurs ({count} affectes).")
                return redirect('admin:auth_user_changelist')
            else:
                messages.error(request, "Confirmation incorrecte. Action annulee.")
                return redirect('admin:auth_user_changelist')
        total_users = UserProfile.objects.count()
        total_pts   = UserProfile.objects.aggregate(t=Sum('total_points'))['t'] or 0
        return render(request, 'admin/reset_all_points.html', {
            'total_users': total_users,
            'total_pts': total_pts,
            'form_url': reverse('admin:reset_all_points'),
            'opts': self.model._meta,
        })

    # ── DISPLAY COLUMNS ────────────────────────────────────────────────────────
    def username_display(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.pk])
        return format_html('<a href="{}" style="font-weight:700;color:#D4A017;">{}</a>', url, obj.username)
    username_display.short_description = "Utilisateur"

    def full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return format_html('<span style="color:#E8E8F0;">{}</span>', name or '—')
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
                'border-radius:20px;font-size:11px;font-weight:700;border:1px solid rgba(231,76,60,.3);">'
                'BLOQUE</span>')
        return format_html(
            '<span style="background:rgba(46,204,113,.2);color:#2ecc71;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;border:1px solid rgba(46,204,113,.3);">'
            'ACTIF</span>')
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
            ' onclick="return confirm(\'Reinitialiser les points de {}?\')">Reset Pts</a>'
            '<a href="{}" class="action-btn action-btn-cert">Certificat</a>'
            '<a href="{}" class="action-btn action-btn-hist"'
            ' onclick="return confirm(\'Supprimer historique de {}?\')">Historique</a>'
            '<a href="{}" class="action-btn action-btn-delete">Supprimer</a>',
            format_html(toggle),
            ap_url, rp_url,
            rs_url, obj.username,
            ct_url,
            dh_url, obj.username,
            da_url,
        )
    admin_actions.short_description = "Actions"

    # ── CHANGELIST extra button ─────────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['reset_all_url'] = reverse('admin:reset_all_points')
        return super().changelist_view(request, extra_context=extra_context)

    # ── BULK ACTIONS ───────────────────────────────────────────────────────────
    def block_users(self, request, queryset):
        for u in queryset:
            try:
                u.profile.is_blocked = True; u.profile.save()
            except Exception: pass
        messages.success(request, f"{queryset.count()} compte(s) bloque(s).")
    block_users.short_description = "Bloquer les comptes selectionnes"

    def unblock_users(self, request, queryset):
        for u in queryset:
            try:
                u.profile.is_blocked = False; u.profile.blocked_reason = ''; u.profile.save()
            except Exception: pass
        messages.success(request, f"{queryset.count()} compte(s) debloque(s).")
    unblock_users.short_description = "Debloquer les comptes selectionnes"

    def clear_history_bulk(self, request, queryset):
        total = 0
        for u in queryset:
            c = UserAnswer.objects.filter(user=u).count()
            UserAnswer.objects.filter(user=u).delete()
            total += c
        messages.success(request, f"Historique supprime pour {queryset.count()} utilisateur(s) ({total} reponses).")
    clear_history_bulk.short_description = "Supprimer l'historique des selectionnes"

    def reset_points_selected(self, request, queryset):
        count = 0
        for u in queryset:
            try:
                if u.profile.total_points > 0:
                    u.profile.total_points = 0; u.profile.save()
                    Notification.objects.create(user=u, message="Vos points ont ete reinitialises a 0 par l'administrateur.")
                    count += 1
            except Exception: pass
        messages.success(request, f"Points reinitialises pour {count} utilisateur(s).")
    reset_points_selected.short_description = "Reinitialiser les points des selectionnes"

    def reset_points_ALL(self, request, queryset):
        """Redirect to confirmation page for resetting ALL users"""
        return redirect(reverse('admin:reset_all_points'))
    reset_points_ALL.short_description = "Reinitialiser les points de TOUS les utilisateurs"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ─── UserProfile ──────────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user_link', 'points_col', 'status_col', 'phone', 'whatsapp_link', 'pwd_col', 'created_at')
    list_filter   = ('is_blocked',)
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('created_at', 'pwd_display')
    list_per_page = 25
    actions = ['block_sel', 'unblock_sel', 'reset_pts_sel']

    fieldsets = (
        ('Utilisateur',  {'fields': ('user', 'avatar', 'bio', 'phone', 'whatsapp')}),
        ('Points',       {'fields': ('total_points',)}),
        ('Compte',       {'fields': ('is_blocked', 'blocked_reason'), 'classes': ('collapse',)}),
        ('Securite',     {'fields': ('pwd_display',), 'classes': ('collapse',)}),
        ('Date',         {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def pwd_display(self, obj):
        return format_html(
            '<code style="background:#0D0D14;color:#D4A017;padding:10px 14px;border-radius:8px;'
            'display:block;word-break:break-all;font-size:11px;line-height:1.6;">{}</code>',
            obj.user.password
        )
    pwd_display.short_description = "Hash du mot de passe"

    def pwd_col(self, obj):
        alg = obj.user.password.split('$')[0] if '$' in obj.user.password else 'unknown'
        return format_html('<code style="color:#D4A017;font-size:10px;">{}</code>', alg)
    pwd_col.short_description = "Algo"

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="color:#D4A017;font-weight:700;">{}</a>', url, obj.user.username)
    user_link.short_description = "Utilisateur"

    def points_col(self, obj):
        color = '#2ecc71' if obj.total_points >= 50 else '#f39c12' if obj.total_points >= 20 else '#8892A4'
        return format_html('<strong style="color:{};">{} pts</strong>', color, obj.total_points)
    points_col.short_description = "Points"

    def status_col(self, obj):
        if obj.is_blocked:
            return format_html('<span style="color:#e74c3c;font-weight:700;">BLOQUE</span>')
        return format_html('<span style="color:#2ecc71;font-weight:700;">ACTIF</span>')
    status_col.short_description = "Statut"

    def whatsapp_link(self, obj):
        if obj.whatsapp:
            clean = obj.whatsapp.replace('+', '').replace(' ', '')
            return format_html('<a href="https://wa.me/{}" target="_blank" style="color:#25D366;font-weight:700;">WhatsApp</a>', clean)
        return '—'
    whatsapp_link.short_description = "WhatsApp"

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


# ─── DailyQuestion ────────────────────────────────────────────────────────────
@admin.register(DailyQuestion)
class DailyQuestionAdmin(admin.ModelAdmin):
    list_display   = ('q_short', 'date_col', 'category', 'correct_answer', 'points', 'is_active', 'stats_col', 'del_btn')
    list_filter    = ('is_active', 'category', 'date')
    search_fields  = ('question_text',)
    date_hierarchy = 'date'
    list_per_page  = 20
    actions = ['delete_past', 'activate_sel', 'deactivate_sel']

    fieldsets = (
        ('Question',           {'fields': ('question_text', 'category', 'date', 'points', 'is_active', 'created_by')}),
        ('Options de reponse', {'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')}),
    )

    def q_short(self, obj):
        t = obj.question_text
        return t[:65] + '...' if len(t) > 65 else t
    q_short.short_description = "Question"

    def date_col(self, obj):
        today = datetime.date.today()
        if obj.date == today:
            return format_html("<strong style='color:#D4A017;'>{} (Aujourd'hui)</strong>", obj.date)
        if obj.date < today:
            return format_html("<span style='color:#8892A4;'>{} (Passe)</span>", obj.date)
        return format_html("<span style='color:#3498db;'>{}</span>", obj.date)
    date_col.short_description = "Date"

    def stats_col(self, obj):
        total   = obj.user_answers.count()
        correct = obj.user_answers.filter(is_correct=True).count()
        pct     = round(correct / total * 100) if total else 0
        return format_html(
            "<span style='color:#8892A4;'>{} rep. | </span><span style='color:#2ecc71;'>{} OK ({}%)</span>",
            total, correct, pct)
    stats_col.short_description = "Stats"

    def del_btn(self, obj):
        if obj.date < datetime.date.today():
            url = reverse('admin:quiz_dailyquestion_delete', args=[obj.pk])
            return format_html(
                "<a href='{}' class='action-btn action-btn-delete' "
                "onclick=\"return confirm('Supprimer cette question passee?')\">Supprimer</a>", url)
        return format_html("<span style='color:#8892A4;font-size:11px;'>Active</span>")
    del_btn.short_description = "Suppr."

    def delete_past(self, request, queryset):
        past  = queryset.filter(date__lt=datetime.date.today())
        count = past.count(); past.delete()
        messages.success(request, f"{count} question(s) passee(s) supprimee(s).")
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


# ─── UserAnswer ───────────────────────────────────────────────────────────────
@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display   = ('user', 'q_short', 'selected_answer', 'correct_col', 'points_earned', 'answered_at')
    list_filter    = ('is_correct', 'answered_at')
    search_fields  = ('user__username', 'question__question_text')
    readonly_fields = ('user', 'question', 'selected_answer', 'is_correct', 'points_earned', 'answered_at')
    list_per_page  = 30
    date_hierarchy = 'answered_at'

    def q_short(self, obj):
        return obj.question.question_text[:55] + '...'
    q_short.short_description = "Question"

    def correct_col(self, obj):
        if obj.is_correct:
            return format_html("<span style='color:#2ecc71;font-weight:700;'>Correcte</span>")
        return format_html("<span style='color:#e74c3c;font-weight:700;'>Incorrecte</span>")
    correct_col.short_description = "Resultat"


# ─── Certificate ──────────────────────────────────────────────────────────────
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display  = ('user_col', 'title', 'points_required', 'issued_at', 'issued_by', 'file_link')
    list_filter   = ('issued_at',)
    search_fields = ('user__username', 'title')
    list_per_page = 20
    actions = ['notify_selected']

    fieldsets = (
        ('Destinataire',        {'fields': ('user', 'issued_by')}),
        ('Contenu du certificat', {'fields': ('title', 'description', 'points_required', 'certificate_file')}),
    )

    def user_col(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}" style="color:#D4A017;font-weight:700;">{}</a>', url, obj.user.username)
    user_col.short_description = "Utilisateur"

    def file_link(self, obj):
        if obj.certificate_file:
            return format_html('<a href="{}" target="_blank" style="color:#3498db;font-weight:600;">Telecharger</a>', obj.certificate_file.url)
        return format_html('<span style="color:#8892A4;">Aucun fichier</span>')
    file_link.short_description = "Fichier"

    def notify_selected(self, request, queryset):
        for cert in queryset:
            Notification.objects.create(user=cert.user, message=f"Vous avez recu un certificat: {cert.title}")
        messages.success(request, f"Notifications envoyees pour {queryset.count()} certificat(s).")
    notify_selected.short_description = "Envoyer notification certificat"

    def save_model(self, request, obj, form, change):
        if not obj.issued_by:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            Notification.objects.create(
                user=obj.user,
                message=f"Felicitations! Vous avez recu un certificat: {obj.title}"
            )


# ─── Notification ─────────────────────────────────────────────────────────────
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'msg_short', 'is_read', 'created_at')
    list_filter   = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    actions = ['mark_read']

    def msg_short(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    msg_short.short_description = "Message"

    def mark_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_read.short_description = "Marquer comme lu"
