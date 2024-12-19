from django import forms
from .models import CustomUser

class CustomUserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirmation = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password_confirmation', 'address', 'dob', 'gender', 'first_name', 'last_name']

    def clean_password_confirmation(self):
        password = self.cleaned_data.get("password")
        password_confirmation = self.cleaned_data.get("password_confirmation")
        if password != password_confirmation:
            raise forms.ValidationError("Passwords do not match.")
        return password_confirmation

    def clean_dob(self):
        dob = self.cleaned_data.get("dob")
        if not dob:
            raise forms.ValidationError("Date of Birth is required.")
        return dob
