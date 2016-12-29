Highfive
========

GitHub hooks to provide an encouraging atmosphere for new contributors.

Docs for the highfive instance for servo/servo repository live [on the Servo
wiki](https://github.com/servo/servo/wiki/Highfive).

## Design

Highfive is built as a modular, loosely-coupled set of handlers for Github
API events. Each time an API event is processed, each handler is given the
opportunity to respond to it, either by making direct API calls (such as
manipulating PR labels) or using cross-handler features such as logging a
warning (which are aggregated at the end and posted as a single comment).

## Testing

Per-handler tests can be run using `python test.py`. These consist of
a set of JSON documents collected from the `tests/` subdirectory of
each handler, using the following format:

```js
{
  "initial": {
    // Initial state of the PR before any handlers process the payload.
    "labels": [],
    "diff": "",
    "new_contributor": false,
    "assignee": null
  },
  "expected": {
    // Expected state of the PR after all the handlers process the following payload.
    // Only fields in this object will be checked. Example fields are shown below.
    "comments": 5,
    "labels": ["S-awaiting-review"],
    "assignee": "jdm"
  },
  "payload": {
    // Github API event payload in JSON format.
  }
}
```

Each test runs with a mock Github API provider, so no account information
or network connection is required to run the test suite.

## Enabling a repo

Visit the repo's webhook settings page at
`https://github.com/org/repo/settings/hooks`.

Create a new webhook, pointing at your highfive instance's location:

Payload URL: `http://99.88.777.666/highfive/newpr.py`
Content type: `application/x-www-form-urlencoded`
Leave the 'secret' field blank.
Let me select individual events: Issue Comment, Pull Request, Status
Check the box by 'Active'

Add the bot's github account as a Collaborator to the repo with Write access.
If automatically assigning a reviewer is desired for the repo, add a new section
to the highfive instance's `collaborators.ini` with the list of desired reviewers:

```
[user/repo]
reviewer_name =
another_reviewer_name =
```

## Configuring a Highfive

Copy `config.sample` to `config`. Add the username of the account that will be
commenting as highfive. When logged into that account, visit
`https://github.com/settings/tokens` and create a token with the `public_repo`
permission.

Add that access token's value to the `token` field of the config.
