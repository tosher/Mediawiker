# -*- coding: utf-8 -*-
__doc__ = 'Load browser cookies into a cookiejar'

import os
import sys
import time
import glob
try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib
from contextlib import contextmanager
import tempfile
try:
    import json
except ImportError:
    import simplejson as json
try:
    # should use pysqlite2 to read the cookies.sqlite on Windows
    # otherwise will raise the "sqlite3.DatabaseError: file is encrypted or is not a database" exception
    from pysqlite2 import dbapi2 as sqlite3
except ImportError:
    import sqlite3

# modified modules
# https://bitbucket.org/richardpenman/browsercookie
# https://github.com/borisbabic/browser_cookie3

# external libs
sys.path.insert(0, os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'keyring.zip')))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'pbkdf2.zip')))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'pyaes.zip')))

import keyring
# from Crypto.Protocol.KDF import PBKDF2
# https://pypi.python.org/pypi/pbkdf2
from pbkdf2 import PBKDF2
# from Crypto.Cipher import AES
# https://pypi.python.org/pypi/pyaes/1.6.0
from pyaes import AES


class TLDLazy(object):

    # https://en.wikipedia.org/wiki/Second-level_domain
    sld = [
        "asn.au",
        "com.au",
        "net.au",
        "id.au",
        "org.au",
        "edu.au",
        "gov.au",
        "csiro.au",
        "act.au",
        "nsw.au",
        "nt.au",
        "qld.au",
        "sa.au",
        "tas.au",
        "vic.au",
        "wa.au",
        "co.at",
        "or.at",
        "priv.at",
        "ac.at",
        "gv.at",
        "avocat.fr",
        "aeroport.fr",
        "veterinaire.fr",
        "co.hu",
        "film.hu",
        "lakas.hu",
        "ingatlan.hu",
        "sport.hu",
        "hotel.hu",
        "nz",
        "ac.nz",
        "co.nz",
        "geek.nz",
        "gen.nz",
        "kiwi.nz",
        "maori.nz",
        "net.nz",
        "org.nz",
        "school.nz",
        "cri.nz",
        "govt.nz",
        "health.nz",
        "iwi.nz",
        "mil.nz",
        "parliament.nz",
        "ac.il",
        "co.il",
        "org.il",
        "net.il",
        "k12.il",
        "gov.il",
        "muni.il",
        "idf.il",
        "ac.za",
        "gov.za",
        "law.za",
        "mil.za",
        "nom.za",
        "school.za",
        "net.za",
        "org.es",
        "gob.es",
        "nic.tr",
        "co.uk",
        "org.uk",
        "me.uk",
        "ltd.uk",
        "plc.uk",
        "net.uk",
        "sch.uk",
        "ac.uk",
        "gov.uk",
        "mod.uk",
        "mil.uk",
        "nhs.uk",
        "police.uk"
        "conf.au",
        "info.au",
        "otc.au",
        "telememo.au",
        "ab.ca",
        "bc.ca",
        "mb.ca",
        "nb.ca",
        "nf.ca",
        "nl.ca",
        "ns.ca",
        "nt.ca",
        "nu.ca",
        "on.ca",
        "pe.ca",
        "qc.ca",
        "sk.ca",
        "yk.ca",
        "tm.fr",
        "com.fr",
        "asso.fr",
        "co.nl",
        "ac.yu",
        "co.yu",
        "org.yu",
        "cg.yu",
        "co.tv "
    ]

    def get_tld_domain(self, domain_name):
        # only prev level
        _parts = domain_name.split('.')
        _tld = '.'.join(_parts[1:])
        return _tld if _tld not in self.sld else domain_name


class BrowserCookieError(Exception):
    pass


@contextmanager
def create_local_copy(cookie_file):
    """Make a local copy of the sqlite cookie database and return the new filename.
    This is necessary in case this database is still being written to while the user browses
    to avoid sqlite locking errors.
    """
    # check if cookie file exists
    if os.path.exists(cookie_file):
        # copy to random name in tmp folder
        tmp_cookie_file = tempfile.NamedTemporaryFile(suffix='.sqlite').name
        open(tmp_cookie_file, 'wb').write(open(cookie_file, 'rb').read())
        yield tmp_cookie_file
    else:
        raise BrowserCookieError('Can not find cookie file at: ' + cookie_file)

    os.remove(tmp_cookie_file)


class BrowserCookieLoader(object):
    def __init__(self, cookie_files=None, domain_name=None):
        cookie_files = cookie_files or self.find_cookie_files()
        self.cookie_files = list(cookie_files)
        self.domain_name_tld = TLDLazy().get_tld_domain(domain_name) if domain_name else None

    def find_cookie_files(self):
        '''Return a list of cookie file locations valid for this loader'''
        raise NotImplementedError

    def get_cookies(self):
        '''Return all cookies (May include duplicates from different sources)'''
        raise NotImplementedError

    def load(self):
        '''Load cookies into a cookiejar'''
        cookie_jar = cookielib.CookieJar()
        for cookie in self.get_cookies():
            cookie_jar.set_cookie(cookie)
        return cookie_jar


class Chrome(BrowserCookieLoader):

    SQLREQ_FULL = "SELECT host_key, path, secure, expires_utc, name, value, encrypted_value FROM cookies"
    SQLREQ_DOMAIN = "SELECT host_key, path, secure, expires_utc, name, value, encrypted_value FROM cookies WHERE host_key like ?"

    def __str__(self):
        return 'chrome'

    def find_cookie_files(self):
        for pattern in [
            os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cookies'),
            os.path.expanduser('~/.config/chromium/Default/Cookies'),
            os.path.expanduser('~/.config/chromium/Profile */Cookies'),
            os.path.expanduser('~/.config/google-chrome/Default/Cookies'),
            os.path.expanduser('~/.config/google-chrome/Profile */Cookies'),
            os.path.join(os.getenv('APPDATA', ''), r'..\Local\Google\Chrome\User Data\Default\Cookies'),
        ]:
            for result in glob.glob(pattern):
                yield result

    def get_cookies(self):
        salt = b'saltysalt'
        length = 16
        if sys.platform == 'darwin':
            # running Chrome on OSX
            my_pass = keyring.get_password('Chrome Safe Storage', 'Chrome')
            my_pass = my_pass.encode('utf8')
            iterations = 1003
            key = PBKDF2(my_pass, salt, length, iterations)

        elif sys.platform.startswith('linux'):
            # running Chrome on Linux
            my_pass = 'peanuts'.encode('utf8')
            iterations = 1
            key = PBKDF2(my_pass, salt, length, iterations)

        elif sys.platform == 'win32':
            key = None
        else:
            raise BrowserCookieError('Unsupported operating system: ' + sys.platform)

        for cookie_file in self.cookie_files:
            with create_local_copy(cookie_file) as tmp_cookie_file:
                con = sqlite3.connect(tmp_cookie_file)
                cur = con.cursor()

                # cur.execute('SELECT host_key, path, secure, expires_utc, name, value, encrypted_value FROM cookies;')
                if self.domain_name_tld:
                    cur.execute(self.SQLREQ_DOMAIN, ('%%%s' % self.domain_name_tld,))
                else:
                    cur.execute(self.SQLREQ_FULL)

                for item in cur.fetchall():
                    host, path, secure, expires, name = item[:5]
                    value = self._decrypt(item[5], item[6], key=key)
                    yield create_cookie(host, path, secure, expires, name, value)
                con.close()

    def _decrypt(self, value, encrypted_value, key):
        """Decrypt encoded cookies
        """
        if (sys.platform == 'darwin') or sys.platform.startswith('linux'):
            if value or (encrypted_value[:3] != b'v10'):
                return value

            # Encrypted cookies should be prefixed with 'v10' according to the
            # Chromium code. Strip it off.
            encrypted_value = encrypted_value[3:]

            # Strip padding by taking off number indicated by padding
            # eg if last is '\x0e' then ord('\x0e') == 14, so take off 14.
            def clean(x):
                last = x[-1]
                if isinstance(last, int):
                    return x[:-last].decode('utf8')
                else:
                    return x[:-ord(last)].decode('utf8')

            iv = b' ' * 16
            cipher = AES.new(key, AES.MODE_CBC, IV=iv)
            decrypted = cipher.decrypt(encrypted_value)
            return clean(decrypted)
        else:

            if value:
                return value

            # Must be win32 (on win32, all chrome cookies are encrypted)
            try:
                import win32crypt
            except ImportError:
                raise BrowserCookieError('win32crypt must be available to decrypt Chrome cookie on Windows')
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode()


class Firefox(BrowserCookieLoader):

    SQLREQ_FULL = "SELECT host, path, isSecure, expiry, name, value FROM moz_cookies"
    SQLREQ_DOMAIN = "SELECT host, path, isSecure, expiry, name, value FROM moz_cookies WHERE host like ?"

    def __str__(self):
        return 'firefox'

    def find_cookie_files(self):
        if sys.platform == 'darwin':
            cookie_files = glob.glob(os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*.default/cookies.sqlite'))
        elif sys.platform.startswith('linux'):
            cookie_files = glob.glob(os.path.expanduser('~/.mozilla/firefox/*.default*/cookies.sqlite'))
        elif sys.platform == 'win32':
            cookie_files = glob.glob(os.path.join(os.getenv('PROGRAMFILES', ''), 'Mozilla Firefox/profile/cookies.sqlite')) or \
                glob.glob(os.path.join(os.getenv('PROGRAMFILES(X86)', ''), 'Mozilla Firefox/profile/cookies.sqlite')) or \
                glob.glob(os.path.join(os.getenv('APPDATA', ''), 'Mozilla/Firefox/Profiles/*.default*/cookies.sqlite'))
        else:
            raise BrowserCookieError('Unsupported operating system: ' + sys.platform)
        if cookie_files:
            return cookie_files
        else:
            raise BrowserCookieError('Failed to find Firefox cookies')

    def get_cookies(self):
        for cookie_file in self.cookie_files:
            with create_local_copy(cookie_file) as tmp_cookie_file:
                con = sqlite3.connect(tmp_cookie_file)
                cur = con.cursor()

                # cur.execute('select host, path, isSecure, expiry, name, value from moz_cookies')
                if self.domain_name_tld:
                    cur.execute(self.SQLREQ_DOMAIN, ('%%%s' % self.domain_name_tld,))
                else:
                    cur.execute(self.SQLREQ_FULL)

                for item in cur.fetchall():
                    yield create_cookie(*item)
                con.close()

                # current sessions are saved in sessionstore.js
                session_file = os.path.join(os.path.dirname(cookie_file), 'sessionstore.js')
                if os.path.exists(session_file):
                    try:
                        json_data = json.loads(open(session_file, 'rb').read().decode())
                    except ValueError as e:
                        print('Error parsing firefox session JSON:', str(e))
                    else:
                        expires = str(int(time.time()) + 3600 * 24 * 7)
                        for window in json_data.get('windows', []):
                            for cookie in window.get('cookies', []):
                                if not self.domain_name_tld or cookie.get('host', '').endswith(self.domain_name_tld):
                                    yield create_cookie(cookie.get('host', ''), cookie.get('path', ''), False, expires, cookie.get('name', ''), cookie.get('value', ''))
                # it's normal, when browser is not running..
                # else:
                #     print('Firefox session filename does not exist:', session_file)


def create_cookie(host, path, secure, expires, name, value):
    """Shortcut function to create a cookie
    """
    return cookielib.Cookie(0, name, value, None, False, host, host.startswith('.'), host.startswith('.'), path, True, secure, expires, False, None, None, {})


def chrome(cookie_file=None, domain_name=None):
    """Returns a cookiejar of the cookies used by Chrome
    """
    return Chrome(cookie_file, domain_name).load()


def firefox(cookie_file=None, domain_name=None):
    """Returns a cookiejar of the cookies and sessions used by Firefox
    """
    return Firefox(cookie_file, domain_name).load()


def _get_cookies():
    '''Return all cookies from all browsers'''
    for klass in [Chrome, Firefox]:
        try:
            for cookie in klass().get_cookies():
                yield cookie
        except BrowserCookieError:
            pass


def load():
    """Try to load cookies from all supported browsers and return combined cookiejar
    """
    cookie_jar = cookielib.CookieJar()

    for cookie in sorted(_get_cookies(), key=lambda cookie: cookie.expires):
        cookie_jar.set_cookie(cookie)

    return cookie_jar
