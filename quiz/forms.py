from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import UserProfile


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': "Votre nom d'utilisateur",
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        })
    )


class CustomRegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Prenom", max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Votre prenom'})
    )
    last_name = forms.CharField(
        label="Nom", max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Votre nom'})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@exemple.com'})
    )
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'})
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'})
    )

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {'username': "Nom d'utilisateur"}
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'nom_utilisateur'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est deja utilise.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self, commit=True):
        # Use set_password so the password is properly hashed
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model  = UserProfile
        fields = ['avatar', 'bio', 'phone', 'whatsapp']
        labels = {
            'avatar':   "Photo de profil",
            'bio':      "Biographie",
            'phone':    "Telephone",
            'whatsapp': "WhatsApp",
        }
        widgets = {
            'bio':      forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Parlez de vous...'}),
            'phone':    forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+509 ...'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+509 ...'}),
        }


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Prenom',
            'last_name':  'Nom',
            'email':      'Email',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-input'}),
            'email':      forms.EmailInput(attrs={'class': 'form-input'}),
        }


class PasswordChangeCustomForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Ancien mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'})
    )
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'})
    )
    new_password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'})
    )
