# -*- coding: utf-8 -*-

import os
import time
import logging
import unicodedata
import datetime

import string, pickle
from random import choice

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render

from django.contrib.auth.models import User
from userprofile.models import Activity
from userprofile.models import Profile as userprofile

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

import boto.ec2
import boto.ec2.cloudwatch
from amazon import s3_funcs
from amazon import s3_funcs_shortcuts
from vms.models import Cache

logger = logging.getLogger(__name__)

from django.core.mail import send_mail


AWS_REGIONS = {
    "ap-northeast-1":"Asia Pacific (Tokyo) Region",
    "ap-southeast-1":"Asia Pacific (Singapore) Region",
    "ap-southeast-2":"Asia Pacific (Sydney) Region",
    "eu-west-1":"EU (Ireland) Region",
    #"eu-central-1":"EU (Frankfurt) Region",
    "sa-east-1":"South America (Sao Paulo) Region",
    "us-east-1":"US East (Northern Virginia) Region",
    "us-west-1":"US West (Northern California) Region",
    "us-west-2":"US West (Oregon) Region",
}

def _remove_accents(data):
    return ''.join(x for x in unicodedata.normalize('NFKD', data) if x in string.ascii_letters).lower()

def _log_user_activity(userprofile, activity, link, function="", ip=""):

    activity = Activity.objects.create(user=userprofile.user,activity=activity,link=link)

    if(ip):
        activity.ip_addr = ip
        activity.save()

    if(activity.activity=="click"):
        userprofile.clicks += 1

    if(function):
        userprofile.function = function

    userprofile.save()

    #print '*'*100
    #print 'activity', activity, activity.activity

    return activity


def _simple_email_validation(email):

    if('@' and '.' in email):
        return True
    return False


def login_as_demo_user(request):

    user = User.objects.get(username='demo@demo.com')
    user.set_password('demo')
    user.save()

    login(request, authenticate(username='demo@demo.com', password='demo'))

    return HttpResponseRedirect("/")


def user_logout(request):

    print '-- logout'

    try:
        logout(request)
    except: pass

    print request.user

    return HttpResponseRedirect("/goodbye/")

@login_required()
def reset_cloud_settings(request):

    print '-- reset cloud settings'

    user = request.user
    profile = userprofile.objects.get(user=request.user)
    secret = profile.secret

    print request.user

    profile.aws_access_key = ""
    profile.aws_secret_key = ""
    profile.aws_ec2_verified = False
    profile.save()

    vms_cache = Cache.objects.get(user=user)
    vms_cache.vms_response = ""
    vms_cache.save()

    error = None

    ip = request.META['REMOTE_ADDR']
    _log_user_activity(profile,"click","/cloud/settings/reset/","change_password",ip=ip)

    return HttpResponseRedirect("/cloud/settings/")


def goodbye(request):

    return render_to_response('goodbye.html', {'request':request,}, context_instance=RequestContext(request))


def register(request):

    print '-- registration:'

    err = None

    if request.POST:

        print request.POST

        name = request.POST[u'username']
        email = request.POST[u'email']
        username = email

        try:
            if(request.POST['agree']!='on'):
                err = "must_agree_tos"
        except: err = "must_agree_tos"

        password1 = request.POST[u'password1']
        #password2 = request.POST[u'password2']
        password2 = password1

        print username


        if not password1 or not password2:
            err = "empty_password"
            print err

        if(password1 != password2):
            err = "password_mismatch"
            print err

        if not _simple_email_validation(email):
            err = "invalid_email_address"
            print err

        if not err:

            passwd = password1

            try:
                User.objects.create_user(username, email, passwd, last_login=datetime.datetime.now())
            except:
                err = "duplicate_username"
                print err

            if not err:

                user = authenticate(username=username, password=passwd)

                if(user):

                    secret = (''.join([choice(string.digits) for i in range(3)]) + '-' + \
                        ''.join([choice(string.letters + string.digits) for i in range(4)]) + '-' + \
                        ''.join([choice(string.digits) for i in range(5)])).upper()

                    agent_hash = (''.join([choice(string.letters + string.digits) for i in range(12)]))

                    username = _remove_accents(username)
                    #name = _remove_accents(name)

                    userprofile.objects.get_or_create(user=user,secret=secret,name=name,agent_hash=agent_hash,language="EN")
                    login(request, user)

                    request.session['language'] = "us"

                    print 'new user registered'
                    print username

                    return HttpResponseRedirect("/welcome/")


    return render_to_response('register.html', {'err':err,}, context_instance=RequestContext(request))


def auth(request):

    print '-- auth:'

    if(request.method == 'POST'):

        post = request.POST

        print post

        try:
            email = request.POST['username']
            passwprd = request.POST['password']
        except:
            print 'failed login code:1'
            return HttpResponseRedirect("/register")


        try:
            user = User.objects.get(email=email)
        except:
            print 'failed login code:2'
            return HttpResponseRedirect("/register")

        try:
            user = authenticate(username=user.username, password=passwprd)
            login(request, user)
        except:
            print 'failed login code:3'
            return HttpResponseRedirect("/register")

        print 'user logged in', user

        return HttpResponseRedirect("/")


    return render_to_response('login.html', {}, context_instance=RequestContext(request))

@login_required()
def cloud_settings(request):

    print '-- cloud settings:'

    user = request.user
    profile = userprofile.objects.get(user=request.user)
    secret = profile.secret

    user.last_login = datetime.datetime.now()
    user.save()

    print request.user

    ip = request.META['REMOTE_ADDR']
    _log_user_activity(profile,"click","/cloud/settings/","cloud_settings",ip=ip)

    profile_regions = profile.aws_enabled_regions.split(',')
    aws_ec2_verified = profile.aws_ec2_verified

    updated_regions = False
    if request.GET:
        updated = request.GET['updated']
        if(updated=='regions'): updated_regions = True

    return render_to_response('cloud_settings.html', {'aws_ec2_verified':aws_ec2_verified,'aws_regions':AWS_REGIONS,'profile_regions':profile_regions,'profile':profile,'secret':secret,'updated_regions':updated_regions,}, context_instance=RequestContext(request))


@login_required()
def cloud_settings_update_credentials(request):

    user = request.user
    profile = userprofile.objects.get(user=request.user)
    secret = profile.secret

    err = None

    aws_access_key  = request.POST['aws_access_key']
    aws_secret_key = request.POST['aws_access_secret']


    if(aws_secret_key):
        profile.aws_secret_key = aws_secret_key
        profile.save()
    else: err = "Missing AWS Secret"

    if(aws_access_key):
        profile.aws_access_key = aws_access_key
        profile.save()
    else: err = "Missing AWS Access Key"

    profile_regions = profile.aws_enabled_regions.split(',')

    try:
        ec2conn = boto.ec2.connect_to_region( "us-west-1",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key)
        regions_ = ec2conn.get_all_regions()
        profile.aws_ec2_verified = True
    except:
        err = "AWS verification failed.  Please check your Access Key and Secret and try again."
        profile.aws_ec2_verified = False

    profile.save()

    return render_to_response('cloud_settings.html', {'err':err,'aws_ec2_verified':profile.aws_ec2_verified,'aws_regions':AWS_REGIONS,'profile_regions':profile_regions,'profile':profile,'secret':secret,}, context_instance=RequestContext(request))


@login_required()
def change_password(request):

    print '-- change password:'

    user = request.user
    profile = userprofile.objects.get(user=request.user)
    secret = profile.secret

    print request.user

    error = None

    ip = request.META['REMOTE_ADDR']
    _log_user_activity(profile,"click","/account/password/","change_password",ip=ip)

    if(request.POST):

        current_passwd = request.POST['current_passwd']
        new_passwd = request.POST['new_passwd']
        new_passwd_repeat = request.POST['new_passwd_repeat']

        if(new_passwd != new_passwd_repeat):
            error = "Passwords do not match."

        user = authenticate(username=request.user, password=current_passwd)
        if(not user):
            error = "Wrong password."

        if(not error):
            user.set_password(new_passwd)
            user.save()
            return HttpResponseRedirect("/account/settings/")

    return render_to_response('account_change_password.html', {'error':error,}, context_instance=RequestContext(request))


@login_required()
def cloud_settings_update_regions(request):

    enable_regions = request.POST.getlist('checkboxes')

    c=0
    enabled_regions = ""
    for region in enable_regions:
        if(c):
            enabled_regions += ","+str(region)
        else:
            enabled_regions = str(region)
        c+=1

    user = request.user
    profile = userprofile.objects.get(user=request.user)
    profile.aws_enabled_regions = enabled_regions
    profile.save()

    return HttpResponseRedirect("/cloud/settings?updated=regions")


@login_required()
def account_settings(request):

    print '-- account settings:'

    user = request.user
    user.last_login = datetime.datetime.now()
    user.save()

    profile = userprofile.objects.get(user=request.user)
    secret = profile.secret

    print request.user

    ip = request.META['REMOTE_ADDR']
    _log_user_activity(profile,"click","/account/settings/","account_settings",ip=ip)

    return render_to_response('account_settings.html', {'request':request, 'aws_regions':AWS_REGIONS,'user':user,'profile':profile,}, context_instance=RequestContext(request))
