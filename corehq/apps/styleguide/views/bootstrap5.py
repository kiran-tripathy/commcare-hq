from django.shortcuts import render

from corehq.apps.styleguide.context import get_navigation_context


def styleguide_home(request):
    return render(request, 'styleguide/bootstrap5/home.html', get_navigation_context("styleguide_home_b5"))
