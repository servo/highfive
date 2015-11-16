#!/usr/bin/env python

from payloadhandler import TravisPayloadHandler, GithubPayloadHandler
from errorlogparser import ServoErrorLogParser
from githubapiprovider import GithubApiProvider
from travisciapiprovider import TravisCiApiProvider
import cgi, cgitb
import ConfigParser

def extract_globals_from_payload(payload):
    if "action" in payload:
        owner, repo = _extract_globals_from_github_payload(payload)
    elif "state" in payload:
        owner, repo = _extract_globals_from_travis_payload(payload)

    return owner, repo

def _extract_globals_from_github_payload(payload):
    if payload["action"] == "created":
        owner = payload['repository']['owner']['login']
        repo = payload['repository']['name']
    else:
        owner = payload['pull_request']['base']['repo']['owner']['login']
        repo = payload['pull_request']['base']['repo']['name']
    
    return owner, repo

def _extract_globals_from_travis_payload(payload):
    return payload['name'].split('/')

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

    owner, repo = extract_globals_from_payload(payload)
    github = GithubApiProvider(user, token, owner, repo)
    
    if "action" in payload:
        payload_handler = GithubPayloadHandler(github)
    elif "state" in payload:
        travis = TravisCiApiProvider()
        error_parser = ServoErrorLogParser()
        payload_handler = TravisPayloadHandler(github, travis, error_parser)
    else:
        pass

    if payload_handler:
        payload_handler.handle_payload(payload)