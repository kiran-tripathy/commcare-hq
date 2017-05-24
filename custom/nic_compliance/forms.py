from django import forms
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation


class EncodedPasswordChangeFormMixin(object):
    """
    To be used by forms using passwords to enable decoding for obfuscated passwords.
    """
    def clean_new_password1(self):
        from corehq.apps.domain.forms import clean_password
        from corehq.apps.hqwebapp.utils import decode_password
        new_password = decode_password(self.cleaned_data.get('new_password1'))
        # User might not be able to submit empty password but decode_password might
        # return empty password in case the password hashing is messed up with
        if new_password == '':
            raise ValidationError(
                _("Password cannot be empty"), code='new_password1_empty',
            )

        return clean_password(new_password)

    def clean_new_password2(self):
        from corehq.apps.hqwebapp.utils import decode_password
        password2 = decode_password(self.cleaned_data.get('new_password2'))
        if password2 == '':
            raise ValidationError(
                _("Password cannot be empty"), code='new_password2_empty',
            )

        password1 = self.cleaned_data.get('new_password1')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        password_validation.validate_password(password2, self.user)
        return password2


