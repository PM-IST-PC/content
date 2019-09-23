from CommonServerPython import *
from CommonServerUserPython import *
import demistomock as demisto

''' IMPORTS '''
from typing import Dict, Tuple, Optional, List, Union
import urllib3

# Disable insecure warnings
urllib3.disable_warnings()

"""GLOBALS/PARAMS
Attributes:
    INTEGRATION_NAME:
        Name of the integration as shown in the integration UI, for example: Microsoft Graph User.

    INTEGRATION_COMMAND_NAME:
        Command names should be written in all lower-case letters,
        and each word separated with a hyphen, for example: msgraph-user.

    INTEGRATION_CONTEXT_NAME:
        Context output names should be written in camel case, for example: MSGraphUser.
"""
INTEGRATION_NAME = 'Data Enrichment & Threat Intelligence'
# lowercase with `-` dividers
INTEGRATION_COMMAND_NAME = 'data-enrichment-threat-and-intelligence'
# No dividers
INTEGRATION_CONTEXT_NAME = 'DataEnrichmentAndThreatIntelligence'
# Setting global params, initiation in main() function
FILE_HASHES: Tuple = ('md5', 'ssdeep', 'sha1', 'sha256')  # hashes as described in API
''' HELPER FUNCTIONS '''


class Client(BaseClient):
    def __init__(self, base_url, threshold: int = 70, *args, **kwarg):
        """Wrapper of CommonServerPython.BaseClient
        Params:
            threshold: arg will be used in calculate_dbot_score. if None, will use default value of 70.
        """
        self._threshold = threshold
        super().__init__(base_url, *args, **kwarg)

    """ HELPER FUNCTIONS """

    def calculate_dbot_score(self, score: int, threshold: Optional[int] = None) -> int:
        """Transforms `severity` from API to DBot Score and using threshold.

        Args:
            score: Severity from API
            threshold: Any value above this number is malicious. if None, will use self._threshold

        Returns:
            Score representation in DBot
        """
        high_score = threshold if threshold else self._threshold
        # Malicious
        if score > high_score:
            return 3
        # Suspicious
        if score > 30:
            return 2
        # Good
        if score >= 0:
            return 1
        # Unknown
        return 0

    def test_module_request(self) -> Dict:
        """Performs basic get request to see if the API is reachable and authentication works.

        Returns:
            Response JSON
        """
        return self._http_request('GET', 'version')

    def get_ip_request(self, ip: str) -> Dict:
        """Gets an analysis from the API for given IP.

        Args:
            ip: IP to get analysis on

        Returns:
            Response JSON

        """
        suffix = 'ip'
        params = {'ip': ip}
        return self._http_request('GET', suffix, params=params)

    def get_url_request(self, url: str) -> Dict:
        """Gets an analysis from the API for given url.

        Args:
            url: URL to get analysis on

        Returns:
            Response JSON
        """
        suffix = 'analysis'
        params = {'url': url}
        return self._http_request('GET', suffix, params=params)

    def search_file_request(self, file_hash: str) -> Dict:
        """Building request for file command

        Args:
            file_hash: Hash to search in API

        Returns:
            Response JSON
        """
        suffix = 'analysis'
        params = {'hash': file_hash}
        return self._http_request('GET', suffix, params=params)

    def get_domain_request(self, domain):
        """Building request for file command

        Args:
            domain: Domain to search in API

        Returns:
            Response JSON
        """
        suffix = 'analysis'
        params = {'domain': domain}
        return self._http_request('GET', suffix, params=params)


def build_context(results: Union[Dict, List], indicator_type: str) -> Union[Dict, List]:
    """Formatting results from API to Demisto Context

    Args:
        results: raw results from raw_response
        indicator_type: type of indicator

    Returns:
        Results formatted to Demisto Context
    """

    def build_entry_context(entry: Dict):
        return {
            'ID': entry.get('id'),
            'Severity': entry.get('severity'),
            indicator_type: entry.get('indicator'),
            'Description': entry.get('description')
        }

    if isinstance(results, list):
        return [build_entry_context(entry) for entry in results]  # pragma: no cover
    return build_entry_context(results)


''' COMMANDS '''


def search_ip(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Gets results for the API.
    """
    ip = args.get('ip', '')
    raw_response = client.get_ip_request(ip)
    results = raw_response.get('result')
    if results:
        result = results[0]
        title = f'{INTEGRATION_NAME} - Analysis results for IP: {ip}'
        context_entry = build_context(result, 'IP')
        # Building a score for DBot
        score = client.calculate_dbot_score(result.get('severity'))
        dbot_entry = build_dbot_entry(ip, 'ip', INTEGRATION_NAME, score, result.get('description'))
        context = {
            f'{INTEGRATION_CONTEXT_NAME}(val.ID && val.ID === obj.ID)': context_entry
        }
        context.update(dbot_entry)
        human_readable: str = tableToMarkdown(title, context_entry, removeNull=True)
        return human_readable, context, raw_response
    else:
        return f'{INTEGRATION_NAME} - No results found for IP: {ip}', {}, raw_response


def search_url(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Gets a job from the API. Used mostly for polling playbook
    """
    url = args.get('url', '')
    raw_response = client.get_url_request(url)
    results = raw_response.get('result')
    if results:
        result = results[0]
        title = f'{INTEGRATION_NAME} - Analysis results for URL: {url}'
        context_entry = build_context(result, 'URL')
        # Building a score for DBot
        score = client.calculate_dbot_score(result.get('severity'))
        dbot_entry = build_dbot_entry(url, 'url', INTEGRATION_NAME, score, result.get('description'))
        context = {
            f'{INTEGRATION_CONTEXT_NAME}(val.ID && val.ID === obj.ID)': context_entry
        }
        context.update(dbot_entry)
        human_readable = tableToMarkdown(title, context_entry, removeNull=True)
        return human_readable, context, raw_response
    else:
        return f'{INTEGRATION_NAME} - No results found for URL: {url}', {}, raw_response


def search_file(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Searching for given file hash
    """
    file_hash = args.get('file', '')
    raw_response = client.search_file_request(file_hash)
    results = raw_response.get('result')
    if results:
        result = results[0]
        title = f'{INTEGRATION_NAME} - Analysis results for file hash: {file_hash}'
        context_entry = {
            'ID': result.get('id'),
            'Severity': result.get('severity'),
            'MD5': result.get('md5'),
            'SHA1': result.get('sha1'),
            'SHA256': result.get('sha256'),
            'SSDeep': result.get('ssdeep'),
            'Description': result.get('description')
        }
        # Gets DBot score
        score = client.calculate_dbot_score(result.get('severity'))
        # Building a score for DBot
        dbot_score = [
            {
                'Indicator': result.get(hash_name),
                'Type': 'hash',
                'Vendor': f'{INTEGRATION_NAME}',
                'Score': score
            } for hash_name in FILE_HASHES if result.get(hash_name)
        ]
        context = {
            outputPaths['dbotscore']: dbot_score,
            f'{INTEGRATION_CONTEXT_NAME}(val.ID && val.ID === obj.ID)': context_entry
        }

        if score == 3:  # If file is malicious, adds a malicious entry
            context[outputPaths['file']] = [{
                hash_name.upper(): raw_response.get(hash_name),
                'Malicious': {
                    'Vendor': f'{INTEGRATION_NAME}',
                    'Description': raw_response.get('description')
                }
            } for hash_name in FILE_HASHES if raw_response.get(hash_name)]
        human_readable = tableToMarkdown(title, context_entry, removeNull=True)
        return human_readable, context, raw_response
    else:
        return f'{INTEGRATION_NAME} - No results found for file hash: [{file_hash}', {}, raw_response


def search_domain(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Gets a job from the API. Used mostly for polling playbook
    """
    url = args.get('domain', '')
    raw_response = client.get_domain_request(url)
    results = raw_response.get('result')
    if results:
        result = results[0]
        title = f'{INTEGRATION_NAME} - Analysis results for domain: {url}'
        context_entry = build_context(result, 'Domain')
        # Building a score for DBot
        score = client.calculate_dbot_score(result.get('severity'))
        dbot_entry = build_dbot_entry(url, 'domain', INTEGRATION_NAME, score, result.get('description'))
        context = {
            f'{INTEGRATION_CONTEXT_NAME}(val.ID && val.ID === obj.ID)': context_entry
        }
        context.update(dbot_entry)
        human_readable = tableToMarkdown(title, context_entry, removeNull=True)
        return human_readable, context, raw_response
    else:
        return f'{INTEGRATION_NAME} - No results found for Domain: {url}', {}, raw_response


def test_module(client: Client, *_) -> Tuple[str, Dict, Dict]:
    raw_response = client.test_module_request()
    if raw_response.get('version'):
        return 'ok', {}, raw_response
    raise DemistoException(f'Test module failed\nraw_response: {raw_response}')


''' COMMANDS MANAGER / SWITCH PANEL '''


def main():  # pragma: no cover
    params = demisto.params()
    base_url = params.get('url', '').rstrip('/') + '/api/v2'
    verify = not params.get('insecure', False)
    proxy: Optional[bool] = params.get('proxy')
    threshold = int(params.get('threshold', 70))
    client = Client(
        base_url,
        verify=verify,
        proxy=proxy,
        threshold=threshold
    )
    command = demisto.command()
    demisto.info(f'Command being called is {command}')
    commands = {
        'test-module': test_module,
        f'{INTEGRATION_COMMAND_NAME}-search-ip': search_ip,
        'ip': search_ip,
        f'{INTEGRATION_COMMAND_NAME}-search-url': search_url,
        'url': search_url,
        f'{INTEGRATION_COMMAND_NAME}-search-file': search_file,
        'file': search_file,
        f'{INTEGRATION_COMMAND_NAME}-search-domain': search_domain,
        'domain': search_domain,
    }
    try:
        if command in commands:
            return_outputs(*commands[command](client, demisto.args()))

    # Log exceptions
    except Exception as e:
        err_msg = f'Error in {INTEGRATION_NAME} Integration [{e}]'
        return_error(err_msg, error=e)


if __name__ == 'builtins':  # pragma: no cover
    main()
