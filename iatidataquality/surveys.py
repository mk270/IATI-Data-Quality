
#  IATI Data Quality, tools for Data QA on IATI-formatted  publications
#  by Mark Brough, Martin Keegan, Ben Webb and Jennifer Smith
#
#  Copyright (C) 2013  Publish What You Fund
#
#  This programme is free software; you may redistribute and/or modify
#  it under the terms of the GNU Affero General Public License v3.0

from flask import Flask, render_template, flash, request, Markup, \
    session, redirect, url_for, escape, Response, abort, send_file

from flask.ext.login import current_user
from iatidataquality import app
from iatidataquality import db

import os
import sys
import unicodecsv

current = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from iatidq import dqindicators, dqsurveys, dqorganisations, dqusers
from iatidq.models import *

import usermanagement

@app.route("/surveys/admin/")
@usermanagement.perms_required()
def surveys_admin():
    surveys = dqsurveys.surveys()
    workflows = dqsurveys.workflows()
    publishedstatuses=dqsurveys.publishedStatus()
    return render_template("surveys/surveys_admin.html", 
                           workflows=workflows,
                           publishedstatuses=publishedstatuses,
                           surveys=surveys,
                           admin=usermanagement.check_perms('admin'),
                           loggedinuser=current_user)

@app.route("/surveys/create/", methods=["GET", "POST"])
@app.route("/surveys/<organisation_code>/create/", methods=["GET", "POST"])
def create_survey(organisation_code=None):
    return "You're trying to create a survey"

def get_old_organisation_id(organisation_code='GB-1'):
    path = app.config["DATA_STORAGE_DIR"]
    old_organisation_file = os.path.join(path, '2012_2013_organisation_mapping.csv')

    old_organisation_data = unicodecsv.DictReader(file(old_organisation_file))
    for row in old_organisation_data:
        if row['2013_id'] == organisation_code:
            return row['2012_id']

def get_old_indicators():
    path = app.config["DATA_STORAGE_DIR"]
    old_indicators_file = os.path.join(path, '2012_indicators.csv')
    old_indicators_data = unicodecsv.DictReader(file(old_indicators_file))

    indicator_data = {}
    for row in old_indicators_data:
        if ((row["question_number"]) and (row["2013_indicator_name"])):
            indicator_data[int(row["question_number"])] = row["2013_indicator_name"]
    return indicator_data
    
def get_organisation_results(organisation_code, newindicators):
    old_organisation_id = get_old_organisation_id(organisation_code)
    indicators = get_old_indicators()

    path = app.config["DATA_STORAGE_DIR"]

    old_results_file = os.path.join(path, '2012_results.csv')
    old_results_data = unicodecsv.DictReader(file(old_results_file))

    data = {}

    for d in old_results_data:
        if (d["target_id"] == old_organisation_id):
            try:
                question_id = int(d["question_id"])
                d["newindicator_id"] = indicators[(int(d["question_id"]))]
                data[indicators[(int(d["question_id"]))]] = d
            except KeyError:
                pass
    for indicator in newindicators:
        try:
            print data[indicator.name]
        except KeyError:
            data[indicator.name] = {
                'result': ''
            }
    return data

def completion_percentage(survey):
    if survey.Workflow.name == 'researcher':
        pct_complete = (1.0/7.0)*100
    elif survey.Workflow.name == 'send':
        pct_complete = (2.0/7.0)*100
    elif survey.Workflow.name == 'donorreview':
        pct_complete = (3.0/7.0)*100
    elif survey.Workflow.name == 'pwyfreview':
        pct_complete = (4.0/7.0)*100
    elif survey.Workflow.name == 'donorcomments':
        pct_complete = (5.0/7.0)*100
    elif survey.Workflow.name == 'pwyffinal':
        pct_complete = (6.0/7.0)*100
    elif survey.Workflow.name == 'finalised':
        pct_complete = (7.0/7.0)*100
    ## FIXME: this can NameError
    return pct_complete

@app.route("/organisations/<organisation_code>/survey/")
@usermanagement.perms_required('survey', 'view')
def organisation_survey(organisation_code=None):
    organisation = dqorganisations.organisations(organisation_code)
    make_sure_survey_exists = dqsurveys.getOrCreateSurvey({'organisation_id':organisation.id})
    survey = dqsurveys.getSurvey(organisation_code)
    surveydata = dqsurveys.getSurveyDataAllWorkflows(organisation_code)
    workflows = dqsurveys.workflows()
    pct_complete = completion_percentage(survey)
    users = dqusers.surveyPermissions(organisation_code)
        
    return render_template("surveys/survey.html", 
                           organisation=organisation,
                           survey=survey,
                           workflows=workflows,
                           pct_complete=pct_complete,
                           surveydata=surveydata,
                           users=users,
                           admin=usermanagement.check_perms('admin'),
                           loggedinuser=current_user)

def getTimeRemainingNotice(deadline):
    time_remaining = ((deadline.date())-(datetime.utcnow().date()))
    if time_remaining.days >1:
        time_remaining_notice = "You have " + str(time_remaining.days) + " days to submit your response."
    else:
        time_remaining_notice = "Today is the last day for making any changes to your survey."
    return time_remaining_notice

def __survey_process(organisation, workflow, request, organisationsurvey, published_accepted):
    indicators = request.form.getlist('indicator')
    workflow_id = workflow.Workflow.id
    currentworkflow_deadline = organisationsurvey.currentworkflow_deadline

    for indicator in indicators:
        if request.form.get(indicator+"-ordinal_value"):
            published_format= dqsurveys.publishedFormat('document').id
            ordinal_value = request.form.get(indicator+"-ordinal_value")
        elif request.form.get(indicator+"-noformat"):
            published_format= dqsurveys.publishedFormat('document').id
            ordinal_value = None
        else:
            published_format = request.form.get(indicator+"-publishedformat")
            ordinal_value = None
        data = {
            'organisationsurvey_id': organisationsurvey.id,
            'indicator_id': indicator,
            'workflow_id': workflow_id,
            'published_status': request.form.get(indicator+"-published"),
            'published_source': request.form.get(indicator+"-source"),
            'published_comment': request.form.get(indicator+"-comments"),
            'published_format': published_format,
            'published_accepted': published_accepted,
            'ordinal_value': ordinal_value
        }
        surveydata = dqsurveys.addSurveyData(data)
    
    if 'submit' in request.form:
        if workflow.Workflow.id == organisationsurvey.currentworkflow_id:
        # save data, change currentworkflow_id to leadsto
            dqsurveys.advanceSurvey(organisationsurvey)
            flash('Successfully submitted survey data', 'success')
        else:
            flash("Your survey data was updated.", 'warning')
    else:
        time_remaining_notice = getTimeRemainingNotice(organisationsurvey.currentworkflow_deadline)

        flash('Note: your survey has not yet been submitted. '+ time_remaining_notice, 'warning')

def _survey_process_collect(organisation, workflow, request, organisationsurvey):
    return __survey_process(organisation, workflow, request, organisationsurvey, None)

def _survey_process_review(organisation, workflow, request, organisationsurvey):
    return __survey_process(organisation, workflow, request, organisationsurvey, None)

def _survey_process_finalreview(organisation, workflow, request, organisationsurvey):
    return __survey_process(organisation, workflow, request, organisationsurvey, 
                            request.form.get(indicator+"-agree"))

def _survey_process_comment(organisation, workflow, request, organisationsurvey):
    return __survey_process(organisation, workflow, request, organisationsurvey, 
                            request.form.get(indicator+"-agree"))

def _survey_process_send(organisation, workflow, request, organisationsurvey):
    indicators = request.form.getlist('indicator')

    #FIXME: need to actually send

    dqsurveys.advanceSurvey(organisationsurvey)
    flash('Successfully sent survey to donor.', 'success')

old_publication_status= {
    '4': {
        'text': 'Always published',
        'class': 'success'
        },
    '3':  {
        'text': 'Sometimes published',
        'class': 'warning'
        },
    '2':  {
        'text': 'Collected',
        'class': 'important'
        },
    '1':  {
        'text': 'Not collected',
        'class': 'inverse'
        },
    '0':  {
        'text': 'Unknown',
        'class': ''
        },
    "": {
        'text': '',
        'class': ''
        }
    }

def organisation_survey_view(organisation_code, workflow, workflow_name, organisationsurvey, allowed_to_edit):
    organisation = Organisation.query.filter_by(
        organisation_code=organisation_code).first_or_404()

    surveydata = dqsurveys.getSurveyData(organisation_code, workflow_name)
    surveydata_allworkflows = dqsurveys.getSurveyDataAllWorkflows(organisation_code)

    indicators = dqindicators.indicators("pwyf2013")
    org_indicators = dqorganisations._organisation_indicators_split(
        organisation, 2)
        
    twentytwelvedata=get_organisation_results(organisation_code, indicators)
    publishedstatuses = dqsurveys.publishedStatus()
    publishedstatuses = dict(map(lambda ps: (ps.id, ps), publishedstatuses))
    publishedformats = dqsurveys.publishedFormat()
    publishedformats = dict(map(lambda pf: (pf.id, pf), publishedformats))

    template_path = "surveys/_survey_"+workflow.WorkflowType.name+".html"
    return render_template(
        template_path, 
        organisation=organisation,
        indicators=indicators,
        org_indicators = org_indicators,
        twentytwelvedata=twentytwelvedata,
        old_publication_status=old_publication_status,
        publishedstatuses=publishedstatuses,
        workflow=workflow,
        surveydata=surveydata_allworkflows,
        organisationsurvey=organisationsurvey,
        allowed_to_edit=allowed_to_edit,
        publishedformats=publishedformats,
        admin=usermanagement.check_perms('admin'),
        loggedinuser=current_user)

@app.route("/organisations/<organisation_code>/survey/<workflow_name>/", methods=["GET", "POST"])
def organisation_survey_edit(organisation_code=None, workflow_name=None):
    
    workflow = dqsurveys.workflows(workflow_name)
    if not workflow:
        flash('That workflow does not exist.', 'error')
        return abort(404)

    organisation = dqorganisations.organisations(organisation_code)
    organisationsurvey = dqsurveys.getOrCreateSurvey({
                'organisation_id': organisation.id
                })

    def allowed(method):
        permission_name = "survey_" + workflow_name
        permission_value = {'organisation_code': organisation_code}
        return usermanagement.check_perms(permission_name,
                                          method,
                                          permission_value)
    allowed_to_edit = allowed("edit")
    allowed_to_view = allowed("view")
    
    if not allowed_to_view:
        flash("Sorry, you do not have permission to view that survey", 'error')
        if request.referrer is not None:
            redir_to = request.referrer
        else:
            redir_to = url_for('home')
        return redirect(redir_to)

    if request.method=='POST':
        if not allowed_to_edit:
            flash("Sorry, you do not have permission to update that survey", 'error')
            if request.referrer is not None:
                redir_to = request.referrer
            else:
                redir_to = url_for('home')
        
        if (workflow.WorkflowType.name=='collect'):
            _survey_process_collect(organisation, workflow, request, organisationsurvey)
        elif workflow.WorkflowType.name=='send':
            if workflow.Workflow.id == organisationsurvey.currentworkflow_id:
                _survey_process_send(organisation_code, workflow, request, organisationsurvey)
            else:
                flash("Not possible to send survey to donor because it's not at the current stage in the workflow. Maybe you didn't submit the data, or maybe you already sent it to the donor?", 'error')
        elif workflow.WorkflowType.name=='review':
            _survey_process_review(organisation, workflow, request, organisationsurvey)
        elif workflow.WorkflowType.name=='comment':
            _survey_process_comment(organisation, workflow, request, organisationsurvey)
        elif workflow.WorkflowType.name=='finalreview':
            _survey_process_finalreview(organisation, workflow, request, organisationsurvey)
        elif workflow.WorkflowType.name=='finalised':
            return "finalised"
        return redirect(url_for("organisations", organisation_code=organisation_code))

    else:
        return organisation_survey_view(organisation_code, workflow, workflow_name, organisationsurvey, allowed_to_edit)
