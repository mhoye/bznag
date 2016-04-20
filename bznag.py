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
import pprint
from datetime import date, timedelta
from os import mkdir
from bugzilla.agents import BMOAgent
from bugzilla.utils import get_credentials
from email.mime.text import MIMEText


def main():

    pp = pprint.PrettyPrinter(indent=4)

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
    recipients = json.load(open("/var/local/bznag/bznag-participants.cfg"))
    alerts = findbugs(config, recipients)
    sendSLAMail(alerts, recipients, config)


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
    # 2 days long - bugs older than that are being actively ignored.

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
             'core': {
                 'changed_field':'[Bug creation]',
                 'changed_after':date_from,
                 'changed_before':   date_to,
                 'product':  'Core',
                 'status':   'UNCONFIRMED'  },
             'toolkit': {
                 'changed_field':'[Bug creation]',
                 'changed_after':date_from,
                 'changed_before':   date_to,
                 'product':  'Toolkit',
                 'status':   'UNCONFIRMED'},
             'firefox_untriaged': {
                 'changed_field':'[Bug creation]',
                 'changed_after':date_from,
                 'changed_before':   date_to,
                 'product':  'Firefox',
                 'component':'Untriaged'},
             'core_untriaged': {
                 'changed_field':'[Bug creation]',
                 'changed_after':date_from,
                 'changed_before':   date_to,
                 'product':  'Toolkit',
                 'component':'Untriaged'},
             'toolkit_untriaged': {
                 'changed_field':'[Bug creation]',
                 'changed_after':date_from,
                 'changed_before':   date_to,
                 'product':  'Core',
                 'component':'Untriaged'
               },
           }

        bugs = list()
        for options in option_sets.values():
            for b in bzagent.get_bug_list(options):
                if str(b.creation_time) == str(b.last_change_time):
                    bugs.append(b)
                    print str(b.id) + " - " + str(b.creation_time) + " - " + str(b.last_change_time) 
            buglist = list(set(buglist + bugs)) #add and dedupe
            
        notif[ppl] = buglist

    return ( notif ) 

def sendSLAMail(mailout,sla,cfg):


    # Ok, let's email some bugs.

    mailoutlog = ""
    for recipient in mailout.keys():
        mailoutlog = recipient.encode("utf8")
        content = "As part of Mozilla's triage SLA process, you have asked to be notified\n" + \
                  "when new bugs have gone " + str(sla[recipient]) + " days without being acted upon.\n"
        content += "The following bugs have met that criteria:\n\n" 
        bugurls = ""
        for boog in mailout[recipient]:
            mailoutlog += " " + str(boog.id).encode("utf-8")
            bugurls += '''Bug %s - http://bugzilla.mozilla.org/%s - %s

''' % ( str(boog.id).encode("utf-8"), str(boog.id).encode("utf-8"), str(boog.summary).encode("utf-8") )
        content += bugurls
        content += "\nPlease examine these bugs at your earliest convenience, and either move them\n" +\
                   "to the correct category or assign them to or needinfo a developer.\n\n" +\
                   "If you have any questions about this notification service, please contact Mike Hoye."


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
        msg["To"] = recipient.encode("utf8")
        #msg["Reply-To"] = "noreply@mozilla.com"
        server.sendmail(sender, recipient.encode("utf8") , msg.as_string())
        server.quit()
        logging.info(mailoutlog)

if __name__ == "__main__":
    main()

