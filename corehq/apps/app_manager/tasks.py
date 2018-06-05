from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.translation import ugettext as _

from celery.task import task

from corehq.apps.app_manager.dbaccessors import get_app, get_latest_build_id
from corehq.apps.es import AppES
from corehq.apps.users.models import CommCareUser
from corehq.util.decorators import serial_task


@task(queue='background_queue', ignore_result=True)
def create_user_cases(domain_name):
    from corehq.apps.callcenter.utils import sync_usercase
    for user in CommCareUser.by_domain(domain_name):
        sync_usercase(user)


@serial_task('{app._id}-{app.version}', max_retries=0, timeout=60*60)
def make_async_build(app, username):
    latest_build = app.get_latest_app(released_only=False)
    if latest_build.version == app.version:
        return
    errors = app.validate_app()
    if not errors:
        copy = app.make_build(
            previous_version=latest_build,
            comment=_('Auto-generated by a phone update. Will expire after next build if not marked relased.'),
        )
        copy.is_auto_generated = True
        copy.save(increment_version=False)


@task(queue='background_queue', ignore_result=True)
def create_build_files_for_all_app_profiles(domain, build_id):
    app = get_app(domain, build_id)
    build_profiles = app.build_profiles
    save_app = False
    for profile in build_profiles:
        if not app.has_attachment('files/{id}/profile.xml'.format(id=profile)):
            app.create_build_files(save=True, build_profile_id=profile)
            save_app = True
    if save_app:
        app.save()


@task(queue='background_queue')
def prune_auto_generated_builds(domain, app_id):
    last_build = get_latest_build_id(domain, app_id)
    query = (AppES()
             .domain(domain)
             .is_build()
             .is_released(False)
             .term('is_auto_generated', True)
             .term('copy_of', app_id)
             .source(['_id']))

    for hit in query.run().hits:
        if hit['_id'] == last_build:
            continue
        app = get_app(domain, hit['_id'])
        app.delete()
