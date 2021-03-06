
#  IATI Data Quality, tools for Data QA on IATI-formatted  publications
#  by Mark Brough, Martin Keegan, Ben Webb and Jennifer Smith
#
#  Copyright (C) 2013  Publish What You Fund
#
#  This programme is free software; you may redistribute and/or modify
#  it under the terms of the GNU Affero General Public License v3.0

from iatidq import db

import models
import unicodecsv

def downloadUserData():
    fh = urllib2.urlopen(ORG_FREQUENCY_API_URL)
    return _updateOrganisationFrequency(fh)

def importUserDataFromFile():
    filename = 'tests/users.csv'
    with file(filename) as fh:
        return _importUserData(fh)

def _importUserData(fh):

    def getCreateUser(row):
        username = row['username']
        password = row['password']
        name = row['name']
        email_address = row['email_address']
        organisation = row['organisation']

        user = addUser({
            'username': username,
            'password': password,
            'name': name,
            'email_address': email_address,
            'organisation': organisation
        })
        return user

    def perm(user, organisation_id, t):
        name, method = t
        return {
            "user_id": user.id,
            "permission_name": name,
            "permission_method": method,
            "permission_value": organisation_id
            }

    def getCSOPermissions(organisation_id, 
                role, active, primary, user, permissions):
        perms = []
        if active == 'active':
            perms = [
                ('cso', 'role'),
                ('organisation', 'view'),
                ('survey_pwyfreview', 'view'),
                ('survey_donorcomments', 'view'),
                ('survey_pwyffinal', 'view'),
                ('survey_finalised', 'view')
                ]
            if primary == 'primary':
                perms += [
                    ('survey_cso', 'edit')
                    ]

        return [ perm(user, organisation_id, i) for i in perms ]

    def getDonorPermissions(organisation_id, 
                role, active, primary, user, permissions):
        perms = []
        permissions = [{
                'user_id': user.id,
                'permission_name': 'organisation',
                'permission_method': 'role',
                'permission_value': ''
            }]

        if active == 'active':
            perms = [
                ('organisation', 'view'),
                ('survey_donorreview', 'view'),
                ('survey_donorcomments', 'view'),
                ('survey_finalised', 'view')
                ]
            if primary == 'primary':
                perms += [
                    ('organisation', 'edit'),
                    ('survey_donorreview', 'edit'),
                    ('survey_donorcomments', 'edit'),
                    ('survey_finalised', 'edit'),
                    ('organisation_feedback', 'create')
                    ]

        return permissions + [ perm(user, organisation_id, i) for i in perms ]

    def generate_permissions():
        permissions = []
        data = unicodecsv.DictReader(fh)
        for row in data:

            user=getCreateUser(row)
            
            organisation_id = row['organisation_id']
            role = row['role']
            active = row['active']
            primary = row['primary']

            if role == 'donor':
                permissions = getDonorPermissions(organisation_id, 
                        role, active, primary, user, permissions)
            elif role == 'CSO':
                permissions = getCSOPermissions(organisation_id, 
                        role, active, primary, user, permissions)
            elif role == 'admin':
                permissions.append({
                    'user_id': user.id,
                    'permission_name': 'admin',
                    'permission_method': 'role',
                    'permission_value': ''
                })
            elif role == 'super':
                permissions.append({
                    'user_id': user.id,
                    'permission_name': 'super',
                    'permission_method': 'view',
                    'permission_value': ''
                })
            
        for permission in permissions:
            addUserPermission(permission)

    generate_permissions()

def user(user_id=None):
    if user_id:
        user = models.User.query.filter_by(id=user_id
                    ).first()
        return user
    else:
        users = models.User.query.all()
        return users

def user_by_username(username=None):
    if username:
        user = models.User.query.filter_by(username=username
                    ).first()
        return user
    return None

def addUser(data):
    checkU = models.User.query.filter_by(username=data["username"]
                ).first()
    if not checkU:
        with db.session.begin():
            newU = models.User()
            newU.setup(
                username = data["username"],
                password = data["password"],
                name = data.get('name'),
                email_address = data.get('email_address'),
                organisation = data.get('organisation')
                )
            db.session.add(newU)
        return newU
    return checkU

def addUserPermission(data):
    checkP = models.UserPermission.query.filter_by(user_id=data["user_id"],
                permission_name=data["permission_name"],
                permission_method=data.get("permission_method"),
                permission_value=data.get("permission_value")
                ).first()
    if not checkP:
        with db.session.begin():
            newP = models.UserPermission()
            newP.setup(
                user_id = data["user_id"],
                permission_name=data["permission_name"],
                permission_method=data.get("permission_method"),
                permission_value=data.get("permission_value")
                )
            db.session.add(newP)
        return newP
    return None

def deleteUserPermission(permission_id):
    checkP = models.UserPermission.query.filter_by(id=permission_id).first()
    if checkP:
        with db.session.begin():
            db.session.delete(checkP)
        return True
    return None

def deleteUser(username):
    checkU = models.User.query.filter_by(username=username).first()
    if checkU:
        with db.session.begin():
            db.session.delete(checkU)
        return True
    return None

def userPermissions(user_id):
    checkP = models.UserPermission.query.filter_by(user_id=user_id
            ).all()
    return checkP

def surveyPermissions(organisation_code):
    checkP = db.session.query(models.User, models.UserPermission
            ).filter(models.UserPermission.permission_name.like("survey%")
            ).filter(models.UserPermission.permission_value==organisation_code
            ).join(models.UserPermission
            ).all()
    return checkP
