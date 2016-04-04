#!/usr/bin/env python
#
# Author: Mike Hoye
# Email: mhoye@mozilla.com
# License: MPL (current)

import smtplib
import json
import urllib2
import sys
import re
import logging, logging.handlers
import random
from datetime import date, timedelta
from os import mkdir
from bugzilla.agents import BMOAgent
from bugzilla.utils import get_credentials
from email.mime.text import MIMEText


def main():

    fmt = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt="%Y-%m-%d %H:%M:%S %Z")

    if "--quiet" not in sys.argv:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.DEBUG)
        logging.root.addHandler(sh)

    rfh = logging.handlers.RotatingFileHandler("/var/log/bznag.log",
                                               backupCount=10)
    rfh.setFormatter(fmt)
    rfh.setLevel(logging.DEBUG)
    logging.root.addHandler(rfh)
    logging.root.setLevel(logging.DEBUG)

    # cfg should be safe to load/handle
    config = json.load(open("/etc/bznag.cfg"))
    recipients = json.load(open("/etc/bznag-participants.cfg"))

    print recipients 
    mailout = findbugs(config, recipients)

    print mailout

#    sendTriageMail(users, bugs, strs, ranges, config)



def findbugs(cfg,recs):

    server = cfg["server"].encode("utf8")
    owner = cfg["owner"].encode("utf8")
    user =  cfg["user"]
    password =  cfg["password"]

    try:
        bzagent = BMOAgent(user,password)
        logging.info("Connected to " + str(server) )
    except:
        logging.info("Failed to connect to " + str(server))
        exit(-1)

    notif = dict() # key = intended recipient, value = list of bugs

    for ppl in recs.keys():
        
        buglist = list()
    # For each person, get the bugs have aged untouched to their level.
    # I'm making a design decision here to make this range window only
    # 7 days long - bugs older than that are being actively ignored.

        sla = recs[ppl]
        inc = 1

        date_to    = str(date.isoformat(date.today() - timedelta(sla))).encode("utf8")
        date_from  = str(date.isoformat(date.today() - timedelta(sla+inc))).encode("utf8")

    # Not proud of this next part. Store this properly in a file somewhere, you donkus.

    # NOTE: The reason it's laid out like this is because bztools doesn't,
    # seem to work with the "product=foo,bar" syntax, despite what the docs say


        option_sets = {
             'firefox': {
                'changed_field':'[Bug creation]',
                'changed_after':date_from,
                'changed_before':   date_to,
                'product':  'Firefox',
                'status':   'UNCONFIRMED'  },
#             'core': {
#                 'changed_field':'[Bug creation]',
#                 'changed_after':date_from,
#                 'changed_before':   date_to,
#                 'product':  'Core',
#                 'status':   'UNCONFIRMED'  },
#             'toolkit': {
#                 'changed_field':'[Bug creation]',
#                 'changed_after':date_from,
#                 'changed_before':   date_to,
#                 'product':  'Toolkit',
#                 'status':   'UNCONFIRMED'},
#             'firefox_untriaged': {
#                 'changed_field':'[Bug creation]',
#                 'changed_after':date_from,
#                 'changed_before':   date_to,
#                 'product':  'Firefox',
#                 'component':'Untriaged'},
#             'core_untriaged': {
#                 'changed_field':'[Bug creation]',
#                 'changed_after':date_from,
#                 'changed_before':   date_to,
#                 'product':  'Toolkit',
#                 'component':'Untriaged'},
#             'toolkit_untriaged': {
#                 'changed_field':'[Bug creation]',
#                 'changed_after':date_from,
#                 'changed_before':   date_to,
#                 'product':  'Core',
#                 'component':'Untriaged'
#               },
            }

        for options in option_sets.values():
            bugs = bzagent.get_bug_list(options) 
            buglist = list(set(buglist + bugs)) #add and dedupe
        
        notif[ppl] = buglist

        



    return ( notif ) 



def sendTriageMail(people, buglist, rangelist, stepslist, cfg):

    random.shuffle(people)
    random.shuffle(buglist) 
    random.shuffle(rangelist)
    random.shuffle(stepslist)

    triagemail  = dict()
    stepsmail   = dict()
    rangemail   = dict()


    while True:
        if not people:
            break
        if not rangelist and not stepslist and not buglist: #once we've emptied one of them out...
            break
        for t in people:
            if not t[0] in rangemail:
                rangemail[t[0]] = []
            if not t[0] in stepsmail:
                stepsmail[t[0]] = []
            if not t[0] in triagemail:
                triagemail[t[0]] = []

            if len(triagemail[t[0]]) + len(rangemail[t[0]]) + len(stepsmail[t[0]])  >= int(t[2]):
                people.remove(t)
                continue
            while buglist or rangelist or stepslist:
                if t[4] == "on" and rangelist: 
                        rangemail[t[0]].append(rangelist.pop())
                        break
                if t[5] == "on" and stepslist: 
                        stepsmail[t[0]].append(stepslist.pop())
                        break
                if t[0] in triagemail and buglist:
                    triagemail[t[0]].append(buglist.pop())
                    break

    # Ok, let's email some bugs.

    participants = list(set(triagemail.keys() + stepsmail.keys() + rangemail.keys()))

    mailoutlog = ""
    for rec in participants:
        mailoutlog = rec.encode("utf8")
        content = "Hello, " + rec.encode("utf8") + '''

Bug triage is the most important part of a program's life. We're building a smarter, faster Firefox for a smarter, faster Web, and we're grateful for your help.

Thank you.

'''

    if triagemail[rec]:
        content += '''

Today we would like your help triaging the following bugs:

'''
        bugurls = ""
        for boog in triagemail[rec]:
            mailoutlog += " " + str(boog.id).encode("utf-8")
            bugurls += '''Bug %s - http://bugzilla.mozilla.org/%s - %s

''' % ( str(boog.id).encode("utf-8"), str(boog.id).encode("utf-8"), str(boog.summary).encode("utf-8") )
        content += bugurls

    if rangemail[rec]:
        content += '''

Our engineers have asked for help finding a regression range for these bugs:

'''
        bugurls = ""
        for boog in rangemail[rec]:
            mailoutlog += " " + str(boog.id).encode("utf-8")
            bugurls += '''Bug %s - http://bugzilla.mozilla.org/%s - %s

''' % ( str(boog.id).encode("utf-8"), str(boog.id).encode("utf-8"), str(boog.summary).encode("utf-8") )
        content += bugurls

    if stepsmail[rec]:
        content += '''

We need to figure out the steps to reproduce the following bugs:

'''
        bugurls = ""
        for boog in stepsmail[rec]:
            mailoutlog += " " + str(boog.id).encode("utf-8")
            bugurls += '''Bug %s - http://bugzilla.mozilla.org/%s - %s

''' % ( str(boog.id).encode("utf-8"), str(boog.id).encode("utf-8"), str(boog.summary).encode("utf-8") )
        content += bugurls


        content += '''

There are a few things you can do to move these bugs forward:

  - Most importantly, sort the bug into the correct component: https://developer.mozilla.org/en-US/docs/Mozilla/QA/Confirming_unconfirmed_bugs
  - Use MozRegression to figure out exactly when a bug was introduced. You can learn about MozRegression here: http://mozilla.github.io/mozregression/
  - Search for similar bugs or duplicates and link them together if found: https://bugzilla.mozilla.org/duplicates.cgi
  - Check the flags, title and description for clarity and precision
  - Ask the reporter for related crash reports in about:crashes https://developer.mozilla.org/en-US/docs/Crash_reporting
  - Does this look like a small fix? Add [good first bug] to the whiteboard!

If you're just getting started and aren't sure how to proceed, this link will help:
  - https://developer.mozilla.org/en-US/docs/Mozilla/QA/Triaging_Bugs_for_Firefox

As always, the point of this exercise is to get the best information possible in front the right engineers. If you can reproduce them or isolate a test case, please add that information to the bug and change the status from "UNCONFIRMED" to "NEW".

Again, thank you. If you have any questions or concerns about the this process, you can join us on IRC in the #triage channel, or email Mike Hoye - mhoye@mozilla.com - directly.

'''
        smtp = cfg["smtp_server"].encode("utf8")
        sender = cfg["smtp_user"].encode("utf8")
        server = smtplib.SMTP(smtp)
        server.set_debuglevel(True)
        #server.connect(smtp)
        server.ehlo()
        #server.login(sender, cfg["smtp_pass"].encode("utf8"))
        msg = MIMEText(str(content).encode("utf8"))
        msg["Subject"] = str("Bugs to triage for %s" % (date.today()) ).encode("utf8")
        msg["From"] = cfg["smtp_user"].encode("utf8")
        msg["To"] = rec.encode("utf8")
        #msg["Reply-To"] = "noreply@mozilla.com"
        server.sendmail(sender, rec.encode("utf8") , msg.as_string())
        server.quit()
        logging.info(mailoutlog)

if __name__ == "__main__":
    main()

