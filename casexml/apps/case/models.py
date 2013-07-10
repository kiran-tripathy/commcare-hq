from __future__ import absolute_import
from StringIO import StringIO
import re
from datetime import datetime
import logging
from copy import copy
import itertools

from django.core.cache import cache
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from couchdbkit.ext.django.schema import *
from couchdbkit.exceptions import ResourceNotFound, ResourceConflict
from PIL import Image
from dimagi.utils.django.cached_object import CachedObject, OBJECT_ORIGINAL, OBJECT_SIZE_MAP, CachedImage, IMAGE_SIZE_ORDERING
from casexml.apps.phone.xml import get_case_element
from casexml.apps.case.signals import case_post_save
from casexml.apps.case.util import get_close_case_xml, get_close_referral_xml,\
    couchable_property, get_case_xform_ids
from casexml.apps.case import const
from dimagi.utils.modules import to_function
from dimagi.utils import parsing
from dimagi.utils.decorators.memoized import memoized
from dimagi.utils.indicators import ComputedDocumentMixin
from receiver.util import spoof_submission
from couchforms.models import XFormInstance
from casexml.apps.case.sharedmodels import IndexHoldingMixIn, CommCareCaseIndex, CommCareCaseAttachment
from dimagi.utils.couch.database import get_db, SafeSaveDocument
from dimagi.utils.couch import LooselyEqualDocumentSchema


"""
Couch models for commcare cases.  

For details on casexml check out:
http://bitbucket.org/javarosa/javarosa/wiki/casexml
"""

if getattr(settings, 'CASE_WRAPPER', None):
    CASE_WRAPPER = to_function(getattr(settings, 'CASE_WRAPPER'))
else:
    CASE_WRAPPER = None

class CaseBase(SafeSaveDocument):
    """
    Base class for cases and referrals.
    """
    opened_on = DateTimeProperty()
    modified_on = DateTimeProperty()
    type = StringProperty()
    closed = BooleanProperty(default=False)
    closed_on = DateTimeProperty()
    
    def to_full_dict(self):
        """
        Include calculated properties that need to be available to the case
        details display by overriding this method.

        """
        return self.to_json()


class CommCareCaseAction(LooselyEqualDocumentSchema):
    """
    An atomic action on a case. Either a create, update, or close block in
    the xml.
    """
    action_type = StringProperty(choices=list(const.CASE_ACTIONS))
    user_id = StringProperty()
    date = DateTimeProperty()
    server_date = DateTimeProperty()
    xform_id = StringProperty()
    xform_xmlns = StringProperty()
    xform_name = StringProperty()
    sync_log_id = StringProperty()

    updated_known_properties = DictProperty()
    updated_unknown_properties = DictProperty()
    indices = SchemaListProperty(CommCareCaseIndex)
    attachments = SchemaDictProperty(CommCareCaseAttachment)

    @classmethod
    def from_parsed_action(cls, action_type, date, user_id, xformdoc, action):
        if not action_type in const.CASE_ACTIONS:
            raise ValueError("%s not a valid case action!")
        
        ret = CommCareCaseAction(action_type=action_type, date=date, user_id=user_id)
        
        def _couchify(d):
            return dict((k, couchable_property(v)) for k, v in d.items())

        ret.server_date = xformdoc.received_on
        ret.xform_id = xformdoc.get_id
        ret.xform_xmlns = xformdoc.xmlns
        ret.xform_name = xformdoc.name
        ret.updated_known_properties = _couchify(action.get_known_properties())

        ret.updated_unknown_properties = _couchify(action.dynamic_properties)
        ret.indices = [CommCareCaseIndex.from_case_index_update(i) for i in action.indices]
        ret.attachments = dict((attach_id, CommCareCaseAttachment.from_case_index_update(attach))
                               for attach_id, attach in action.attachments.items())
        if hasattr(xformdoc, "last_sync_token"):
            ret.sync_log_id = xformdoc.last_sync_token
        return ret

    @property
    def xform(self):
        return XFormInstance.get(self.xform_id) if self.xform_id else None
        
    def get_user_id(self):
        key = 'xform-%s-user_id' % self.xform_id
        id = cache.get(key)
        if not id:
            xform = self.xform
            try:
                id = xform.metadata.userID
            except AttributeError:
                id = None
            cache.set(key, id, 12*60*60)
        return id

    def __repr__(self):
        return "{xform}: {type} - {date} ({server_date})".format(
            xform=self.xform_id, type=self.action_type,
            date=self.date, server_date=self.server_date
        )

class Referral(CaseBase):
    """
    A referral, taken from casexml.  
    """
    
    # Referrals have top-level couch guids, but this id is important
    # to the phone, so we keep it here.  This is _not_ globally unique
    # but case_id/referral_id/type should be.  
    # (in our world: case_id/referral_id/type)
    referral_id = StringProperty()
    followup_on = DateTimeProperty()
    outcome = StringProperty()
    
    def __unicode__(self):
        return ("%s:%s" % (self.type, self.referral_id))
        
    def apply_updates(self, date, referral_block):
        if not const.REFERRAL_ACTION_UPDATE in referral_block:
            logging.warn("No update action found in referral block, nothing to be applied")
            return
        
        update_block = referral_block[const.REFERRAL_ACTION_UPDATE] 
        if not self.type == update_block[const.REFERRAL_TAG_TYPE]:
            raise logging.warn("Tried to update from a block with a mismatched type!")
            return
        
        if date > self.modified_on:
            self.modified_on = date
        
        if const.REFERRAL_TAG_FOLLOWUP_DATE in referral_block:
            self.followup_on = parsing.string_to_datetime(referral_block[const.REFERRAL_TAG_FOLLOWUP_DATE])
        
        if const.REFERRAL_TAG_DATE_CLOSED in update_block:
            self.closed = True
            self.closed_on = parsing.string_to_datetime(update_block[const.REFERRAL_TAG_DATE_CLOSED])
            
            
    @classmethod
    def from_block(cls, date, block):
        """
        Create referrals from a block of processed data (a dictionary)
        """
        if not const.REFERRAL_ACTION_OPEN in block:
            raise ValueError("No open tag found in referral block!")
        id = block[const.REFERRAL_TAG_ID]
        follow_date = parsing.string_to_datetime(block[const.REFERRAL_TAG_FOLLOWUP_DATE])
        open_block = block[const.REFERRAL_ACTION_OPEN]
        types = open_block[const.REFERRAL_TAG_TYPES].split(" ")
        
        ref_list = []
        for type in types:
            ref = Referral(referral_id=id, followup_on=follow_date, 
                            type=type, opened_on=date, modified_on=date, 
                            closed=False)
            ref_list.append(ref)
        
        # there could be a single update block that closes a referral
        # that we just opened.  not sure why this would happen, but 
        # we'll support it.
        if const.REFERRAL_ACTION_UPDATE in block:
            update_block = block[const.REFERRAL_ACTION_UPDATE]
            for ref in ref_list:
                if ref.type == update_block[const.REFERRAL_TAG_TYPE]:
                    ref.apply_updates(date, block)
        
        return ref_list

class CommCareCase(CaseBase, IndexHoldingMixIn, ComputedDocumentMixin):
    """
    A case, taken from casexml.  This represents the latest
    representation of the case - the result of playing all
    the actions in sequence.
    """
    domain = StringProperty()
    export_tag = StringListProperty()
    xform_ids = StringListProperty()

    external_id = StringProperty()
    user_id = StringProperty()
    owner_id = StringProperty()
    opened_by = StringProperty()
    closed_by = StringProperty()

    referrals = SchemaListProperty(Referral)
    actions = SchemaListProperty(CommCareCaseAction)
    name = StringProperty()
    version = StringProperty()
    indices = SchemaListProperty(CommCareCaseIndex)
    case_attachments = SchemaDictProperty(CommCareCaseAttachment)
    
    # TODO: move to commtrack.models.SupplyPointCases (and full regression test)
    location_ = StringListProperty()

    server_modified_on = DateTimeProperty()

    def __repr__(self):
        return u"Case: {id} ({type}: {name})".format(
            id=self._id,
            type=self.type,
            name=self.name,
        ).encode('utf-8')

    def __unicode__(self):
        return "CommCareCase: %s (%s)" % (self.case_id, self.get_id)

    def __get_case_id(self):
        return self._id

    def __set_case_id(self, id):
        self._id = id

    case_id = property(__get_case_id, __set_case_id)

    @property
    def server_opened_on(self):
        try:
            open_action = self.actions[0]
            #assert open_action.action_type == const.CASE_ACTION_CREATE
            return open_action.server_date
        except Exception:
            pass


    @property
    def reverse_indices(self):
        def wrap_row(row):
            index = CommCareCaseIndex.wrap(row['value'])
            index.is_reverse = True
            return index
        return get_db().view("case/related",
            key=[self.domain, self.get_id, "reverse_index"],
            reduce=False,
            wrapper=wrap_row
        ).all()
        
    @property
    @memoized
    def all_indices(self):
        return list(itertools.chain(self.indices, self.reverse_indices))
        
    def get_json(self):
        
        return {
            # referrals and actions excluded here
            "domain": self.domain,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "closed": self.closed,
            "date_closed": self.closed_on,
            "xform_ids": self.xform_ids,
            # renamed
            "date_modified": self.modified_on,
            "version": self.version,
            # renamed
            "server_date_modified": self.server_modified_on,
            # renamed
            "server_date_opened": self.server_opened_on,
            "properties": dict(self.dynamic_case_properties() + {
                "external_id": self.external_id,
                "owner_id": self.owner_id,
                # renamed
                "case_name": self.name,
                # renamed
                "case_type": self.type,
                # renamed
                "date_opened": self.opened_on,
                # all custom properties go here
            }.items()),
            #reorganized
            "indices": self.get_index_map(),
            "reverse_indices": self.get_index_map(True),
        }

    @memoized
    def get_index_map(self, reversed=False):
        return dict([
            (index.identifier, {
                "case_type": index.referenced_type,
                "case_id": index.referenced_id
            }) for index in (self.indices if not reversed else self.reverse_indices)
        ])

    @classmethod
    def get(cls, id, strip_history=False, **kwargs):
        if strip_history:
            return cls.get_lite(id)
        return super(CommCareCase, cls).get(id, **kwargs)

    @classmethod
    def get_lite(cls, id):
        return cls.wrap(cls.get_db().view("case/get_lite", key=id,
                                          include_docs=False).one()['value'])

    @classmethod
    def get_wrap_class(cls, data):
        if CASE_WRAPPER:
            return CASE_WRAPPER(data) or cls
        return cls

    @classmethod
    def bulk_get_lite(cls, ids):
        for res in cls.get_db().view("case/get_lite", keys=ids,
                                 include_docs=False):
            # cls.wrap is called in a lot of places; do they all need to be updated?
            yield cls.get_wrap_class(res['value']).wrap(res['value'])

    def get_preloader_dict(self):
        """
        Gets the case as a dictionary for use in touchforms preloader framework
        """
        ret = copy(self._doc)
        ret["case-id"] = self.get_id
        return ret

    def get_server_modified_date(self):
        # gets (or adds) the server modified timestamp
        if not self.server_modified_on:
            self.save()
        return self.server_modified_on
        
    def get_case_property(self, property):
        try:
            return getattr(self, property)
        except Exception:
            return None

    def set_case_property(self, property, value):
        setattr(self, property, value)

    def case_properties(self):
        return self.to_json()

    def get_actions_for_form(self, form_id):
        return [a for a in self.actions if a.xform_id == form_id]
        
    def get_version_token(self):
        """
        A unique token for this version. 
        """
        # in theory since case ids are unique and modification dates get updated
        # upon any change, this is all we need
        return "%s::%s" % (self.case_id, self.modified_on)
    
    def get_forms(self):
        """
        Gets the form docs associated with a case. If it can't find a form
        it won't be included.
        """
        def _get(id):
            try:
                return XFormInstance.get(id)
            except ResourceNotFound:
                return None
        
        forms = [_get(id) for id in self.xform_ids]
        return [form for form in forms if form] 

    def get_attachment(self, attachment_key):
        return self.fetch_attachment(attachment_key)

    def get_attachment_server_url(self, attachment_key):
        """
        A server specific URL for remote clients to access case attachment resources async.
        """
        if attachment_key in self.case_attachments:
            return reverse("api_case_attachment", kwargs={
                "domain": self.domain,
                "case_id": self._id,
                "attachment_id": attachment_key}
            )
        else:
            return None

    @classmethod
    def fetch_case_image(cls, case_id, attachment_key, filesize_limit=0, width_limit=0, height_limit=0, fixed_size=None):
        """
        Return (metadata, stream) information of best matching image attachment.
        """
        do_constrain = False

        if fixed_size is not None:
            size_key = fixed_size
        else:
            size_key = OBJECT_ORIGINAL

        constraint_dict = {}
        if filesize_limit or width_limit or height_limit:
            do_constrain=True
            if filesize_limit:
                constraint_dict['content_length'] = filesize_limit

            if height_limit:
                constraint_dict['height'] = filesize_limit

            if width_limit:
                constraint_dict['width'] = width_limit
            #do_constrain = False

        #if size key is None, then one of the limit criteria are set
        attachment_cache_key = "%(case_id)s_%(attachment)s" % {
            "case_id": case_id,
            "attachment": attachment_key
        }

        cached_image = CachedImage(attachment_cache_key)
        if not cached_image.is_cached():
            resp = cls.get_db().fetch_attachment(case_id, attachment_key, stream=True)
            stream = StringIO(resp.read())
            headers = resp.resp.headers
            cached_image.cache_image(stream, headers)

        #now that we got it cached, let's check for size constraints
        meta, stream = cached_image.get_size(size_key)

        if do_constrain:
            #check this size first
            #see if the current size matches the criteria

            def meets_constraint(constraints, meta):
                for c, limit in constraints.items():
                    if meta[c] > limit:
                        return False
                return True

            if meets_constraint(constraint_dict, meta):
                #yay, do nothing
                pass
            else:
                #this meta is no good, find another one
                lesser_keys = IMAGE_SIZE_ORDERING[0:IMAGE_SIZE_ORDERING.index(size_key)]
                lesser_keys.reverse()
                is_met = False
                for lesser_size in lesser_keys:
                    less_meta, less_stream = cached_image.get_size(lesser_size)
                    if meets_constraint(constraint_dict, less_meta):
                        meta = less_meta
                        stream = less_stream
                        is_met = True
                        break
                if not is_met:
                    meta = None
                    stream = None

        return meta, stream


    @classmethod
    def fetch_case_attachment(cls, case_id, attachment_key, filesize_limit=0, fixed_size=None, **kwargs):
        """
        Return (metadata, stream) information of best matching image attachment.
        TODO: This should be the primary case_attachment retrieval method, the image one is a silly separation of similar functionality
        Additional functionality to be abstracted by content_type of underlying attachment
        """
        size_key = OBJECT_ORIGINAL
        if fixed_size is not None and fixed_size in OBJECT_SIZE_MAP:
            size_key = fixed_size

        #if size key is None, then one of the limit criteria are set
        attachment_cache_key = "%(case_id)s_%(attachment)s" % {
            "case_id": case_id,
            "attachment": attachment_key
        }

        cobject = CachedObject(attachment_cache_key)
        if not cobject.is_cached():
            resp = cls.get_db().fetch_attachment(case_id, attachment_key, stream=True)
            stream = StringIO(resp.read())
            headers = resp.resp.headers
            cobject.cache_put(stream, headers)
        meta, stream = cobject.get()

        return meta, stream

    # this is only used by CommTrack SupplyPointCase cases and should go in
    # that class
    def bind_to_location(self, loc):
        self.location_ = loc.path

    @classmethod
    def from_case_update(cls, case_update, xformdoc):
        """
        Create a case object from a case update object.
        """
        case = cls()
        case._id = case_update.id
        case.modified_on = parsing.string_to_datetime(case_update.modified_on_str) \
                            if case_update.modified_on_str else datetime.utcnow()
        
        # apply initial updates, referrals and such, if present
        case.update_from_case_update(case_update, xformdoc)
        return case
    
    def apply_create_block(self, create_action, xformdoc, modified_on, user_id):
        # create case from required fields in the case/create block
        # create block
        def _safe_replace_and_force_to_string(me, attr, val):
            if getattr(me, attr, None):
                # attr exists and wasn't empty or false, for now don't do anything, 
                # though in the future we want to do a date-based modification comparison
                return
            if val:
                setattr(me, attr, unicode(val))

        _safe_replace_and_force_to_string(self, "type", create_action.type)
        _safe_replace_and_force_to_string(self, "name", create_action.name)
        _safe_replace_and_force_to_string(self, "external_id", create_action.external_id)
        _safe_replace_and_force_to_string(self, "user_id", create_action.user_id)
        _safe_replace_and_force_to_string(self, "owner_id", create_action.owner_id)
        create_action = CommCareCaseAction.from_parsed_action(const.CASE_ACTION_CREATE,
                                                              modified_on,
                                                              user_id,
                                                              xformdoc,
                                                              create_action)
        self.actions.append(create_action)
    
    def update_from_case_update(self, case_update, xformdoc):
        mod_date = parsing.string_to_datetime(case_update.modified_on_str) \
                    if   case_update.modified_on_str else datetime.utcnow()
        
        if self.modified_on is None or mod_date > self.modified_on:
            self.modified_on = mod_date
    
        if case_update.creates_case():
            self.apply_create_block(case_update.get_create_action(), xformdoc, mod_date, case_update.user_id)
            # case_update.get_create_action() seems to sometimes return an action with all properties set to none,
            # so set opened_by and opened_on here
            if not self.opened_on:
                self.opened_on = mod_date
            if not self.opened_by:
                self.opened_by = case_update.user_id


        if case_update.updates_case():
            update_action = CommCareCaseAction.from_parsed_action(const.CASE_ACTION_UPDATE, 
                                                                  mod_date,
                                                                  case_update.user_id,
                                                                  xformdoc,
                                                                  case_update.get_update_action())
            self._apply_action(update_action)
            self.actions.append(update_action)
        
        if case_update.closes_case():
            close_action = CommCareCaseAction.from_parsed_action(const.CASE_ACTION_CLOSE, 
                                                                 mod_date,
                                                                 case_update.user_id,
                                                                 xformdoc,
                                                                 case_update.get_close_action())
            self.closed_by = case_update.user_id
            self._apply_action(close_action)
            self.actions.append(close_action)

        if case_update.has_referrals():
            if const.REFERRAL_ACTION_OPEN in case_update.referral_block:
                referrals = Referral.from_block(mod_date, case_update.referral_block)
                # for some reason extend doesn't work.  disconcerting
                # self.referrals.extend(referrals)
                for referral in referrals:
                    self.referrals.append(referral)
            elif const.REFERRAL_ACTION_UPDATE in case_update.referral_block:
                found = False
                update_block = case_update.referral_block[const.REFERRAL_ACTION_UPDATE]
                for ref in self.referrals:
                    if ref.type == update_block[const.REFERRAL_TAG_TYPE]:
                        ref.apply_updates(mod_date, case_update.referral_block)
                        found = True
                if not found:
                    logging.error(("Tried to update referral type %s for referral %s in case %s "
                                   "but it didn't exist! Nothing will be done about this.") % \
                                   (update_block[const.REFERRAL_TAG_TYPE], 
                                    case_update.referral_block[const.REFERRAL_TAG_ID],
                                    self.case_id))
        
        if case_update.has_indices():
            index_action = CommCareCaseAction.from_parsed_action(const.CASE_ACTION_INDEX, 
                                                                 mod_date,
                                                                 case_update.user_id,
                                                                 xformdoc,
                                                                 case_update.get_index_action())
            self.actions.append(index_action)
            self._apply_action(index_action)

        if case_update.has_attachments():
            attachment_action = CommCareCaseAction.from_parsed_action(const.CASE_ACTION_ATTACHMENT,
                                                                      mod_date,
                                                                      case_update.user_id,
                                                                      xformdoc,
                                                                      case_update.get_attachment_action())
            self.actions.append(attachment_action)
            self._apply_action(attachment_action)

        # finally override any explicit properties from the update
        if case_update.user_id:     self.user_id = case_update.user_id
        if case_update.version:     self.version = case_update.version

    def _apply_action(self, action):
        if action.action_type == const.CASE_ACTION_UPDATE:
            self.apply_updates(action)
        elif action.action_type == const.CASE_ACTION_INDEX:
            self.update_indices(action.indices)
        elif action.action_type == const.CASE_ACTION_CLOSE:
            self.apply_close(action)
        elif action.action_type == const.CASE_ACTION_ATTACHMENT:
            self.apply_attachments(action)
        else:
            raise ValueError("Can't apply action of type %s" % action.action_type)

        
    def apply_updates(self, update_action):
        """
        Applies updates to a case
        """
        for k, v in update_action.updated_known_properties.items():
            setattr(self, k, v)

        for item in update_action.updated_unknown_properties:
            if item not in const.CASE_TAGS:
                self[item] = couchable_property(update_action.updated_unknown_properties[item])
            
    def apply_attachments(self, attachment_action):
        #the actions and _attachment must be added before the first saves canhappen
        #todo attach cached attachment info

        stream_dict = {}
        #cache all attachment streams from xform
        for k, v in attachment_action.attachments.items():
            if v.is_present:
                #fetch attachment, update metadata, get the stream
                attach_data = XFormInstance.get_db().fetch_attachment(attachment_action.xform_id, v.identifier)
                stream_dict[k] = attach_data
                v.attachment_size = len(attach_data)

                if v.is_image:
                    img = Image.open(StringIO(attach_data))
                    img_size = img.size
                    props = dict(width=img_size[0], height=img_size[1])
                    v.attachment_properties = props

        self.force_save()
        update_attachments = {}
        for k, v in self.case_attachments.items():
            if v.is_present:
                update_attachments[k] = v

        for k, v in attachment_action.attachments.items():
            #grab xform_attachments
            #copy over attachments from form onto case
            update_attachments[k] = v
            if v.is_present:
                #fetch attachment from xform
                attachment_key = v.attachment_key
                attach = stream_dict[attachment_key]
                self.put_attachment(attach, name=attachment_key, content_type=v.server_mime)
            else:
                self.delete_attachment(k)
                del(update_attachments[k])

        self.case_attachments = update_attachments


    def apply_close(self, close_action):
        self.closed = True
        self.closed_on = close_action.date

    def force_close(self, submit_url):
        if not self.closed:
            submission = get_close_case_xml(time=datetime.utcnow(), case_id=self._id)
            spoof_submission(submit_url, submission, name="close.xml")

    def reconcile_actions(self, rebuild=False):
        """
        Runs through the action list and tries to reconcile things that seem
        off (for example, out-of-order submissions, duplicate actions, etc.).

        This method fails hard if anything goes wrong so it's up to the caller
        to deal with that. It will raise assertion errors if this happens.
        """
        def _check_preconditions():
            for a in self.actions:
                assert a.server_date is not None and a.xform_id is not None

        def _type_sort(action_type):
            """
            Consistent ordering for action types
            """
            return const.CASE_ACTIONS.index(action_type)

        _check_preconditions()

        # this would normally work except we only recently started using the
        # form timestamp as the modificaiton date so we have to do something
        # fancier to deal with old data
        deduplicated_actions = list(set(self.actions))
        def further_deduplicate(action_list):
            def actions_match(a1, a2):
                # if everything but the server_date match, the actions match.
                # this will allow for multiple case blocks to be submitted
                # against the same case in the same form so long as they
                # are different
                a1doc = copy(a1._doc)
                a2doc = copy(a2._doc)
                a2doc['server_date'] = a1doc['server_date']
                a2doc['date'] = a1doc['date']
                return a1doc == a2doc

            ret = []
            for a in action_list:
                found_actions = [other for other in ret if actions_match(a, other)]
                if found_actions:
                    assert len(found_actions) == 1
                    match = found_actions[0]
                    # when they disagree, choose the _earlier_ one as this is
                    # the one that is likely timestamped with the form's date
                    # (and therefore being processed later in absolute time)
                    ret[ret.index(match)] = a if a.server_date < match.server_date else match
                else:
                    ret.append(a)
            return ret

        deduplicated_actions = further_deduplicate(deduplicated_actions)
        sorted_actions = sorted(
            deduplicated_actions,
            key=lambda a: (a.server_date, a.xform_id, _type_sort(a.action_type))
        )
        if sorted_actions:
            assert sorted_actions[0].action_type == const.CASE_ACTION_CREATE
        self.actions = sorted_actions
        if rebuild:
            self.rebuild()

    def rebuild(self):
        """
        Rebuilds the case state from its actions
        """
        assert self.actions[0].action_type == const.CASE_ACTION_CREATE, (
            'first case action should be a create but was %s' % self.actions[0].action_type)
        for i in range(1, len(self.actions)):
            self._apply_action(self.actions[i])
        self.xform_ids = list(set([a.xform_id for a in self.actions]))

    def force_close_referral(self, submit_url, referral):
        if not referral.closed:
            submission = get_close_referral_xml(time=datetime.utcnow(), case_id=self._id, referral_id=referral.referral_id, referral_type=referral.type)
            spoof_submission(submit_url, submission, name="close_referral.xml")

    def dynamic_case_properties(self):
        """(key, value) tuples sorted by key"""
        return sorted([(key, value) for key, value in self.dynamic_properties().items() if re.search(r'^[a-zA-Z]', key)])

    def save(self, **params):
        self.server_modified_on = datetime.utcnow()
        super(CommCareCase, self).save(**params)
        case_post_save.send(CommCareCase, case=self)

    def force_save(self, **params):
        try:
            self.save()
        except ResourceConflict:
            conflict = CommCareCase.get(self._id)
            # if there's a conflict, make sure we know about every
            # form in the conflicting doc
            missing_forms = set(conflict.xform_ids) - set(self.xform_ids)
            if missing_forms:
                logging.exception('doc update conflict saving case {id}. missing forms: {forms}'.format(
                    id=self._id,
                    forms=",".join(missing_forms)
                ))
                raise
            # couchdbkit doesn't like to let you set _rev very easily
            self._doc["_rev"] = conflict._rev
            self.force_save()

    def to_xml(self, version):
        from xml.etree import ElementTree
        if self.closed:
            elem = get_case_element(self, ('close'), version)
        else:
            elem = get_case_element(self, ('create', 'update'), version)
        return ElementTree.tostring(elem)
    
    @classmethod
    def get_by_xform_id(cls, xform_id):
        return cls.view("case/by_xform_id", reduce=False, include_docs=True, 
                        key=xform_id)

    def get_xform_ids_from_couch(self):
        """
        Like xform_ids, but will grab the raw output from couch (including
        potential duplicates or other forms, so that they can be reprocessed
        if desired).
        """
        return get_case_xform_ids(self._id)

    @classmethod
    def get_display_config(cls):
        return [
            {
                "layout": [
                    [
                        {
                            "expr": "name",
                            "name": _("Name"),
                        },
                        {
                            "expr": "opened_on",
                            "name": _("Opened On"),
                            "parse_date": True,
                        },
                        {
                            "expr": "modified_on",
                            "name": _("Modified On"),
                            "parse_date": True,
                        },
                        {
                            "expr": "closed_on",
                            "name": _("Closed On"),
                            "parse_date": True,
                        },
                    ],
                    [
                        {
                            "expr": "type",
                            "name": _("Case Type"),
                            "format": '<code>{0}</code>',
                        },
                        {
                            "expr": "user_id",
                            "name": _("User ID"),
                            "format": '<span data-field="user_id">{0}</span>',
                        },
                        {
                            "expr": "owner_id",
                            "name": _("Owner ID"),
                            "format": '<span data-field="owner_id">{0}</span>',
                        },
                        {
                            "expr": "_id",
                            "name": _("Case ID"),
                        },
                    ],
                ],
            }
        ]

import casexml.apps.case.signals
