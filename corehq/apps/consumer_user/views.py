import json

from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.signing import TimestampSigner
from django.core.signing import BadSignature
from django.core.signing import SignatureExpired
from datetime import timedelta, datetime
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from .forms.change_contact_details_form import ChangeContactDetailsForm
from .forms.consumer_user_signup_form import ConsumerUserSignUpForm
from .forms.consumer_user_authentication_form import ConsumerUserAuthenticationForm
from django.views.decorators.debug import sensitive_post_parameters
from two_factor.views import LoginView
from corehq.apps.consumer_user.models import ConsumerUser
from corehq.apps.consumer_user.models import ConsumerUserCaseRelationship
from corehq.apps.consumer_user.models import ConsumerUserInvitation
from corehq.apps.domain.decorators import two_factor_exempt
from .decorators import consumer_user_login_required
from django.utils.http import urlsafe_base64_decode
from two_factor.forms import AuthenticationTokenForm, BackupTokenForm
from django.utils.translation import ugettext as _
from ..users.models import CouchUser


class ConsumerUserLoginView(LoginView):
    form_list = (
        ('auth', ConsumerUserAuthenticationForm),
        ('token', AuthenticationTokenForm),
        ('backup', BackupTokenForm),
    )
    invitation = None
    hashed_invitation = None
    template_name = 'p_login.html'

    def get_form_kwargs(self, step=None):
        """
        Returns the keyword arguments for instantiating the form
        (or formset) on the given step.
        """
        if self.invitation:
            return {'invitation': self.invitation}
        return {}

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        url = reverse('consumer_user:consumer_user_homepage')
        return url

    def get_context_data(self, **kwargs):
        context = super(ConsumerUserLoginView, self).get_context_data(**kwargs)
        if self.hashed_invitation:
            extra_context = {}
            this_is_not_me = reverse('consumer_user:consumer_user_register',
                                     kwargs={
                                         'invitation': self.hashed_invitation
                                     })
            extra_context['this_is_not_me'] = '%s%s' % (this_is_not_me,
                                                        '?create_user=1')
            context.update(extra_context)
        return context


def get_invitation_object_or_error(invitation):
    try:
        decoded_invitation = urlsafe_base64_decode(TimestampSigner().unsign(invitation,
                                                                            max_age=timedelta(days=30)))
        invitation_obj = ConsumerUserInvitation.objects.get(id=decoded_invitation)
        if invitation_obj.accepted:
            url = reverse('consumer_user:consumer_user_login')
            return HttpResponseRedirect(url)
        elif not invitation_obj.active:
            return HttpResponse(_("Invitation is inactive"), status=400)
        else:
            return invitation_obj
    except (BadSignature, ConsumerUserInvitation.DoesNotExist):
        return HttpResponse(_("Invalid invitation"), status=400)
    except SignatureExpired:
        return HttpResponse(_("Invitation is expired"), status=400)


@two_factor_exempt
def register_view(request, invitation):
    invitation_obj = get_invitation_object_or_error(invitation)
    if isinstance(invitation_obj, HttpResponse):
        return invitation_obj
    email = invitation_obj.email
    create_user = request.GET.get('create_user', False)
    if create_user != '1' and User.objects.filter(username=email).exists():
        url = reverse('consumer_user:consumer_user_login_with_invitation',
                      kwargs={
                          'invitation': invitation
                      })
        return HttpResponseRedirect(url)
    if request.method == "POST":
        form = ConsumerUserSignUpForm(request.POST, invitation=invitation_obj)
        if form.is_valid():
            form.save()
            url = reverse('consumer_user:consumer_user_login')
            return HttpResponseRedirect(url)
    else:
        form = ConsumerUserSignUpForm()
    return render(request, 'signup.html', {'form': form})


@two_factor_exempt
@sensitive_post_parameters('auth-password')
def login_view(request, invitation=None):
    if invitation:
        return login_accept_view(request, invitation)
    if request.user and request.user.is_authenticated:
        consumer_user = ConsumerUser.objects.get_or_none(user=request.user)
        if consumer_user:
            url = reverse('consumer_user:consumer_user_homepage')
            return HttpResponseRedirect(url)
    return ConsumerUserLoginView.as_view()(request)


def login_accept_view(request, invitation):
    invitation_obj = get_invitation_object_or_error(invitation)
    if isinstance(invitation_obj, HttpResponse):
        return invitation_obj
    return ConsumerUserLoginView.as_view(invitation=invitation_obj, hashed_invitation=invitation)(request)


@consumer_user_login_required
def success_view(request):
    return render(request, 'homepage.html')


@consumer_user_login_required
def logout_view(request):
    logout(request)
    url = reverse('consumer_user:consumer_user_login')
    return HttpResponseRedirect(url)


@consumer_user_login_required
def change_password_view(request):
    consumer_user = ConsumerUser.objects.get_or_none(user=request.user)
    if consumer_user:
        if request.method == 'POST':
            form = PasswordChangeForm(user=request.user, data=request.POST)
            msg = None
            if form.is_valid():
                form.save()
                couch_user = CouchUser.from_django_user(request.user)
                if couch_user:
                    couch_user.last_password_set = datetime.utcnow()
                    couch_user.save()
                msg = _('Updated successfully')
            return render(request, 'change_password.html', {'form': form,
                                                            'msg': msg})
        else:
            form = PasswordChangeForm(user=request.user)
            return render(request, 'change_password.html', {'form': form})
    else:
        return HttpResponse(status=404)


@consumer_user_login_required
def domains_and_cases_list_view(request):
    consumer_user = ConsumerUser.objects.get_or_none(user=request.user)
    if consumer_user:
        qs = ConsumerUserCaseRelationship.objects.filter(consumer_user=consumer_user)
        domains_and_cases = [val for val in qs.values('domain', 'case_id')]
        return render(request, 'domains_and_cases.html', {'domains_and_cases': domains_and_cases})
    else:
        return HttpResponse(status=404)


@consumer_user_login_required
def change_contact_details_view(request):
    consumer_user = ConsumerUser.objects.get_or_none(user=request.user)
    if consumer_user:
        msg = None
        if request.method == 'POST':
            form = ChangeContactDetailsForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                msg = _('Updated successfully')
        else:
            form = ChangeContactDetailsForm(instance=request.user)
        return render(request, 'change_contact_details.html', {'form': form,
                                                               'msg': msg})
    else:
        return HttpResponse(status=404)
