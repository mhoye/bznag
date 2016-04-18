# bznag

Pretty much what it says on the tin: this is tool for nagging people about 
certain Bugzilla bugs have met certain conditions; in this case, that the 
creation date and last-modified dates are the same after some period of time.

Right now it's kind of gross - some things are in the code, some are in config
files... it needs a lot love, but it does have the all-important quality of
actually working right, which is not nothing.

bznag should be run by a daily cron job; sample config files contain two
json blobs; bznag-participants is a dictionary of { recipient : number-of-days }
(meaning "this recipient will be notified of bugs that go untouched for X days)
and bznag.cfg, which contains the owner of the bznag process and and some
information about where the mail server is and what account talks to it. 

Depending on your setup, you may need a username and password for both Bugzilla
and your mail server in plaintext in bznag.cfg. While filesystem permissions
should protect you from any particular disaster there, I nevertheless strongly
advise you to use unprivileged, dummy account(s) for that. I'm pretty sure that
there aren't any particularly malicious ways into our out of this code that
don't involve your Bugzilla installation already being compromised, but basic
precautions are always reasonable.

If you have questions, feedback or pull requests, please email Mike Hoye at 
mhoye@mozilla.com.

This software was released under the Mozilla Public License, version 2.0 or 
current latest, on April 18th, 2016.
