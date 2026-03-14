from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import SourceSystem


class StaffAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Email or username',
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'username',
                'placeholder': 'matthewbketchum',
            }
        ),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'placeholder': 'Enter your password',
            }
        ),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                'Staff access required for Member OS.',
                code='staff_access_required',
            )


class StyledPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Current password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label='New password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )


class CsvImportForm(forms.Form):
    source_system = forms.ChoiceField(
        label='Source system',
        choices=SourceSystem.choices,
        initial=SourceSystem.MANUAL_CSV,
    )
    file = forms.FileField(
        label='CSV file',
        help_text='Upload a UTF-8 CSV with a header row. Raw rows are preserved append-only.',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv,text/csv'}),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        filename = (uploaded_file.name or '').lower()
        if filename and not filename.endswith('.csv'):
            raise forms.ValidationError('Upload a file ending in .csv.')
        return uploaded_file
