from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from .models import UserProfile, DailyQuestion, UserAnswer, Certificate, Notification
from .forms import (
    CustomLoginForm, CustomRegisterForm, UserProfileForm,
    UserSettingsForm, PasswordChangeCustomForm
)
import datetime


# ─────────────────────────────────────────────────────────────────────────────
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
                messages.success(request, f"Bienvenue, {user.first_name or user.username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Identifiants incorrects. Verifiez votre nom d'utilisateur et mot de passe.")
    return render(request, 'quiz/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = CustomRegisterForm()
    if request.method == 'POST':
        form = CustomRegisterForm(data=request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f"Bienvenue sur KING CH, {user.username}! Compte cree avec succes.")
            return redirect('dashboard')
    return render(request, 'quiz/register.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Vous etes deconnecte. A bientot!")
    return redirect('login')


@login_required
def dashboard_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_blocked:
        logout(request)
        messages.error(request, "Votre compte a ete bloque. Contactez l'administrateur.")
        return redirect('login')

    today = datetime.date.today()
    today_qs   = DailyQuestion.objects.filter(date=today, is_active=True)
    answered_ids = UserAnswer.objects.filter(user=user).values_list('question_id', flat=True)
    pending_qs   = today_qs.exclude(id__in=answered_ids)
    answered_today = today_qs.filter(id__in=answered_ids)

    points_today = UserAnswer.objects.filter(
        user=user, question__date=today
    ).aggregate(total=Sum('points_earned'))['total'] or 0

    certificates  = Certificate.objects.filter(user=user).order_by('-issued_at')
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]
    leaderboard   = UserProfile.objects.filter(is_blocked=False).order_by('-total_points')[:10]

    return render(request, 'quiz/dashboard.html', {
        'profile':        profile,
        'today_questions': today_qs,
        'pending_questions': pending_qs,
        'answered_today': answered_today,
        'points_today':   points_today,
        'certificates':   certificates,
        'notifications':  notifications,
        'leaderboard':    leaderboard,
        'today':          today,
    })


@login_required
def quiz_view(request, question_id):
    question = get_object_or_404(DailyQuestion, id=question_id, is_active=True)
    user     = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_blocked:
        logout(request)
        return redirect('login')

    if UserAnswer.objects.filter(user=user, question=question).exists():
        messages.warning(request, "Vous avez deja repondu a cette question.")
        return redirect('dashboard')

    if request.method == 'POST':
        selected = request.POST.get('answer')
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
                messages.success(request, f"Bonne reponse! +{pts} points!")
            else:
                correct_text = getattr(question, f'option_{question.correct_answer.lower()}')
                messages.error(request, f"Mauvaise reponse. La bonne reponse etait: ({question.correct_answer}) {correct_text}")

            return redirect('quiz_result', question_id=question.id)
        else:
            messages.error(request, "Veuillez selectionner une reponse.")

    return render(request, 'quiz/quiz.html', {'question': question})


@login_required
def quiz_result_view(request, question_id):
    question = get_object_or_404(DailyQuestion, id=question_id)
    answer   = get_object_or_404(UserAnswer, user=request.user, question=question)
    return render(request, 'quiz/quiz_result.html', {'question': question, 'answer': answer})


@login_required
def profile_view(request, username=None):
    profile_user = get_object_or_404(User, username=username) if username else request.user
    profile, _   = UserProfile.objects.get_or_create(user=profile_user)

    answers       = UserAnswer.objects.filter(user=profile_user).order_by('-answered_at')[:20]
    correct_count = UserAnswer.objects.filter(user=profile_user, is_correct=True).count()
    total_count   = UserAnswer.objects.filter(user=profile_user).count()
    certificates  = Certificate.objects.filter(user=profile_user).order_by('-issued_at')
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
        'rank':          rank,
    })


@login_required
def edit_profile_view(request):
    profile,   _ = UserProfile.objects.get_or_create(user=request.user)
    form       = UserProfileForm(instance=profile)
    user_form  = UserSettingsForm(instance=request.user)

    if request.method == 'POST':
        form      = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid() and user_form.is_valid():
            form.save(); user_form.save()
            messages.success(request, "Profil mis a jour avec succes.")
            return redirect('profile')

    return render(request, 'quiz/edit_profile.html', {'form': form, 'user_form': user_form})


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
                messages.success(request, "Mot de passe change avec succes. Reconnectez-vous.")
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


@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'quiz/notifications.html', {'notifications': notifs})


def createur_view(request):
    return render(request, 'quiz/createur.html')


@login_required
def certificats_view(request):
    certificates = Certificate.objects.filter(user=request.user).order_by('-issued_at')
    return render(request, 'quiz/certificats.html', {'certificates': certificates})


@login_required
def leaderboard_view(request):
    leaders = UserProfile.objects.filter(is_blocked=False)\
                                  .select_related('user').order_by('-total_points')[:50]
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    my_rank = UserProfile.objects.filter(
        total_points__gt=profile.total_points, is_blocked=False
    ).count() + 1
    return render(request, 'quiz/leaderboard.html', {
        'leaders': leaders, 'my_rank': my_rank, 'profile': profile,
    })
