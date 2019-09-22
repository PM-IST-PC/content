import demistomock as demisto
from CommonServerPython import *

''' IMPORTS '''

import json


def test_module():
    """
    returning 'ok' indicates that the integration works like it suppose to. Connection to the service is successful.
    """
    return 'ok'


def fetch_incidents(last_run):
    """
    This function will execute each 1 minute.

    :return: next_run, list of incidents that will be created in Demisto
    """
    # Get the last fetch time, if exists
    last_fetch = last_run.get('last_fetch')

    # Handle first time fetch
    if last_fetch is None:
        last_fetch = 0

    incidents = [
        {
            "name": "Hello incident {}".format(last_fetch + 1),
            "rawJSON": json.dumps({
                "hello": "world"
            })
        },
        {
            "name": "Hello incident {}".format(last_fetch + 2),
            "rawJSON": json.dumps({
                "hello": "world"
            })
        }
    ]

    next_run = {"last_fetch": last_fetch + 2}
    return next_run, incidents


def say_hello_command(args):
    name = args.get("name")

    return "Hello {}".format(name)


def main():
    if demisto.command() == "test-module":
        results = test_module()
        return_outputs(readable_output=results, outputs=None)

    if demisto.command() == "helloworldsimple-say-hello":
        results = say_hello_command(demisto.args())
        return_outputs(readable_output=results, outputs=None)

    if demisto.command() == "fetch-incidents":
        next_run, incidents = fetch_incidents(demisto.getLastRun())
        demisto.setLastRun(next_run)
        demisto.incidents(incidents)


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()
