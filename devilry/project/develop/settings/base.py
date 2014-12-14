import os
from os.path import join
from os.path import exists
from os.path import dirname
from os.path import abspath

from devilry.project.common.settings import *
from .log import create_logging_conf




#########################################################
#
# Setup the developfiles/ directory as storage for
# generated files during development
#
#########################################################
REPOROOT = dirname(dirname(dirname(dirname(dirname(abspath(__file__))))))
if not exists(join(REPOROOT, 'manage.py')):
    raise SystemExit('Could not find manage.py in REPOROOT.')
developfilesdir = join(REPOROOT, 'developfiles')
if not exists(developfilesdir):
    os.mkdir(developfilesdir)
logdir = join(developfilesdir, 'log')
if not exists(logdir):
    os.mkdir(logdir)
MEDIA_ROOT = join(developfilesdir, "filestore")
DEVILRY_FSHIERDELIVERYSTORE_ROOT = join(developfilesdir, 'deliverystorehier')
LOGGING = create_logging_conf(logdir)


#########################################################
#
# Make it possible to select database engine using
# the DEVDB environent variable. Example usage:
#
#    $ DEVDB=postgres python manage.py runserver
#
# We default to ``DEVDB=sqlite``.
#
#########################################################

dbengine = os.environ.get('DEVDB', 'sqlite')
if dbengine == 'sqlite':
    DATABASES = {
        "default": {
            'ENGINE': 'django.db.backends.sqlite3',  # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': join(developfilesdir, 'db.sqlite3'),    # Or path to database file if using sqlite3.
            'USER': '',             # Not used with sqlite3.
            'PASSWORD': '',         # Not used with sqlite3.
            'HOST': '',             # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',             # Set to empty string for default. Not used with sqlite3.
        }
    }
elif dbengine == 'postgres':
    from django_dbdev.backends.postgres import DBSETTINGS
    DATABASES = {
        'default': DBSETTINGS
    }
else:
    raise ValueError('Invalid DEVDB: "{}". Use one of: "sqlite", "postgres".'.format(dbengine))

INSTALLED_APPS += [
    'seleniumhelpers',
    'djangosenchatools',
    # 'raven.contrib.django.raven_compat', # Sentry client (Raven)
    'devilry.devilry_sandbox',

    'devilry.project.develop',
    'simple_rest',

    # Not apps, but here for the Django test system to discover them:
    'devilry.utils',
    'devilry.restful',
    'devilry.simplified',

    ## For Trix development
    #'trix',
    #'trix_extjshelpers',
    #'trix_restful',
    #'trix_simplified',
]


INTERNAL_IPS = ["127.0.0.1"]
DEBUG = True
TEMPLATE_DEBUG = DEBUG
EXTJS4_DEBUG = True
STATIC_ROOT = 'static'
CRISPY_TEMPLATE_PACK = 'bootstrap3'

DEVILRY_ENABLE_MATHJAX = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = '+g$%**q(w78xqa_2)(_+%v8d)he-b_^@d*pqhq!#2p*a7*9e9h'

# If no admins are set, no emails are sent to admins
ADMINS = (
     ('Devilry admin', 'admin@example.com'),
)
MANAGERS = ADMINS
ROOT_URLCONF = 'devilry.project.develop.dev_urls'

DEVILRY_SCHEME_AND_DOMAIN = 'https://devilry.example.com'

DEVILRY_DELIVERY_STORE_BACKEND = 'devilry.apps.core.deliverystore.FsHierDeliveryStore'
DEVILRY_FSHIERDELIVERYSTORE_INTERVAL = 10
DEVILRY_SYNCSYSTEM = 'FS (Felles Studentsystem)'

## django_seleniumhelpers
## - http://django_seleniumhelpers.readthedocs.org/
#SKIP_SELENIUMTESTS = True
SELENIUM_BROWSER = 'Chrome'  # Default selenium browser
SELENIUM_DEFAULT_TIMEOUT = 8


PASSWORD_HASHERS = (
    #    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
)


#DEVILRY_USERADMIN_USER_READONLY_FIELDS = ['email', 'is_superuser', 'is_staff', 'is_active']
#DEVILRY_USERADMIN_DEVILRYUSERPROFILE_READONLY_FIELDS = ['languagecode', 'full_name']
#DEVILRY_USERADMIN_USER_CHANGE_VIEW_MESSAGE = 'This is a test.'
#DEVILRY_USERADMIN_USER_ADD_VIEW_MESSAGE = 'This is a add test.'
#DEVILRY_USERADMIN_PASSWORD_HELPMESSAGE = 'Passwords are handled by Our Awesome External User Management System. Follow <a href="https://awesome.example.com">this link</a> to reset passwords.'


##################################################################################
# Haystack (search)
##################################################################################
HAYSTACK_CONNECTIONS = {  # Whoosh
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': join(developfilesdir, 'devilry_whoosh_index'),
    },
}
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'


##################################################################################
# Make Devilry speak in typical university terms (semester instead of period, ...)
##################################################################################
INSTALLED_APPS += ['devilry.devilry_university_translations']
DEVILRY_JAVASCRIPT_LOCALE_OVERRIDE_APPS = ('devilry.devilry_university_translations',)


##################################################################################
# Email
##################################################################################
DEVILRY_SEND_EMAIL_TO_USERS = True
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = join(developfilesdir, 'email_log')
EMAIL_BACKEND = os.environ.get('DEVILRY_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEVILRY_EMAIL_DEFAULT_FROM = 'devilry-support@example.com'
DEVILRY_SYSTEM_ADMIN_EMAIL='devilry-support@example.com'
DEVILRY_DEFAULT_EMAIL_SUFFIX='@example.com'

## If you want to test with a "real" smtp server instead of the file backend, see:
##     https://docs.djangoproject.com/en/dev/topics/email/#testing-email-sending
## In short, uncomment the settings below and run the built in smtpd server in python:
##      python -m smtpd -n -c DebuggingServer localhost:1025
## The smtpd server prints emails to stdout.
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST = 'localhost'
#EMAIL_PORT = 1025





#######################################################################
# Various developertools/settings
#######################################################################

# The if's below is just to make it easy to toggle these settings on and off during development
profiler_middleware = False
if profiler_middleware:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + [
        'devilry.utils.profile.ProfilerMiddleware' # Enable profiling. Just add ?prof=yes to any url to see a profile report
    ]

#DELAY_MIDDLEWARE_TIME = (80, 120) # Wait for randint(*DELAY_MIDDLEWARE_TIME)/100.0 before responding to each request when using DelayMiddleware
#delay_middleware = True
#if delay_middleware:
    #MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + [
        #'devilry.utils.delay_middleware.DelayMiddleware'
    #]

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ['devilry.apps.developertools.middleware.FakeLoginMiddleware']



#######################################################################
# Logging
#######################################################################

if not 'devilry.utils.logexceptionsmiddleware.TracebackLoggingMiddleware' in MIDDLEWARE_CLASSES:
    MIDDLEWARE_CLASSES.append('devilry.utils.logexceptionsmiddleware.TracebackLoggingMiddleware')

# MIDDLEWARE_CLASSES += [
    #'devilry.utils.profile.ProfilerMiddleware' # Enable profiling. Just add ?prof=yes to any url to see a profile report
# ]


##############################################################
#
# Cache
#
##############################################################
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

##############################################################
#
# Rosetta
# - see: https://github.com/mbi/django-rosetta
# - uncomment it here, in dev_urls, and in developments-base.cfg to use rosetta
#
##############################################################
#INSTALLED_APPS += ['rosetta']


##############################################################
#
# Sentry
#
##############################################################
# RAVEN_CONFIG = {
#     'dsn': 'http://85cc6c611c904a0ebb4afd363fe60fe4:32988134adad4044bc7d13f85f318498@localhost:9000/2',
# }


##################################################################################
# Celery
##################################################################################
CELERY_ALWAYS_EAGER = True

## For testing celery
#CELERY_ALWAYS_EAGER = False
#CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
#BROKER_URL = 'django://'
#INSTALLED_APPS += ['kombu.transport.django']

## For testing django-celery-email
#INSTALLED_APPS += ['djcelery_email']
#EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
#CELERY_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
