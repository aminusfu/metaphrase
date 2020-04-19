"""Authentication for Metaphrase.

Most of the time, the client sends a pair of cookies: 'login', which contains
the base64-encoded email address of the user, and 'token', a random hex string.
As long as these match the entries stored on the server, the user is
authenticated and request.login is set to the email address.

A token is created (or recreated) for a particular email address by POST'ing it
to login/ with the correct password.
"""

from binascii import hexlify
from os import urandom

import bcrypt
import cherrypy


cookie_domain = "metaphrase.org"


def set_cookie(name, value, timeout=86400 * 365, path='/', secure=True, httponly=False):
    c = cherrypy.response.cookie
    c[name] = value
    c[name]['Path'] = path
    if timeout:
        c[name]['max-age'] = timeout
    else:
        c[name]['expires'] = 0
    c[name]['domain'] = cookie_domain
    if secure:
        c[name]['secure'] = True
    if httponly:
        c[name]['httponly'] = True


tokens = {}


def token_auth(secure=True, debug=False):
    cherrypy.request.login = "public"

    if debug:
        cherrypy.log("Cookie: %s" % cherrypy.request.cookie)

    try:
        email = cherrypy.request.cookie['login'].value.decode('base64')
        token = cherrypy.request.cookie['token'].value
        if tokens[email] == token:
            cherrypy.request.login = email
            if debug:
                cherrypy.log("Token for email %s matched stored token." % email)
            return
        else:
            if debug:
                cherrypy.log("Token for email %s did not match stored token." % email)
    except KeyError:
        pass

    # Delete any token cookie.
    # Clients can then use the absence of a token to prompt for login.
    if 'token' in cherrypy.request.cookie:
        if debug:
            cherrypy.log("Deleting token from cookie.")
        set_cookie('token', '', 0, secure=secure, httponly=True)
cherrypy.tools.token_auth = cherrypy.Tool('on_start_resource', token_auth)


class Login(object):

    exposed = True

    @cherrypy.tools.json_in()
    def POST(self):
        req = cherrypy.serving.request
        body = req.json

        try:
            email = body["email"]
            password = body["password"]
        except KeyError:
            raise cherrypy.HTTPError(400, "An email and password are required.")

        secure = req.config['tools.token_auth.secure']

        # For some reason, encode('base64') adds a spurious trailing newline,
        # which chokes javascript's atob() and is ignored by decode('base64').
        set_cookie('login', email.encode('base64')[:-1], secure=secure)

        if email in salted_passwords:
            if bcrypt.checkpw(password, salted_passwords[email]):
                # Reuse any existing token. This allows one to log in
                # with the same account on multiple devices.
                if email not in tokens:
                    tokens[email] = hexlify(urandom(64))

                set_cookie('token', tokens[email], secure=secure)
                cherrypy.response.status = 204
                return

        raise cherrypy.HTTPError(401)


salted_passwords = {
    "fumanchu@aminus.org": "$2a$15$Ntwbp0H/HJXBuIJ2z7lhqe6xnz9rLTVvLNvSxbzURzl5va4AHQF3K"
}


def set_password(email, password):
    # The salt is stored in the password; no need to keep it around.
    # The number of rounds should be increased as computers get faster.
    # 2**15 takes a couple of seconds on my fast laptop in 2014.
    salted_passwords[email] = bcrypt.hashpw(password, bcrypt.gensalt(15))
