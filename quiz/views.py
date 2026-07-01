from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from .models import UserProfile, DailyQuestion, UserAnswer, Certificate, Notification, Referral
from .forms import (
    CustomLoginForm, CustomRegisterForm,
    UserProfileForm, UserSettingsForm, PasswordChangeCustomForm
)
import datetime


# ── Public ─────────────────────────────────────────────────────────────────────
def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'quiz/home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = CustomLoginForm()
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user:
                try:
                    if user.profile.is_blocked:
                        messages.error(request, "Votre compte est bloque. Contactez l'administrateur.")
                        return render(request, 'quiz/login.html', {'form': form})
                except Exception:
                    pass
                login(request, user)
                messages.success(request, f"Bienvenue, {user.first_name or user.username} !")
                return redirect('dashboard')
            else:
                messages.error(request, "Identifiants incorrects.")
    return render(request, 'quiz/login.html', {'form': form})


def register_view(request):
    """Registration — supports ?ref=CODE for referral."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    ref_code = request.GET.get('ref', '').strip().upper()
    form = CustomRegisterForm()
    if request.method == 'POST':
        form = CustomRegisterForm(data=request.POST)
        if form.is_valid():
            user = form.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            # Handle referral
            ref_code_post = request.POST.get('ref_code', '').strip().upper()
            if ref_code_post:
                try:
                    referrer_profile = UserProfile.objects.get(referral_code=ref_code_post)
                    if referrer_profile.user != user:
                        # Award 2 points to referrer
                        referrer_profile.total_points += 2
                        referrer_profile.referral_points_earned += 2
                        referrer_profile.save()
                        # Record referral
                        Referral.objects.create(
                            referrer=referrer_profile.user,
                            referred_user=user,
                            points_given=2,
                        )
                        profile.referred_by = referrer_profile.user
                        profile.save()
                        # Notify referrer
                        Notification.objects.create(
                            user=referrer_profile.user,
                            message=f"Votre ami {user.username} a rejoint KING CH grace a votre invitation ! +2 points bonus."
                        )
                        messages.success(request, f"Bienvenue ! Vous avez ete invite par {referrer_profile.user.username}.")
                except UserProfile.DoesNotExist:
                    messages.warning(request, "Code de parrainage invalide. Compte cree sans parrainage.")
            login(request, user)
            messages.success(request, f"Bienvenue sur KING CH, {user.username} !")
            return redirect('dashboard')
    return render(request, 'quiz/register.html', {'form': form, 'ref_code': ref_code})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Vous etes deconnecte. A bientot !")
    return redirect('login')


# ── Dashboard ──────────────────────────────────────────────────────────────────
@login_required
def dashboard_view(request):
    user    = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_blocked:
        logout(request)
        messages.error(request, "Votre compte a ete bloque. Contactez l'administrateur.")
        return redirect('login')

    today        = datetime.date.today()
    today_qs     = DailyQuestion.objects.filter(date=today, is_active=True)
    answered_ids = UserAnswer.objects.filter(user=user).values_list('question_id', flat=True)
    pending_qs   = today_qs.exclude(id__in=answered_ids)
    answered_today = today_qs.filter(id__in=answered_ids)

    points_today = UserAnswer.objects.filter(
        user=user, question__date=today
    ).aggregate(total=Sum('points_earned'))['total'] or 0

    certificates  = Certificate.objects.filter(user=user).order_by('-issued_at')
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]
    leaderboard   = UserProfile.objects.filter(is_blocked=False).order_by('-total_points')[:10]
    my_referrals  = Referral.objects.filter(referrer=user).count()

    return render(request, 'quiz/dashboard.html', {
        'profile':          profile,
        'today_questions':  today_qs,
        'pending_questions':pending_qs,
        'answered_today':   answered_today,
        'points_today':     points_today,
        'certificates':     certificates,
        'notifications':    notifications,
        'leaderboard':      leaderboard,
        'today':            today,
        'my_referrals':     my_referrals,
    })


def _check_leaderboard_notifications(user, profile):
    """
    Verifie le rang de l utilisateur apres avoir gagne des points.
    Envoie des notifications automatiques selon le rang atteint.
    """
    # Rang actuel (combien de profils ont PLUS de points que lui)
    rank = UserProfile.objects.filter(
        total_points__gt=profile.total_points,
        is_blocked=False
    ).count() + 1

    # Evite les doublons : ne notifie pas si le meme rang a deja ete notifie
    already_notified_key = f"Vous etes maintenant {rank}"
    already_sent = Notification.objects.filter(
        user=user,
        message__startswith=already_notified_key
    ).exists()

    if already_sent:
        return  # pas de doublon

    if rank == 1:
        # Devenu premier du classement
        Notification.objects.create(
            user=user,
            message=(
                f"Felicitations ! Vous etes maintenant 1er du classement KING CH "
                f"avec {profile.total_points} points. Vous etes le meilleur !"
            )
        )
        # Notifie aussi l ancien premier (l autre joueur qui perd sa place)
        ex_leaders = UserProfile.objects.filter(
            total_points__lte=profile.total_points,
            is_blocked=False
        ).exclude(user=user).order_by('-total_points')[:1]
        for ex in ex_leaders:
            Notification.objects.create(
                user=ex.user,
                message=(
                    f"{user.first_name or user.username} vient de vous depasser "
                    f"et prend la 1ere place du classement avec {profile.total_points} points. "
                    f"Repondez aux questions pour reprendre votre place !"
                )
            )

    elif rank == 2:
        Notification.objects.create(
            user=user,
            message=(
                f"Vous etes maintenant 2eme du classement avec {profile.total_points} points. "
                f"Encore un effort pour atteindre la 1ere place !"
            )
        )
    elif rank == 3:
        Notification.objects.create(
            user=user,
            message=(
                f"Vous etes maintenant 3eme du classement avec {profile.total_points} points. "
                f"Continuez, le podium est a vous !"
            )
        )
    elif rank <= 10:
        Notification.objects.create(
            user=user,
            message=(
                f"Vous etes maintenant {rank}eme du classement avec {profile.total_points} points. "
                f"Continuez vos efforts !"
            )
        )


# ── Quiz ───────────────────────────────────────────────────────────────────────
@login_required
def quiz_view(request, question_id):
    question   = get_object_or_404(DailyQuestion, id=question_id, is_active=True)
    user       = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_blocked:
        logout(request); return redirect('login')

    if UserAnswer.objects.filter(user=user, question=question).exists():
        messages.warning(request, "Vous avez deja repondu a cette question.")
        return redirect('dashboard')

    if request.method == 'POST':
        selected = request.POST.get('answer')

        # TIMEOUT : le temps est ecoule, on enregistre 0 point
        if selected == 'TIMEOUT':
            UserAnswer.objects.create(
                user=user, question=question,
                selected_answer='A',
                is_correct=False, points_earned=0
            )
            return redirect('dashboard')

        if selected in ['A', 'B', 'C', 'D']:
            is_correct = (selected == question.correct_answer)
            pts = question.points if is_correct else 0
            UserAnswer.objects.create(
                user=user, question=question,
                selected_answer=selected, is_correct=is_correct, points_earned=pts
            )
            if is_correct:
                profile.total_points += pts
                profile.save()
                messages.success(request, f"Bonne reponse ! +{pts} points !")
                # Verifie et notifie selon le rang atteint
                _check_leaderboard_notifications(user, profile)
            else:
                correct_text = getattr(question, f'option_{question.correct_answer.lower()}')
                messages.error(request,
                    f"Mauvaise reponse. La bonne reponse etait : ({question.correct_answer}) {correct_text}")
            return redirect('quiz_result', question_id=question.id)
        else:
            messages.error(request, "Veuillez selectionner une reponse.")

    from django.conf import settings as django_settings
    timer = getattr(django_settings, 'QUIZ_TIMER_SECONDS', 10)
    return render(request, 'quiz/quiz.html', {
        'question': question,
        'QUIZ_TIMER_SECONDS': timer,
    })


@login_required
def quiz_result_view(request, question_id):
    question = get_object_or_404(DailyQuestion, id=question_id)
    answer   = get_object_or_404(UserAnswer, user=request.user, question=question)

    # Rang actuel apres avoir repondu
    try:
        profile = request.user.profile
        current_rank = UserProfile.objects.filter(
            total_points__gt=profile.total_points,
            is_blocked=False
        ).count() + 1
    except Exception:
        current_rank = None

    return render(request, 'quiz/quiz_result.html', {
        'question':     question,
        'answer':       answer,
        'current_rank': current_rank,
    })


# ── Profile ────────────────────────────────────────────────────────────────────
@login_required
def profile_view(request, username=None):
    profile_user = get_object_or_404(User, username=username) if username else request.user
    profile, _   = UserProfile.objects.get_or_create(user=profile_user)
    answers       = UserAnswer.objects.filter(user=profile_user).order_by('-answered_at')[:20]
    correct_count = UserAnswer.objects.filter(user=profile_user, is_correct=True).count()
    total_count   = UserAnswer.objects.filter(user=profile_user).count()
    certificates  = Certificate.objects.filter(user=profile_user).order_by('-issued_at')
    referrals     = Referral.objects.filter(referrer=profile_user).order_by('-created_at')
    rank = UserProfile.objects.filter(
        total_points__gt=profile.total_points, is_blocked=False
    ).count() + 1
    return render(request, 'quiz/profile.html', {
        'profile_user':  profile_user,
        'profile':       profile,
        'answers':       answers,
        'correct_count': correct_count,
        'total_count':   total_count,
        'certificates':  certificates,
        'referrals':     referrals,
        'rank':          rank,
    })


@login_required
def edit_profile_view(request):
    profile, _  = UserProfile.objects.get_or_create(user=request.user)
    form        = UserProfileForm(instance=profile)
    user_form   = UserSettingsForm(instance=request.user)
    if request.method == 'POST':
        form      = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid() and user_form.is_valid():
            form.save(); user_form.save()
            messages.success(request, "Profil mis a jour avec succes.")
            return redirect('profile')
    return render(request, 'quiz/edit_profile.html', {'form': form, 'user_form': user_form})


# ── Parrainage ─────────────────────────────────────────────────────────────────
@login_required
def parrainage_view(request):
    profile, _  = UserProfile.objects.get_or_create(user=request.user)
    referrals   = Referral.objects.filter(referrer=request.user).order_by('-created_at')
    invite_url  = request.build_absolute_uri(f'/register/?ref={profile.referral_code}')
    return render(request, 'quiz/parrainage.html', {
        'profile':     profile,
        'referrals':   referrals,
        'invite_url':  invite_url,
    })


# ── Settings ───────────────────────────────────────────────────────────────────
@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    pwd_form   = PasswordChangeCustomForm(user=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_password':
            pwd_form = PasswordChangeCustomForm(user=request.user, data=request.POST)
            if pwd_form.is_valid():
                pwd_form.save()
                messages.success(request, "Mot de passe change. Reconnectez-vous.")
                return redirect('login')
            else:
                messages.error(request, "Erreur lors du changement de mot de passe.")
        elif action == 'delete_account':
            if request.POST.get('confirm_delete') == request.user.username:
                request.user.delete()
                messages.info(request, "Votre compte a ete supprime.")
                return redirect('home')
            else:
                messages.error(request, "Nom d'utilisateur incorrect.")
    return render(request, 'quiz/settings.html', {'pwd_form': pwd_form, 'profile': profile})


# ── Notifications ──────────────────────────────────────────────────────────────
@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'quiz/notifications.html', {'notifications': notifs})


# ── Certificats ────────────────────────────────────────────────────────────────
@login_required
def certificats_view(request):
    certificates = Certificate.objects.filter(user=request.user).order_by('-issued_at')
    return render(request, 'quiz/certificats.html', {'certificates': certificates})


# ── Leaderboard ────────────────────────────────────────────────────────────────
@login_required
def leaderboard_view(request):
    leaders    = UserProfile.objects.filter(is_blocked=False).select_related('user').order_by('-total_points')[:50]
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    my_rank    = UserProfile.objects.filter(total_points__gt=profile.total_points, is_blocked=False).count() + 1
    return render(request, 'quiz/leaderboard.html', {
        'leaders': leaders, 'my_rank': my_rank, 'profile': profile,
    })


# ── Createur ───────────────────────────────────────────────────────────────────
def createur_view(request):
    return render(request, 'quiz/createur.html')
