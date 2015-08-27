from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from model_mommy import mommy

from devilry.devilry_account.models import User, UserEmail, UserName


class TestUser(TestCase):
    def test_get_full_name(self):
        user = mommy.make('devilry_account.User', fullname="Elvis Aron Presley")
        self.assertEqual("Elvis Aron Presley", user.get_full_name())

    def test_get_full_name_fallback_to_shortname(self):
        user = mommy.make('devilry_account.User', shortname='test@example.com')
        self.assertEqual("test@example.com", user.get_full_name())

    def test_get_displayname_has_fullname(self):
        user = mommy.make('devilry_account.User', shortname='elvis',
                          fullname="Elvis Aron Presley")
        self.assertEqual("Elvis Aron Presley (elvis)", user.get_displayname())

    def test_get_displayname_fullname_blank(self):
        user = mommy.make('devilry_account.User', shortname='elvis')
        self.assertEqual("elvis", user.get_displayname())

    def test_is_active(self):
        user = mommy.make('devilry_account.User')
        self.assertTrue(user.is_active)

    def test_is_not_active(self):
        user = mommy.make('devilry_account.User',
                          suspended_datetime=timezone.now())
        self.assertFalse(user.is_active)

    def test_clean_suspended_reason_with_blank_suspended_datetime(self):
        user = mommy.make('devilry_account.User',
                          suspended_datetime=None,
                          suspended_reason='Test')
        with self.assertRaisesMessage(ValidationError,
                                      'Can not provide a reason for suspension when suspension time is blank.'):
            user.clean()

    def test_clean_suspended_reason_with_suspended_datetime(self):
        user = mommy.make('devilry_account.User',
                          suspended_datetime=timezone.now(),
                          suspended_reason='Test')
        user.clean()

    def test_clean_set_lastname_from_fullname(self):
        user = mommy.make('devilry_account.User')
        user.fullname = 'The Test User'
        user.clean()
        self.assertEqual(user.lastname, 'User')

    def test_clean_unset_lastname_when_no_fullname(self):
        user = mommy.make('devilry_account.User',
                          fullname='The Test User')
        user.fullname = ''
        user.clean()
        self.assertEqual(user.lastname, '')


class TestUserQuerySet(TestCase):
    def test_prefetch_related_notification_emails(self):
        user = mommy.make('devilry_account.User')
        notification_useremail1 = mommy.make('devilry_account.UserEmail',
                                             user=user,
                                             use_for_notifications=True,
                                             email='test1@example.com')
        notification_useremail2 = mommy.make('devilry_account.UserEmail',
                                             user=user,
                                             use_for_notifications=True,
                                             email='test2@example.com')
        mommy.make('devilry_account.UserEmail',
                   user=user,
                   use_for_notifications=False,
                   email='unused@example.com')
        with self.assertNumQueries(2):
            user_with_prefetch = User.objects\
                .prefetch_related_notification_emails().first()
            self.assertEqual(len(user_with_prefetch.notification_useremail_objects), 2)
            self.assertTrue(isinstance(user_with_prefetch.notification_useremail_objects,
                                       list))
            self.assertEqual({notification_useremail1, notification_useremail2},
                             set(user_with_prefetch.notification_useremail_objects))
            self.assertEqual({'test1@example.com', 'test2@example.com'},
                             set(user_with_prefetch.notification_emails))

    def test_prefetch_related_primary_email(self):
        user = mommy.make('devilry_account.User')
        primary_useremail = mommy.make('devilry_account.UserEmail',
                                       user=user,
                                       email='test@example.com',
                                       is_primary=True)
        mommy.make('devilry_account.UserEmail',
                   user=user,
                   is_primary=None)
        mommy.make('devilry_account.UserEmail',
                   user=user,
                   is_primary=None)
        with self.assertNumQueries(2):
            user_with_prefetch = User.objects\
                .prefetch_related_primary_email().first()
            self.assertEqual(len(user_with_prefetch.primary_useremail_objects), 1)
            self.assertTrue(isinstance(user_with_prefetch.primary_useremail_objects, list))
            self.assertEqual(primary_useremail,
                             user_with_prefetch.primary_useremail_objects[0])
            self.assertEqual(primary_useremail,
                             user_with_prefetch.primary_useremail_object)
            self.assertEqual('test@example.com',
                             user_with_prefetch.primary_email)

    def test_prefetch_related_primary_username(self):
        user = mommy.make('devilry_account.User')
        primary_username = mommy.make('devilry_account.UserName',
                                      user=user,
                                      username='testuser',
                                      is_primary=True)
        mommy.make('devilry_account.UserEmail',
                   user=user,
                   is_primary=None)
        mommy.make('devilry_account.UserEmail',
                   user=user,
                   is_primary=None)
        with self.assertNumQueries(2):
            user_with_prefetch = User.objects\
                .prefetch_related_primary_username().first()
            self.assertEqual(len(user_with_prefetch.primary_username_objects), 1)
            self.assertTrue(isinstance(user_with_prefetch.primary_username_objects, list))
            self.assertEqual(primary_username,
                             user_with_prefetch.primary_username_objects[0])
            self.assertEqual(primary_username,
                             user_with_prefetch.primary_username_object)
            self.assertEqual('testuser',
                             user_with_prefetch.primary_username)


class TestUserManager(TestCase):
    def test_create_user_username(self):
        user = User.objects.create_user(username='testuser')
        self.assertEqual(user.shortname, 'testuser')
        self.assertEqual(user.username_set.count(), 1)
        self.assertEqual(user.username_set.first().username, 'testuser')
        self.assertEqual(user.useremail_set.count(), 0)

    def test_create_user_email(self):
        user = User.objects.create_user(email='testuser@example.com')
        self.assertEqual(user.shortname, 'testuser@example.com')
        self.assertEqual(user.username_set.count(), 0)
        self.assertEqual(user.useremail_set.count(), 1)
        self.assertEqual(user.useremail_set.first().email, 'testuser@example.com')
        self.assertTrue(user.useremail_set.first().use_for_notifications)

    def test_create_user_username_or_email_required(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user()

    def test_create_user_no_password(self):
        user = User.objects.create_user(email='testuser@example.com')
        self.assertFalse(user.has_usable_password())

    def test_create_user_password(self):
        user = User.objects.create_user(email='testuser@example.com', password='test')
        self.assertTrue(user.has_usable_password())

    def test_create_user_fullname(self):
        user = User.objects.create_user(email='testuser@example.com',
                                        fullname='The Test User')
        self.assertEqual(user.fullname, 'The Test User')

    def test_create_user_set_lastname_from_fullname(self):
        user = User.objects.create_user(email='testuser@example.com',
                                        fullname='The Test User')
        self.assertEqual(user.lastname, 'User')

    def test_create_user_unset_lastname_when_no_fullname(self):
        user = User.objects.create_user(email='testuser@example.com',
                                        fullname='')
        self.assertEqual(user.lastname, '')

    def test_get_by_email(self):
        user = mommy.make('devilry_account.User')
        mommy.make('devilry_account.UserEmail', user=user, email='test@example.com')
        self.assertEqual(
            User.objects.get_by_email(email='test@example.com'),
            user)

    def test_get_by_email_doesnotexist(self):
        user = mommy.make('devilry_account.User')
        mommy.make('devilry_account.UserEmail', user=user, email='test2@example.com')
        with self.assertRaises(User.DoesNotExist):
            User.objects.get_by_email(email='test@example.com')

    def test_get_by_username(self):
        user = mommy.make('devilry_account.User')
        mommy.make('devilry_account.UserName', user=user, username='test@example.com')
        self.assertEqual(
            User.objects.get_by_username(username='test@example.com'),
            user)

    def test_get_by_username_doesnotexist(self):
        user = mommy.make('devilry_account.User')
        mommy.make('devilry_account.UserName', user=user, username='test2@example.com')
        with self.assertRaises(User.DoesNotExist):
            User.objects.get_by_username(username='test@example.com')


class TestUserEmail(TestCase):
    def test_email_unique(self):
        mommy.make('devilry_account.UserEmail', email='test@example.com')
        with self.assertRaises(IntegrityError):
            mommy.make('devilry_account.UserEmail', email='test@example.com')

    def test_clean_is_primary_can_not_be_false(self):
        useremail = mommy.make('devilry_account.UserEmail')
        useremail.clean()  # No error
        useremail.is_primary = False
        with self.assertRaisesMessage(ValidationError,
                                      'is_primary can not be False. Valid values are: True, None.'):
            useremail.clean()

    def test_clean_useremail_set_is_primary_unsets_other(self):
        user = mommy.make('devilry_account.User')
        useremail1 = mommy.make('devilry_account.UserEmail',
                                user=user,
                                is_primary=True)
        useremail2 = mommy.make('devilry_account.UserEmail',
                                user=user,
                                is_primary=None)
        useremail2.is_primary = True
        useremail2.clean()
        self.assertIsNone(UserEmail.objects.get(pk=useremail1.pk).is_primary)


class TestUserName(TestCase):
    def test_username_unique(self):
        mommy.make('devilry_account.UserName', username='test')
        with self.assertRaises(IntegrityError):
            mommy.make('devilry_account.UserName', username='test')

    def test_is_primary_unique(self):
        user = mommy.make('devilry_account.User')
        mommy.make('devilry_account.UserName', user=user, is_primary=True)
        with self.assertRaises(IntegrityError):
            mommy.make('devilry_account.UserName', user=user, is_primary=True)

    def test_is_primary_not_unique_for_none(self):
        user = mommy.make('devilry_account.User')
        mommy.make('devilry_account.UserName', user=user, is_primary=None)
        mommy.make('devilry_account.UserName', user=user, is_primary=None)

    def test_clean_is_primary_can_not_be_false(self):
        usernameobject = mommy.make('devilry_account.UserName')
        usernameobject.clean()  # No error
        usernameobject.is_primary = False
        with self.assertRaisesMessage(ValidationError,
                                      'is_primary can not be False. Valid values are: True, None.'):
            usernameobject.clean()

    def test_clean_usernam_set_is_primary_unsets_other(self):
        user = mommy.make('devilry_account.User')
        usernameobject1 = mommy.make('devilry_account.UserName',
                                     user=user,
                                     is_primary=True)
        usernameobject2 = mommy.make('devilry_account.UserName',
                                     user=user,
                                     is_primary=None)
        usernameobject2.is_primary = True
        usernameobject2.clean()
        self.assertIsNone(UserName.objects.get(pk=usernameobject1.pk).is_primary)