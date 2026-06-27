from django.db import models
from django.contrib.auth.models import User
import datetime


class UserProfile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone         = models.CharField(max_length=20, blank=True, verbose_name="Telephone")
    avatar        = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Photo de profil")
    total_points  = models.IntegerField(default=0, verbose_name="Points totaux")
    is_blocked    = models.BooleanField(default=False, verbose_name="Compte bloque")
    blocked_reason= models.TextField(blank=True, verbose_name="Raison du blocage")
    whatsapp      = models.CharField(max_length=20, blank=True, verbose_name="WhatsApp")
    bio           = models.TextField(blank=True, verbose_name="Bio")
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"Profil de {self.user.username}"


class DailyQuestion(models.Model):
    CATEGORY_CHOICES = [
        ('general',  'Culture generale'),
        ('science',  'Science'),
        ('history',  'Histoire'),
        ('geography','Geographie'),
        ('tech',     'Technologie'),
        ('sport',    'Sport'),
        ('art',      'Art & Culture'),
    ]

    question_text  = models.TextField(verbose_name="Question")
    option_a       = models.CharField(max_length=300, verbose_name="Reponse A")
    option_b       = models.CharField(max_length=300, verbose_name="Reponse B")
    option_c       = models.CharField(max_length=300, verbose_name="Reponse C")
    option_d       = models.CharField(max_length=300, verbose_name="Reponse D")
    correct_answer = models.CharField(
        max_length=1,
        choices=[('A','A'),('B','B'),('C','C'),('D','D')],
        verbose_name="Bonne reponse"
    )
    points     = models.IntegerField(default=3, verbose_name="Points")
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general', verbose_name="Categorie")
    date       = models.DateField(default=datetime.date.today, verbose_name="Date")
    is_active  = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_questions', verbose_name="Creee par"
    )

    class Meta:
        verbose_name        = "Question du jour"
        verbose_name_plural = "Questions du jour"
        ordering            = ['-date', '-created_at']

    def __str__(self):
        return f"[{self.date}] {self.question_text[:60]}"

    def get_option(self, letter):
        """Return option text by letter A/B/C/D."""
        return getattr(self, f'option_{letter.lower()}', '')


class UserAnswer(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    question        = models.ForeignKey(DailyQuestion, on_delete=models.CASCADE, related_name='user_answers')
    selected_answer = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    is_correct      = models.BooleanField(default=False)
    points_earned   = models.IntegerField(default=0)
    answered_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Reponse utilisateur"
        verbose_name_plural = "Reponses utilisateurs"
        unique_together     = ['user', 'question']

    def __str__(self):
        mark = "OK" if self.is_correct else "KO"
        return f"{self.user.username} | {mark} | {self.points_earned} pts"


class Certificate(models.Model):
    """
    Certificat envoye par l'admin a un utilisateur.
    certificate_image : photo/image uploadee depuis l'admin (stockee dans media/certificates/)
    L'utilisateur peut voir et telecharger cette image depuis son profil.
    """
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    issued_by         = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='issued_certificates', verbose_name="Emis par"
    )
    title             = models.CharField(max_length=200, verbose_name="Titre du certificat")
    description       = models.TextField(blank=True, verbose_name="Description / Message")
    points_required   = models.IntegerField(default=0, verbose_name="Points requis")
    # IMAGE du certificat — stockee dans media/certificates/
    certificate_image = models.ImageField(
        upload_to='certificates/',
        blank=True, null=True,
        verbose_name="Image du certificat (photo)"
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Certificat"
        verbose_name_plural = "Certificats"
        ordering            = ['-issued_at']

    def __str__(self):
        return f"{self.title} — {self.user.username}"


class Notification(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message    = models.TextField(verbose_name="Message")
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Notification"
        verbose_name_plural = "Notifications"
        ordering            = ['-created_at']

    def __str__(self):
        return f"Notif pour {self.user.username}"
