import json
import os

from couchdbkit import ResourceConflict, ResourceNotFound
from django.contrib import messages
from django.urls import RegexURLResolver, Resolver404
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from corehq import toggles
from corehq.apps.app_manager.dbaccessors import get_all_built_app_ids_and_versions, get_app
from corehq.apps.app_manager.decorators import safe_download, safe_cached_download
from corehq.apps.app_manager.exceptions import ModuleNotFoundException, \
    AppManagerException, FormNotFoundException
from corehq.apps.app_manager.util import add_odk_profile_after_build
from corehq.apps.app_manager.views.utils import back_to_main, get_langs
from corehq.apps.app_manager.tasks import make_async_build
from corehq.apps.builds.jadjar import convert_XML_To_J2ME
from corehq.apps.hqmedia.views import DownloadMultimediaZip
from corehq.util.soft_assert import soft_assert
from corehq.util.view_utils import set_file_download
from dimagi.utils.web import json_response
from corehq.apps.accounting.utils import domain_has_privilege
from corehq import privileges


BAD_BUILD_MESSAGE = _("Sorry: this build is invalid. Try deleting it and rebuilding. "
                      "If error persists, please contact us at commcarehq-support@dimagi.com")


@safe_download
def download_odk_profile(request, domain, app_id):
    """
    See ApplicationBase.create_profile

    """
    if not request.app.copy_of:
        username = request.GET.get('username', 'unknown user')
        make_async_build.delay(request.app, username)
    else:
        request._always_allow_browser_caching = True
    build_profile = request.GET.get('profile')
    return HttpResponse(
        request.app.create_profile(is_odk=True, build_profile_id=build_profile),
        content_type="commcare/profile"
    )


@safe_download
def download_odk_media_profile(request, domain, app_id):
    if not request.app.copy_of:
        username = request.GET.get('username', 'unknown user')
        make_async_build.delay(request.app, username)
    else:
        request._always_allow_browser_caching = True
    build_profile = request.GET.get('profile')
    return HttpResponse(
        request.app.create_profile(is_odk=True, with_media=True, build_profile_id=build_profile),
        content_type="commcare/profile"
    )


@safe_cached_download
def download_suite(request, domain, app_id):
    """
    See Application.create_suite

    """
    if not request.app.copy_of:
        previous_version = request.app.get_latest_app(released_only=False)
        request.app.set_form_versions(previous_version)
    return HttpResponse(
        request.app.create_suite()
    )


@safe_cached_download
def download_media_suite(request, domain, app_id):
    """
    See Application.create_media_suite

    """
    if not request.app.copy_of:
        previous_version = request.app.get_latest_app(released_only=False)
        request.app.set_media_versions(previous_version)
    return HttpResponse(
        request.app.create_media_suite()
    )


@safe_cached_download
def download_app_strings(request, domain, app_id, lang):
    """
    See Application.create_app_strings

    """
    return HttpResponse(
        request.app.create_app_strings(lang)
    )


@safe_cached_download
def download_xform(request, domain, app_id, module_id, form_id):
    """
    See Application.fetch_xform

    """
    try:
        return HttpResponse(
            request.app.fetch_xform(module_id, form_id)
        )
    except (IndexError, ModuleNotFoundException):
        raise Http404()
    except AppManagerException:
        form_unique_id = request.app.get_module(module_id).get_form(form_id).unique_id
        response = validate_form_for_build(request, domain, app_id, form_unique_id, ajax=False)
        response.status_code = 404
        return response


@safe_cached_download
def download_jad(request, domain, app_id):
    """
    See ApplicationBase.create_jadjar_from_build_files

    """
    app = request.app
    if not app.copy_of:
        app.set_form_versions(None)
        app.set_media_versions(None)
    jad, _ = app.create_jadjar_from_build_files()
    try:
        response = HttpResponse(jad)
    except Exception:
        messages.error(request, BAD_BUILD_MESSAGE)
        return back_to_main(request, domain, app_id=app_id)
    set_file_download(response, "CommCare.jad")
    response["Content-Type"] = "text/vnd.sun.j2me.app-descriptor"
    response["Content-Length"] = len(jad)
    return response


@safe_cached_download
def download_jar(request, domain, app_id):
    """
    See ApplicationBase.create_jadjar_from_build_files

    This is the only view that will actually be called
    in the process of downloading a complete CommCare.jar
    build (i.e. over the air to a phone).

    """
    response = HttpResponse(content_type="application/java-archive")
    app = request.app
    if not app.copy_of:
        app.set_form_versions(None)
        app.set_media_versions(None)
    _, jar = app.create_jadjar_from_build_files()
    set_file_download(response, 'CommCare.jar')
    response['Content-Length'] = len(jar)
    try:
        response.write(jar)
    except Exception:
        messages.error(request, BAD_BUILD_MESSAGE)
        return back_to_main(request, domain, app_id=app_id)
    return response


def download_test_jar(request):
    with open(os.path.join(os.path.dirname(__file__), 'static', 'app_manager', 'CommCare.jar')) as f:
        jar = f.read()

    response = HttpResponse(content_type="application/java-archive")
    set_file_download(response, "CommCare.jar")
    response['Content-Length'] = len(jar)
    response.write(jar)
    return response


@safe_cached_download
def download_raw_jar(request, domain, app_id):
    """
    See ApplicationBase.fetch_jar

    """
    response = HttpResponse(
        request.app.fetch_jar()
    )
    response['Content-Type'] = "application/java-archive"
    return response


class DownloadCCZ(DownloadMultimediaZip):
    name = 'download_ccz'
    compress_zip = True

    @property
    def zip_name(self):
        return 'commcare_v{}.ccz'.format(self.app.version)

    include_index_files = True

    def check_before_zipping(self):
        if self.app.is_remote_app():
            self.include_multimedia_files = False
        super(DownloadCCZ, self).check_before_zipping()


@safe_cached_download
def download_file(request, domain, app_id, path):
    if path == "app.json":
        return JsonResponse(request.app.to_json())

    content_type_map = {
        'ccpr': 'commcare/profile',
        'jad': 'text/vnd.sun.j2me.app-descriptor',
        'jar': 'application/java-archive',
        'xml': 'application/xml',
        'txt': 'text/plain',
    }
    try:
        content_type = content_type_map[path.split('.')[-1]]
    except KeyError:
        content_type = None
    response = HttpResponse(content_type=content_type)

    build_profile = request.GET.get('profile')
    build_profile_access = domain_has_privilege(domain, privileges.BUILD_PROFILES)
    if path in ('CommCare.jad', 'CommCare.jar'):
        set_file_download(response, path)
        full_path = path
    elif build_profile and build_profile in request.app.build_profiles and build_profile_access:
        full_path = 'files/%s/%s' % (build_profile, path)
    else:
        full_path = 'files/%s' % path

    def resolve_path(path):
        return RegexURLResolver(
            r'^', 'corehq.apps.app_manager.download_urls').resolve(path)

    try:
        assert request.app.copy_of
        # lazily create language profiles to avoid slowing initial build
        try:
            payload = request.app.fetch_attachment(full_path)
        except ResourceNotFound:
            if build_profile in request.app.build_profiles and build_profile_access:
                try:
                    # look for file guaranteed to exist if profile is created
                    assert request.app.copy_of
                    request.app.fetch_attachment('files/{id}/profile.xml'.format(id=build_profile))
                except ResourceNotFound:
                    request.app.create_build_files(save=True, build_profile_id=build_profile)
                    request.app.save()
                    payload = request.app.fetch_attachment(full_path)
                else:
                    # if profile.xml is found the profile has been built and its a bad request
                    raise
            else:
                raise
        if type(payload) is unicode:
            payload = payload.encode('utf-8')
        if path in ['profile.xml', 'media_profile.xml']:
            payload = convert_XML_To_J2ME(payload, path, request.app.use_j2me_endpoint)
        response.write(payload)
        response['Content-Length'] = len(response.content)
        return response
    except (ResourceNotFound, AssertionError):
        if request.app.copy_of:
            if request.META.get('HTTP_USER_AGENT') == 'bitlybot':
                raise Http404()
            elif path == 'profile.ccpr':
                # legacy: should patch build to add odk profile
                # which wasn't made on build for a long time
                add_odk_profile_after_build(request.app)
                request.app.save()
                return download_file(request, domain, app_id, path)
            elif path in ('CommCare.jad', 'CommCare.jar'):
                if not request.app.build_spec.supports_j2me():
                    raise Http404()
                request.app.create_jadjar_from_build_files(save=True)
                try:
                    request.app.save(increment_version=False)
                except ResourceConflict:
                    # Likely that somebody tried to download the jad and jar
                    # files for the first time simultaneously.
                    pass
                return download_file(request, domain, app_id, path)
            else:
                try:
                    resolve_path(path)
                except Resolver404:
                    # ok this was just a url that doesn't exist
                    # todo: log since it likely exposes a mobile bug
                    # logging was removed because such a mobile bug existed
                    # and was spamming our emails
                    pass
                else:
                    # this resource should exist but doesn't
                    _assert = soft_assert('@'.join(['jschweers', 'dimagi.com']))
                    _assert(False, 'Expected build resource %s not found' % path)
                raise Http404()
        try:
            callback, callback_args, callback_kwargs = resolve_path(path)
        except Resolver404:
            raise Http404()

        return callback(request, domain, app_id, *callback_args, **callback_kwargs)


@safe_download
def download_profile(request, domain, app_id):
    """
    See ApplicationBase.create_profile

    """
    if not request.app.copy_of:
        username = request.GET.get('username', 'unknown user')
        make_async_build.delay(request.app, username)
    else:
        request._always_allow_browser_caching = True
    return HttpResponse(
        request.app.create_profile()
    )


@safe_download
def download_media_profile(request, domain, app_id):
    if not request.app.copy_of:
        username = request.GET.get('username', 'unknown user')
        make_async_build.delay(request.app, username)
    else:
        request._always_allow_browser_caching = True
    return HttpResponse(
        request.app.create_profile(with_media=True)
    )


@safe_cached_download
def download_practice_user_restore(request, domain, app_id):
    if not request.app.copy_of:
        make_async_build.delay(request.app)
    return HttpResponse(
        request.app.create_practice_user_restore()
    )


@safe_download
def download_index(request, domain, app_id):
    """
    A landing page, mostly for debugging, that has links the jad and jar as well as
    all the resource files that will end up zipped into the jar.

    """
    files = []
    try:
        files = source_files(request.app)
    except Exception:
        messages.error(
            request,
            _(
                "We were unable to get your files "
                "because your Application has errors. "
                "Please click <strong>Make New Version</strong> "
                "for feedback on how to fix these errors."
            ),
            extra_tags='html'
        )
    built_versions = get_all_built_app_ids_and_versions(domain, request.app.copy_of)
    return render(request, "app_manager/download_index.html", {
        'app': request.app,
        'files': [{'name': f[0], 'source': f[1]} for f in files],
        'supports_j2me': request.app.build_spec.supports_j2me(),
        'built_versions': [{
            'app_id': app_id,
            'build_id': build_id,
            'version': version,
            'comment': comment,
        } for app_id, build_id, version, comment in built_versions]
    })


def validate_form_for_build(request, domain, app_id, form_unique_id, ajax=True):
    app = get_app(domain, app_id)
    try:
        form = app.get_form(form_unique_id)
    except FormNotFoundException:
        # this can happen if you delete the form from another page
        raise Http404()
    errors = form.validate_for_build()
    lang, langs = get_langs(request, app)

    if ajax and "blank form" in [error.get('type') for error in errors] and not form.form_type == "shadow_form":
        response_html = ""
    else:
        if form.form_type == "shadow_form":
            # Don't display the blank form error if its a shadow form
            errors = [e for e in errors if e['type'] != "blank form"]
        response_html = render_to_string("app_manager/partials/build_errors.html", {
            'request': request,
            'app': app,
            'form': form,
            'build_errors': errors,
            'not_actual_build': True,
            'domain': domain,
            'langs': langs,
            'lang': lang
        })

    if ajax:
        return json_response({
            'error_html': response_html,
        })
    else:
        return HttpResponse(response_html)


def download_index_files(app, build_profile_id=None):
    if app.copy_of:
        prefix = 'files/'
        if build_profile_id is not None:
            prefix += build_profile_id + '/'
            needed_for_CCZ = lambda path: path.startswith(prefix)
        else:
            profiles = set(app.build_profiles)
            needed_for_CCZ = lambda path: (path.startswith(prefix) and
                                           path.split('/')[1] not in profiles)
        if not (prefix + 'profile.ccpr') in app.blobs:
            # profile hasnt been built yet
            app.create_build_files(save=True, build_profile_id=build_profile_id)
            app.save()
        files = [(path[len(prefix):], app.fetch_attachment(path))
                 for path in app.blobs if needed_for_CCZ(path)]
    else:
        files = app.create_all_files().items()
    return sorted(files)


def source_files(app):
    """
    Return the app's source files, including the app json.
    Return format is a list of tuples where the first item in the tuple is a
    file name and the second is the file contents.
    """
    if not app.copy_of:
        app.set_media_versions(None)
    files = download_index_files(app)
    files.append(
        ("app.json", json.dumps(
            app.to_json(), sort_keys=True, indent=4, separators=(',', ': ')
        ))
    )
    return sorted(files)
