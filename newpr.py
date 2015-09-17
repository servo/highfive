#!/usr/bin/env python
from payloadhandler import TravisPayloadHandler, GithubPayloadHandler
import cgi, cgitb
import ConfigParser

if __name__ == "__main__":
    print "Content-Type: text/html;charset=utf-8"
    print

    cgitb.enable()

    config = ConfigParser.RawConfigParser()
    config.read('./config')
    user = config.get('github', 'user')
    token = config.get('github', 'token')

    post = cgi.FieldStorage()
    payload_raw = post.getfirst("payload",'')
    payload = json.loads(payload_raw)

    if "action" in payload:
        payload_handler = GithubPayloadHandler(payload)
    elif "state" in payload:
        payload_handler = TravisPayloadHandler(payload)

    owner, repo = payload_handler.extract_globals_from_payload()
    payload_handler.handle_payload(user, token, owner, repo)