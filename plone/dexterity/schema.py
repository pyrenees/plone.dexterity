# -*- coding: utf-8 -*-
from plone.behavior.interfaces import IBehavior
from plone.behavior.registration import BehaviorRegistration
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.interfaces import ISchemaInvalidatedEvent
from plone.synchronize import synchronized
from threading import RLock
from zope.component import adapter
from zope.component import getAllUtilitiesRegisteredFor
from zope.component import getUtility
from zope.component import queryUtility
from zope.dottedname.resolve import resolve
from zope.interface import implementer
import functools
import logging
import types

log = logging.getLogger(__name__)

transient = types.ModuleType("transient")

_MARKER = dict()


def invalidate_cache(fti):
    fti._p_activate()
    fti.__dict__.pop('_v_schema_get', None)
    fti.__dict__.pop('_v_schema_behavior_registrations', None)
    fti.__dict__.pop('_v_schema_subtypes', None)
    fti.__dict__.pop('_v_schema_schema_interfaces', None)
    fti.__dict__.pop('_v_schema_modified', None)
    fti.__dict__.pop('_v_schema_behavior_schema_interfaces', None)


def volatile(func):
    @functools.wraps(func)
    def decorator(self, portal_type):
        """lookup fti from portal_type and cache
        """
        if IDexterityFTI.providedBy(portal_type):
            fti = portal_type
        else:
            fti = queryUtility(IDexterityFTI, name=portal_type)
        if fti is not None and self.cache_enabled:
            key = '_v_schema_%s' % func.__name__
            cache = getattr(fti, key, _MARKER)
            if cache is not _MARKER:
                mtime, value = cache
                if fti._p_mtime == mtime:
                    return value

        value = func(self, fti)

        if fti is not None and self.cache_enabled:
            setattr(fti, key, (fti._p_mtime, value))

        return value
    return decorator


class SchemaCache(object):
    """Simple schema cache for FTI based schema information.

    This cache will store a Python object reference to the schema, as returned
    by fti.lookupSchema(), for any number of portal types. The value will
    be cached until the server is restarted or the cache is invalidated or
    cleared.

    You should only use this if you require bare-metal speed. For almost all
    operations, it's safer and easier to do:

        >>> fti = getUtility(IDexterityFTI, name=portal_type)
        >>> schema = fti.lookupSchema()

    The lookupSchema() call is probably as fast as this cache. However, if
    you need to avoid the utility lookup, you can use the cache like so:

        >>> from plone.dexterity.schema import SCHEMA_CACHE
        >>> my_schema = SCHEMA_CACHE.get(portal_type)

    The cache uses the FTI's modification time as its invariant.
    """

    lock = RLock()

    def __init__(self, cache_enabled=True):
        self.cache_enabled = cache_enabled
        self.invalidations = 0

    @synchronized(lock)
    @volatile
    def get(self, fti):
        """main schema

        magic! fti is passed in as a string (identifier of fti), then volatile
        decorator looks it up and passes the FTI instance in.
        """
        if fti is not None:
            try:
                return fti.lookupSchema()
            except (AttributeError, ValueError):
                pass

    @synchronized(lock)
    @volatile
    def behavior_registrations(self, fti):
        """all behavior behavior registrations of a given fti passed in as
        portal_type string (magic see get)

        returns a tuple with instances of
        ``plone.behavior.registration.BehaviorRegistration`` instances
        for the given fti.
        """
        if fti is None:
            return tuple()
        registrations = []
        for behavior_name in fti.behaviors:
            registration = queryUtility(IBehavior, name=behavior_name)
            if registration is None:
                # BBB - this case should be deprecated in v 3.0
                log.warning(
                    'No behavior registration found for behavior named: "{0}"'
                    ' - trying fallback lookup..."'.format(
                        behavior_name
                    )
                )
                try:
                    schema_interface = resolve(behavior_name)
                except (ValueError, ImportError):
                    log.error(
                        "Error resolving behavior {0}".format(
                            behavior_name
                        )
                    )
                    continue
                registration = BehaviorRegistration(
                    title=behavior_name,
                    description="bbb fallback lookup",
                    interface=schema_interface,
                    marker=None,
                    factory=None
                )
            registrations.append(registration)
        return tuple(registrations)

    @synchronized(lock)
    @volatile
    def subtypes(self, fti):
        """all registered marker interfaces of ftis behaviors

        XXX: this one does not make much sense and should be deprecated
        """
        if fti is None:
            return ()
        subtypes = []
        for behavior_registration in self.behavior_registrations(fti):
            if behavior_registration is not None \
               and behavior_registration.marker is not None:
                subtypes.append(behavior_registration.marker)
        return tuple(subtypes)

    @synchronized(lock)
    @volatile
    def behavior_schema_interfaces(self, fti):
        """behavior schema interfaces registered for the fti

        all schemas from behaviors
        """
        if fti is None:
            return ()
        schemas = []
        for behavior_registration in self.behavior_registrations(fti):
            if behavior_registration is not None \
               and behavior_registration.interface:
                schemas.append(behavior_registration.interface)
        return tuple(schemas)

    @synchronized(lock)
    @volatile
    def schema_interfaces(self, fti):
        """all schema interfaces registered for the fti

        main_schema plus schemas from behaviors
        """
        if fti is None:
            return ()
        schemas = []
        try:
            main_schema = self.get(fti)  # main schema
            schemas.append(main_schema)
        except (ValueError, AttributeError):
            pass
        for schema in self.behavior_schema_interfaces(fti):
            schemas.append(schema)
        return tuple(schemas)

    @synchronized(lock)
    def clear(self):
        for fti in getAllUtilitiesRegisteredFor(IDexterityFTI):
            self.invalidate(fti)

    @synchronized(lock)
    def invalidate(self, fti):
        if not IDexterityFTI.providedBy(fti):
            fti = queryUtility(IDexterityFTI, name=fti)
        if fti is not None:
            invalidate_cache(fti)
            self.invalidations += 1

    @synchronized(lock)
    @volatile
    def modified(self, fti):
        if fti:
            return fti._p_mtime

SCHEMA_CACHE = SchemaCache()


@implementer(ISchemaInvalidatedEvent)
class SchemaInvalidatedEvent(object):

    def __init__(self, portal_type):
        self.portal_type = portal_type


@adapter(ISchemaInvalidatedEvent)
def invalidate_schema(event):
    if event.portal_type:
        SCHEMA_CACHE.invalidate(event.portal_type)
    else:
        SCHEMA_CACHE.clear()


# here starts the code dealing wih dynamic schemas.
class SchemaNameEncoder(object):
    """Schema name encoding
    """

    key = (
        (' ', '_1_'),
        ('.', '_2_'),
        ('-', '_3_'),
        ('/', '_4_'),
    )

    def encode(self, s):
        for k, v in self.key:
            s = s.replace(k, v)
        return s

    def decode(self, s):
        for k, v in self.key:
            s = s.replace(v, k)
        return s

    def join(self, *args):
        return '_0_'.join([self.encode(a) for a in args if a])

    def split(self, s):
        return [self.decode(a) for a in s.split('_0_')]


def schemaNameToPortalType(schemaName):
    """Return a the portal_type part of a schema name
    """
    encoder = SchemaNameEncoder()
    return encoder.split(schemaName)[1]


def splitSchemaName(schemaName):
    """Return a tuple prefix, portal_type, schemaName
    """
    encoder = SchemaNameEncoder()
    items = encoder.split(schemaName)
    if len(items) == 2:
        return items[0], items[1], u""
    elif len(items) == 3:
        return items[0], items[1], items[2]
    else:
        raise ValueError("Schema name %s is invalid" % schemaName)
