import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id',                     models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('phone',                  models.CharField(blank=True, max_length=20, verbose_name='Telephone')),
                ('avatar',                 models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='Photo de profil')),
                ('total_points',           models.IntegerField(default=0, verbose_name='Points totaux')),
                ('is_blocked',             models.BooleanField(default=False, verbose_name='Compte bloque')),
                ('blocked_reason',         models.TextField(blank=True, verbose_name='Raison du blocage')),
                ('whatsapp',               models.CharField(blank=True, max_length=20, verbose_name='WhatsApp')),
                ('bio',                    models.TextField(blank=True, verbose_name='Bio')),
                ('created_at',             models.DateTimeField(auto_now_add=True)),
                ('referral_code',          models.CharField(blank=True, max_length=12, unique=True, verbose_name='Code de parrainage')),
                ('referral_points_earned', models.IntegerField(default=0, verbose_name='Points de parrainage gagnes')),
                ('referred_by',            models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to=settings.AUTH_USER_MODEL, verbose_name='Parraine par')),
                ('user',                   models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Profil utilisateur', 'verbose_name_plural': 'Profils utilisateurs'},
        ),

        migrations.CreateModel(
            name='DailyQuestion',
            fields=[
                ('id',             models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('question_text',  models.TextField(verbose_name='Question')),
                ('option_a',       models.CharField(max_length=300, verbose_name='Reponse A')),
                ('option_b',       models.CharField(max_length=300, verbose_name='Reponse B')),
                ('option_c',       models.CharField(max_length=300, verbose_name='Reponse C')),
                ('option_d',       models.CharField(max_length=300, verbose_name='Reponse D')),
                ('correct_answer', models.CharField(choices=[('A','A'),('B','B'),('C','C'),('D','D')], max_length=1, verbose_name='Bonne reponse')),
                ('points',         models.IntegerField(default=3, verbose_name='Points')),
                ('category',       models.CharField(choices=[('general','Culture generale'),('science','Science'),('history','Histoire'),('geography','Geographie'),('tech','Technologie'),('sport','Sport'),('art','Art & Culture')], default='general', max_length=20, verbose_name='Categorie')),
                ('date',           models.DateField(default=datetime.date.today, verbose_name='Date')),
                ('is_active',      models.BooleanField(default=True, verbose_name='Active')),
                ('created_at',     models.DateTimeField(auto_now_add=True)),
                ('created_by',     models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_questions', to=settings.AUTH_USER_MODEL, verbose_name='Creee par')),
            ],
            options={'verbose_name': 'Question du jour', 'verbose_name_plural': 'Questions du jour', 'ordering': ['-date', '-created_at']},
        ),

        migrations.CreateModel(
            name='UserAnswer',
            fields=[
                ('id',              models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('selected_answer', models.CharField(choices=[('A','A'),('B','B'),('C','C'),('D','D')], max_length=1)),
                ('is_correct',      models.BooleanField(default=False)),
                ('points_earned',   models.IntegerField(default=0)),
                ('answered_at',     models.DateTimeField(auto_now_add=True)),
                ('question',        models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_answers', to='quiz.dailyquestion')),
                ('user',            models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Reponse utilisateur', 'verbose_name_plural': 'Reponses utilisateurs', 'unique_together': {('user', 'question')}},
        ),

        migrations.CreateModel(
            name='Certificate',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title',             models.CharField(max_length=200, verbose_name='Titre du certificat')),
                ('description',       models.TextField(blank=True, verbose_name='Description / Message')),
                ('points_required',   models.IntegerField(default=0, verbose_name='Points requis')),
                ('certificate_image', models.ImageField(blank=True, null=True, upload_to='certificates/', verbose_name='Image du certificat (photo)')),
                ('issued_at',         models.DateTimeField(auto_now_add=True)),
                ('issued_by',         models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_certificates', to=settings.AUTH_USER_MODEL, verbose_name='Emis par')),
                ('user',              models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Certificat', 'verbose_name_plural': 'Certificats', 'ordering': ['-issued_at']},
        ),

        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('message',    models.TextField(verbose_name='Message')),
                ('is_read',    models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Notification', 'verbose_name_plural': 'Notifications', 'ordering': ['-created_at']},
        ),

        migrations.CreateModel(
            name='Referral',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('points_given', models.IntegerField(default=2, verbose_name='Points accordes')),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('referrer',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_referrals',    to=settings.AUTH_USER_MODEL, verbose_name='Parrain')),
                ('referred_user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='referral_record', to=settings.AUTH_USER_MODEL, verbose_name='Invite')),
            ],
            options={'verbose_name': 'Parrainage', 'verbose_name_plural': 'Parrainages', 'ordering': ['-created_at']},
        ),
    ]
