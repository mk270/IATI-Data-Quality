
#  IATI Data Quality, tools for Data QA on IATI-formatted  publications
#  by Mark Brough, Martin Keegan, Ben Webb and Jennifer Smith
#
#  Copyright (C) 2013  Publish What You Fund
#
#  This programme is free software; you may redistribute and/or modify
#  it under the terms of the GNU Affero General Public License v3.0

from flask import Flask, render_template, flash, request, Markup, \
    session, redirect, url_for, escape, Response, abort, send_file
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser,
                            confirm_login, fresh_login_required)
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed

from iatidataquality import app
from iatidataquality import db
from iatidq import dqusers


users = [{
        'username': 'mark',
        'password': '1234',
        'name': 'Mark',
        'permissions': [{
            'permission_name': 'admin',
            'permission_method': 'full'
            }]
        },
        {
        'username': 'fred',
        'password': '1234',
        'name': 'Fred',
        'permissions': [{
            'permission_name': 'tests',
            'permission_method': 'edit',
            'permission_value': '1'
            }]
        }]
for user in users:
    dqusers.addUser(user)
    the_user = dqusers.user_by_username(user['username'])
    for permission in user['permissions']:
        
        permission["user_id"]=the_user.id
        dqusers.addUserPermission(permission)

class Anonymous(AnonymousUser):
    name = u"Anonymous"

login_manager = LoginManager()

login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."
login_manager.refresh_view = "reauth"

@login_manager.user_loader
def load_user(id):
    return dqusers.user(id)

login_manager.setup_app(app)

@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST" and "username" in request.form:
        user = dqusers.user_by_username(request.form["username"])
        if (user and user.check_password(request.form["password"])):
            remember = request.form.get("remember", "no") == "yes"
            if login_user(user, remember=remember):
                flash("Logged in!", "success")
                return redirect(request.args.get("next") or url_for("home"))
            else:
                flash("Sorry, but you could not log in.", "error")
        else:
            flash(u"Invalid username or password.", "error")
    return render_template("login.html")

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'success')
    return redirect(request.args.get('next') or '/')
