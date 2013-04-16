
#  IATI Data Quality, tools for Data QA on IATI-formatted  publications
#  by Mark Brough, Martin Keegan, Ben Webb and Jennifer Smith
#
#  Copyright (C) 2013  Publish What You Fund
#
#  This programme is free software; you may redistribute and/or modify
#  it under the terms of the GNU Affero General Public License v3.0

from flask import render_template, flash, request, Markup, \
    session, redirect, url_for, escape, Response, abort, send_file
import StringIO
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser,
                            confirm_login, fresh_login_required)
from sqlalchemy import func
from datetime import datetime

from iatidataquality import app
from iatidataquality import db

import os
import sys
import json

current = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from iatidq import models, dqdownload, dqregistry, dqindicators, dqorganisations, dqpackages
import aggregation

import StringIO
import unicodecsv
import tempfile
import spreadsheet

@app.route("/publisher_conditions/")
@app.route("/publisher_conditions/<id>/")
def publisher_conditions(id=None):
    if (id is not None):
        pc = db.session.query(models.PublisherCondition.id,
                               models.PublisherCondition.description,
                               models.PublisherCondition.operation,
                               models.PublisherCondition.condition,
                               models.PublisherCondition.condition_value,
                               models.PackageGroup.title.label("packagegroup_name"),
                               models.PackageGroup.id.label("packagegroup_id"),
                               models.Test.name.label("test_name"),    
                               models.Test.description.label("test_description"),
                               models.Test.id.label("test_id")
                            ).filter_by(id=id
                            ).join(models.PackageGroup, models.Test).first()
        return render_template("publisher_condition.html", pc=pc)
    else:
        pcs = db.session.query(models.PublisherCondition.id,
                               models.PublisherCondition.description,
                               models.PackageGroup.title.label("packagegroup_name"),
                               models.PackageGroup.id.label("packagegroup_id"),
                               models.Test.name.label("test_name"),    
                               models.Test.description.label("test_description"),
                               models.Test.id.label("test_id")
                            ).order_by(models.PublisherCondition.id
                            ).join(models.PackageGroup, models.Test
                            ).all()
        return render_template("publisher_conditions.html", pcs=pcs)

@app.route("/publisher_conditions/<id>/edit/", methods=['GET', 'POST'])
def publisher_conditions_editor(id=None):
    publishers = models.PackageGroup.query.order_by(
        models.PackageGroup.id).all()
    tests = models.Test.query.order_by(models.Test.id).all()
    if (request.method == 'POST'):
        if (request.form['password'] == app.config["SECRET_PASSWORD"]):
            pc = models.PublisherCondition.query.filter_by(id=id).first_or_404()
            pc.description = request.form['description']
            pc.publisher_id = int(request.form['publisher_id'])
            pc.test_id = int(request.form['test_id'])
            pc.operation = int(request.form['operation'])
            pc.condition = request.form['condition']
            pc.condition_value = request.form['condition_value']
            pc.file = request.form['file']
            pc.line = int(request.form['line'])
            pc.active = int(request.form['active'])
            db.session.add(pc)
            db.session.commit()
            flash('Updated', "success")
            return redirect(url_for('publisher_conditions_editor', id=pc.id))
        else:
            flash('Incorrect password', "error")
            pc = models.PublisherCondition.query.filter_by(id=id).first_or_404()
            return render_template("publisher_condition_editor.html", 
                                   pc=pc, publishers=publishers, tests=tests)
    else:
        pc = models.PublisherCondition.query.filter_by(id=id).first_or_404()
        return render_template("publisher_condition_editor.html", 
                               pc=pc, publishers=publishers, tests=tests)

@app.route("/publisher_conditions/new/", methods=['GET', 'POST'])
def publisher_conditions_new(id=None):
    publishers = models.PackageGroup.query.order_by(
        models.PackageGroup.id).all()
    tests = models.Test.query.order_by(models.Test.id).all()
    if (request.method == 'POST'):
        pc = models.PublisherCondition()
        pc.description = request.form['description']
        pc.publisher_id = int(request.form['publisher_id'])
        pc.test_id = int(request.form['test_id'])
        pc.operation = int(request.form['operation'])
        pc.condition = request.form['condition']
        pc.condition_value = request.form['condition_value']
        pc.file = request.form['file']
        pc.line = int(request.form['line'])
        pc.active = int(request.form['active'])
        if (request.form['password'] == app.config["SECRET_PASSWORD"]):
            db.session.add(pc)
            db.session.commit()
            flash('Created new condition', "success")
            return redirect(url_for('publisher_conditions_editor', id=pc.id))
        else:
            flash('Incorrect password', "error")
            return render_template("publisher_condition_editor.html", 
                                   pc=pc, publishers=publishers, tests=tests)
    else:
        return render_template("publisher_condition_editor.html", 
                               pc={}, publishers=publishers, tests=tests)

@app.route("/publisher_conditions/import/step<step>", methods=['GET', 'POST'])
@app.route("/publisher_conditions/import/", methods=['GET', 'POST'])
def import_publisher_conditions(step=None):
    # Step=1: form; submit to step2
    # 
    if (step == '2'):
        if (request.method == 'POST'):
            from iatidq import dqimportpublisherconditions
            if (request.form['password'] == app.config["SECRET_PASSWORD"]):
                if (request.form.get('local')):
                    results = dqimportpublisherconditions.importPCsFromFile()
                else:
                    url = request.form['url']
                    results = dqimportpublisherconditions.importPCsFromUrl(url)
                if (results):
                    flash('Parsed tests', "success")
                    return render_template(
                        "import_publisher_conditions_step2.html", 
                        results=results, step=step)
                else:
                    results = None
                    flash('There was an error importing your tests', "error")
                    return redirect(url_for('import_publisher_conditions'))
            else:
                flash('Wrong password', "error")
                return render_template("import_publisher_conditions.html")
    elif (step=='3'):
        out = []
        for row in request.form.getlist('include'):
            publisher_id = request.form['pc['+row+'][publisher_id]']
            test_id = request.form['pc['+row+'][test_id]']
            operation = request.form['pc['+row+'][operation]']
            condition = request.form['pc['+row+'][condition]']
            condition_value = request.form['pc['+row+'][condition_value]']
            pc = models.PublisherCondition.query.filter_by(
                publisher_id=publisher_id, test_id=test_id, 
                operation=operation, condition=condition, 
                condition_value=condition_value).first()
            if (pc is None):
                pc = models.PublisherCondition()
            pc.publisher_id=publisher_id
            pc.test_id=test_id
            pc.operation = operation
            pc.condition = condition
            pc.condition_value = condition_value
            pc.description = request.form['pc['+row+'][description]']
            db.session.add(pc)
        db.session.commit()
        flash('Successfully updated publisher conditions', 'success')
        return redirect(url_for('publisher_conditions'))
    else:
        return render_template("import_publisher_conditions.html")

@app.route("/publisher_conditions/export/")
def export_publisher_conditions():
    conditions = db.session.query(
        models.PublisherCondition.description).distinct().all()
    conditionstext = ""
    for i, condition in enumerate(conditions):
        if (i != 0):
            conditionstext = conditionstext + "\n"
        conditionstext = conditionstext + condition.description

    strIO = StringIO.StringIO()
    strIO.write(str(conditionstext))
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename="publisher_structures.txt",
                     as_attachment=True)