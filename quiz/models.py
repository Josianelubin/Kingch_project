from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Photo de profil")
    total_points = models.IntegerField(default=0, verbose_name="Points totaux")
    is_blocked = models.BooleanField(default=False, verbose_name="Compte bloqué")
    blocked_reason = models.TextField(blank=True, verbose_name="Raison du blocage")
    whatsapp = models.CharField(max_length=20, blank=True, verbose_name="WhatsApp")
    created_at = models.DateTimeField(auto_now_add=True)
    bio = models.TextField(blank=True, verbose_name="Bio")

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"Profil de {self.user.username}"

    def get_plain_password(self):
        """Store hashed, but admin can see it as-is in profile note"""
        return self.user.password


class DailyQuestion(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'Culture générale'),
        ('science', 'Science'),
        ('history', 'Histoire'),
        ('geography', 'Géographie'),
        ('tech', 'Technologie'),
        ('sport', 'Sport'),
        ('art', 'Art & Culture'),
    ]

    question_text = models.TextField(verbose_name="Question")
    option_a = models.CharField(max_length=300, verbose_name="Option A")
    option_b = models.CharField(max_length=300, verbose_name="Option B")
    option_c = models.CharField(max_length=300, verbose_name="Option C")
    option_d = models.CharField(max_length=300, verbose_name="Option D")
    correct_answer = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        verbose_name="Bonne réponse"
    )
    points = models.IntegerField(default=3, verbose_name="Points")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general', verbose_name="Catégorie")
    date = models.DateField(default=datetime.date.today, verbose_name="Date")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Créée par")

    class Meta:
        verbose_name = "Question du jour"
        verbose_name_plural = "Questions du jour"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"[{self.date}] {self.question_text[:60]}..."


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(DailyQuestion, on_delete=models.CASCADE, related_name='user_answers')
    selected_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Réponse utilisateur"
        verbose_name_plural = "Réponses utilisateurs"
        unique_together = ['user', 'question']

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{self.user.username} - {status} - {self.points_earned} pts"


class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    title = models.CharField(max_length=200, verbose_name="Titre du certificat")
    description = models.TextField(blank=True, verbose_name="Description")
    points_required = models.IntegerField(verbose_name="Points requis")
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='issued_certificates', verbose_name="Émis par"
    )
    certificate_file = models.FileField(
        upload_to='certificates/', blank=True, null=True,
        verbose_name="Fichier certificat"
    )

    class Meta:
        verbose_name = "Certificat"
        verbose_name_plural = "Certificats"

    def __str__(self):
        return f"Certificat de {self.user.username} - {self.title}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField(verbose_name="Message")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif pour {self.user.username}"
