# -*- coding: utf-8 -*-
# Copyright 2016-2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import mock
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


@mock.patch(
    'odoo.addons.auth_totp.wizards.res_users_authenticator_create.pyotp'
)
class TestResUsersAuthenticatorCreate(TransactionCase):

    def setUp(self):
        super(TestResUsersAuthenticatorCreate, self).setUp()

        self.test_user = self.env.ref('base.user_root')

    def _new_wizard(self, extra_values=None):
        base_values = {
            'name': 'Test Authenticator',
            'confirmation_code': 'Test',
            'user_id': self.test_user.id,
        }
        if extra_values is not None:
            base_values.update(extra_values)

        return self.env['res.users.authenticator.create'].create(base_values)

    def test_secret_key_default(self, pyotp_mock):
        '''Should default to random string generated by PyOTP'''
        pyotp_mock.random_base32.return_value = test_random = 'Test'
        test_wiz = self.env['res.users.authenticator.create']
        test_key = test_wiz.default_get(['secret_key'])['secret_key']

        self.assertEqual(test_key, test_random)

    def test_default_user_id_no_uid_in_context(self, pyotp_mock):
        '''Should return empty user recordset when no uid in context'''
        test_wiz = self.env['res.users.authenticator.create'].with_context(
            uid=None,
        )

        self.assertFalse(test_wiz._default_user_id())
        self.assertEqual(test_wiz._default_user_id()._name, 'res.users')

    def test_default_user_id_uid_in_context(self, pyotp_mock):
        '''Should return correct user record when there is a uid in context'''
        test_wiz = self.env['res.users.authenticator.create'].with_context(
            uid=self.test_user.id,
        )

        self.assertEqual(test_wiz._default_user_id(), self.test_user)

    def test_compute_qr_code_tag_no_user_id(self, pyotp_mock):
        '''Should not call PyOTP or set field if no user_id present'''
        test_wiz = self.env['res.users.authenticator.create'].with_context(
            uid=None,
        ).new()
        pyotp_mock.reset_mock()

        self.assertFalse(test_wiz.qr_code_tag)
        pyotp_mock.assert_not_called()

    def test_compute_qr_code_tag_user_id(self, pyotp_mock):
        '''Should set field to image with encoded PyOTP URI if user present'''
        pyotp_mock.TOTP().provisioning_uri.return_value = 'test:uri'
        test_wiz = self._new_wizard()

        self.assertEqual(
            test_wiz.qr_code_tag,
            '<img src="/report/barcode/?type=QR&amp;value='
            '%s&amp;width=300&amp;height=300">' % 'test%3Auri',
        )

    def test_compute_qr_code_tag_pyotp_use(self, pyotp_mock):
        '''Should call PyOTP twice with correct arguments if user_id present'''
        test_wiz = self._new_wizard()
        pyotp_mock.reset_mock()
        test_wiz._compute_qr_code_tag()

        pyotp_mock.TOTP.assert_called_once_with(test_wiz.secret_key)
        pyotp_mock.TOTP().provisioning_uri.assert_called_once_with(
            self.test_user.display_name,
            issuer_name=self.test_user.company_id.display_name,
        )

    def test_perform_validations_wrong_confirmation(self, pyotp_mock):
        '''Should raise correct error if PyOTP cannot verify code'''
        test_wiz = self._new_wizard()
        pyotp_mock.TOTP().verify.return_value = False

        with self.assertRaisesRegexp(ValidationError, 'confirmation code'):
            test_wiz._perform_validations()

    def test_perform_validations_right_confirmation(self, pyotp_mock):
        '''Should not raise error if PyOTP can verify code'''
        test_wiz = self._new_wizard()
        pyotp_mock.TOTP().verify.return_value = True

        try:
            test_wiz._perform_validations()
        except ValidationError:
            self.fail('A ValidationError was raised and should not have been.')

    def test_perform_validations_pyotp_use(self, pyotp_mock):
        '''Should call PyOTP twice with correct arguments'''
        test_wiz = self._new_wizard()
        pyotp_mock.reset_mock()
        test_wiz._perform_validations()

        pyotp_mock.TOTP.assert_called_once_with(test_wiz.secret_key)
        pyotp_mock.TOTP().verify.assert_called_once_with(
            test_wiz.confirmation_code,
        )

    def test_create_authenticator(self, pyotp_mock):
        '''Should create single authenticator record with correct info'''
        test_wiz = self._new_wizard()
        auth_model = self.env['res.users.authenticator']
        auth_model.search([('id', '>', 0)]).unlink()
        test_wiz._create_authenticator()
        test_auth = auth_model.search([('id', '>', 0)])

        self.assertEqual(len(test_auth), 1)
        self.assertEqual(
            (test_auth.name, test_auth.secret_key, test_auth.user_id),
            (test_wiz.name, test_wiz.secret_key, test_wiz.user_id),
        )

    def test_action_create_return_info(self, pyotp_mock):
        '''Should return info of user preferences action with user_id added'''
        test_wiz = self._new_wizard()
        test_info = self.env.ref('base.action_res_users_my').read()[0]
        test_info.update({'res_id': test_wiz.user_id.id})

        self.assertEqual(test_wiz.action_create(), test_info)

    def test_action_create_helper_use(self, pyotp_mock):
        '''Should call correct helper methods with proper arguments'''
        test_wiz = self._new_wizard()

        with mock.patch.multiple(
            test_wiz,
            _perform_validations=mock.DEFAULT,
            _create_authenticator=mock.DEFAULT,
        ):
            test_wiz.action_create()
            test_wiz._perform_validations.assert_called_once_with()
            test_wiz._create_authenticator.assert_called_once_with()
