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
```json
{
  "initial": {
    // Initial state of the PR before any handlers process the payload.
    // Defaults:
    "labels": [],
    "diff": "",
    "new_contributor": false,
    "assignee": null,
  },
  "expected": {
    // Expected state of the PR after all the handlers process
    // the following payload.
    // Only fields present in this object will be checked.
    // comments: 5,
    // labels: ["S-awaiting-review"],
    // assignee: "jdm"
  },
  "payload": {
    // Github API event payload in JSON format
  }
}
```
Each test runs with a mock Github API provider, so no account information
or network connection is required to run the test suite.
