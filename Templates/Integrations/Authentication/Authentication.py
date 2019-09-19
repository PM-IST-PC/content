import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

''' IMPORTS '''
from typing import Dict, Tuple, List, AnyStr, Union
import urllib3

# Disable insecure warnings
urllib3.disable_warnings()

''' GLOBALS/PARAMS '''


class Client(BaseClient):
    def test_module_request(self) -> Dict:
        """Performs basic GET request to check if the API is reachable and authentication is successful.

        Returns:
            Response JSON
        """
        return self._http_request('GET', 'version')

    def list_credentials_request(self) -> Dict:
        """Uses to fetch incidents into Demisto
        Documentation:https://github.com/demisto/content/tree/master/docs/fetching_incidents
        Returns:
            Response JSON
        """
        suffix = 'credential'
        return self._http_request('GET', suffix)

    def list_accounts_request(self) -> Dict:
        """Uses to fetch incidents into Demisto
        Documentation:https://github.com/demisto/content/tree/master/docs/fetching_incidents
        Returns:
            Response JSON
        """
        suffix = 'account'
        return self._http_request('GET', suffix)

    def lock_account_request(self, account_id: AnyStr) -> Dict:
        """Locks an account by the account ID.

        Args:
            account_id: Account ID to lock.

        Returns:
            Response JSON
        """
        # The service endpoint to request from
        suffix = 'account/lock'
        # Dictionary of params for the request
        params = {'account': account_id}
        return self._http_request('POST', suffix, params=params)

    def unlock_account_request(self, account_id: AnyStr) -> Dict:
        """Returns events by the account ID.

        Args:
            account_id: Account ID to unlock.

        Returns:
            Response JSON
        """
        # The service endpoint to request from
        suffix = 'account/unlock'
        # Dictionary of params for the request
        params = {'account': account_id}
        # Send a request using our http_request wrapper
        return self._http_request('POST', suffix, params=params)

    def reset_account_request(self, account_id: str):
        """Resets an account by account ID.

        Args:
            account_id: Account ID to reset.

        Returns:
            Response JSON
        """
        # The service endpoint to request from
        suffix = 'account/reset'
        # Dictionary of params for the request
        params = {'account': account_id}
        # Send a request using our http_request wrapper
        return self._http_request('POST', suffix, params=params)

    def unlock_vault_request(self, vault_to_lock: AnyStr) -> Dict:
        """Unlocks a vault by vault ID.

        Args:
            vault_to_lock: Vault ID to lock

        Returns:
            Response JSON
        """
        suffix = 'vault/unlock'
        params = {'vaultId': vault_to_lock}
        return self._http_request('POST', suffix, params=params)

    def lock_vault_request(self, vault_to_lock: AnyStr) -> Dict:
        """Locks vault by vault ID.

        Args:
            vault_to_lock: Vault ID to lock.

        Returns:
            Response JSON
        """
        suffix = 'vault/lock'
        params = {'vaultId': vault_to_lock}
        return self._http_request('POST', suffix, params=params)

    def list_vaults_request(self, max_results: int) -> Dict:
        """Return all vaults from API.

        Args:
            max_results: Vault ID to lock.

        Returns:
            Response JSON
        """
        suffix = 'vault'
        values_to_ignore = [0]
        params = assign_params(limit=max_results, values_to_ignore=values_to_ignore)
        return self._http_request('GET', suffix, params=params)


''' HELPER FUNCTIONS '''


def build_account_context(credentials: Union[Dict, List]) -> Union[Dict, List]:
    """Formats the API response to Demisto context.

    Args:
        credentials: The raw response from the API call. Can be a List or Dict.

    Returns:
        The formatted Dict or List.

    Examples:
        >>> build_account_context([{'username': 'user', 'name': 'demisto', 'isLocked': False}])
        [{'User': 'user', 'Name': 'demisto', 'IsLocked': False}]
    """

    def build_dict(credential: Dict) -> Dict:
        """Builds a Dict formatted for Demisto.

        Args:
            credential: A single event from the API call.

        Returns:
            A Dict formatted for Demisto context.
        """
        return assign_params(
            Username=credential.get('username'),
            Name=credential.get('name'),
            IsLocked=credential.get('isLocked')
        )

    if isinstance(credentials, list):
        return [build_dict(credential) for credential in credentials]
    return build_dict(credentials)


def build_credentials_fetch(credentials: Union[Dict, List]) -> Union[Dict, List]:
    """Formats the API response to Demisto context.

    Args:
        credentials: The raw response from the API call. Can be a List or Dict.

    Returns:
        The formatted Dict or List.

    Examples:
        >>> build_credentials_fetch([{'username': 'user1', 'name': 'name1', 'password': 'password'}])
        [{'user': 'user1', 'name': 'name1', 'password': 'password'}]
    """

    def build_dict(credential: Dict) -> Dict:
        """Builds a Dict formatted for Demisto.

        Args:
            credential: A single event from the API call.

        Returns:
            A Dict formatted for Demisto context.
        """
        return {
            'user': credential.get('username'),
            'name': credential.get('name'),
            'password': credential.get('password'),
        }

    if isinstance(credentials, list):
        return [build_dict(credential) for credential in credentials]
    return build_dict(credentials)  # pragma: no cover


def build_vaults_context(vaults: Union[List, Dict]) -> Union[List[Dict], Dict]:
    def vault_builder(vault_entry: Dict):
        return {
            'ID': vault_entry.get('vaultId'),
            'IsLocked': vault_entry.get('isLocked')
        }

    if isinstance(vaults, list):
        return [vault_builder(vault) for vault in vaults]
    if isinstance(vaults, dict):
        return vault_builder(vaults)


''' COMMANDS '''


def test_module(client: Client, *_) -> Tuple[str, Dict, Dict]:
    """Performs a basic GET request to check if the API is reachable and authentication is successful.
    """
    results = client.test_module_request()
    if 'version' in results:
        return 'ok', {}, {}
    raise DemistoException('Test module failed, {}'.format(results))


def fetch_credentials(client: Client):
    """Uses to fetch credentials into Demisto
    Documentation: https://github.com/demisto/content/tree/master/docs/fetching_credentials
    """
    # Get credentials from api
    raw_response = client.list_credentials_request()
    if 'credential' in raw_response:
        raw_credentials = raw_response.get('credential', [])
        # Creates credentials entry
        credentials = build_credentials_fetch(raw_credentials)
        demisto.credentials(credentials)
    else:
        raise DemistoException(f'`fetch-incidents` failed in `{client.integration_name}`, no keyword `credentials` in'
                               f' response. Check API')


def lock_account(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Locks an account by account ID.
    """
    # Get arguments from user
    username = args.get('username', '')
    # Make request and get raw response
    raw_response = client.lock_account_request(username)
    # Get account from raw_response
    user_object = raw_response.get('account', [{}])[0]
    # Parse response into context & content entries
    if user_object.get('username') == username and user_object.get('isLocked') is True:
        title: str = f'{client.integration_name} - Account `{username}` has been locked.'
        context_entry = {
            'IsLocked': True,
            'Username': username
        }
        context = {f'{client.integration_context_name}.Account(val.ID && val.ID === obj.ID)': context_entry}
        # Creating human readable for War room
        human_readable: str = tableToMarkdown(title, context_entry)
        # Return data to Demisto
        return human_readable, context, raw_response
    else:
        raise DemistoException(f'{client.integration_name} - Could not lock account `{username}`')


def unlock_account(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Unlocks an account by account ID.
    """
    # Get arguments from user
    username = args.get('username', '')
    # Make request and get raw response
    raw_response = client.unlock_account_request(username)
    # Get account from raw_response
    user_object = raw_response.get('account', [{}])[0]
    # Parse response into context & content entries
    if user_object.get('username') == username and user_object.get('isLocked') is False:
        title = f'{client.integration_name} - Account `{username}` has been unlocked.'
        context_entry = {
            'IsLocked': False,
            'Username': username
        }
        context = {f'{client.integration_context_name}.Account(val.ID && val.ID === obj.ID)': context_entry}
        # Creating human readable for War room
        human_readable = tableToMarkdown(title, context_entry)
        # Return data
        return human_readable, context, raw_response
    else:
        raise DemistoException(f'{client.integration_name} - Could not unlock account `{username}`')


def reset_account(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Resets an account by account ID
    """
    # Get arguments from user
    username = args.get('username', '')
    # Make request and get raw response
    raw_response = client.reset_account_request(username)
    # Get account from raw_response
    user_object = raw_response.get('account', [{}])[0]
    # Parse response into context & content entries
    if user_object.get('username') == username and user_object.get('isLocked') is False:
        title = f'{client.integration_name} - Account `{username}` has been returned to default.'
        context_entry = {
            'IsLocked': False,
            'ID': username
        }
        context = {f'{client.integration_context_name}.Account(val.ID && val.ID === obj.ID)': context_entry}
        # Creating human readable for War room
        human_readable = tableToMarkdown(title, context_entry)
        # Return data to Demisto
        return human_readable, context, raw_response
    else:
        raise DemistoException(f'{client.integration_name} - Could not reset account `{username}`')


def list_accounts(client: Client, *_) -> Tuple[str, Dict, Dict]:
    """Returns credentials to user without passwords.
    """
    raw_response = client.list_accounts_request()
    # Filtering out passwords for list_credentials, so it won't get back to the user
    raw_response['account'] = [
        assign_params(keys_to_ignore=['password'], **account) for account in raw_response.get('account', [])
    ]
    accounts = raw_response['account']
    if accounts:
        title = f'{client.integration_name} - Account list.'
        context_entry = build_account_context(accounts)
        context = {f'{client.integration_context_name}.Account(val.ID && val.ID ==== obj.ID)': context_entry}
        human_readable = tableToMarkdown(title, context_entry)
        return human_readable, context, raw_response
    else:
        return f'{client.integration_name} - Could not find any users.', {}, {}


def lock_vault(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Locks a vault by vault ID.
    """
    vault_to_lock = args.get('vault_id', '')
    raw_response = client.lock_vault_request(vault_to_lock)
    vault_object = raw_response.get('vault', [{}])[0]
    if vault_object.get('vaultId') and vault_object.get('isLocked') is True:
        title = f'{client.integration_name} - Vault {vault_to_lock} has been locked'
        context_entry = {
            'ID': vault_to_lock,
            'IsLocked': True
        }
        context = {f'{client.integration_context_name}.Vault(val.ID && val.ID === obj.ID)': context_entry}
        human_readable = tableToMarkdown(title, context_entry)
        return human_readable, context, raw_response
    else:
        raise DemistoException(f'{client.integration_name} - Could not lock vault ID: {vault_to_lock}')


def unlock_vault(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Unlocks a vault by vault ID.
    """
    vault_to_lock = args.get('vault_id', '')
    raw_response = client.unlock_vault_request(vault_to_lock)
    vault_object = raw_response.get('vault', [{}])[0]
    if vault_object.get('vaultId') and vault_object.get('isLocked') is False:
        title = f'{client.integration_name} - Vault {vault_to_lock} has been unlocked'
        context_entry = build_vaults_context(vault_object)
        context = {f'{client.integration_context_name}.Vault(val.ID && val.ID === obj.ID)': context_entry}
        human_readable = tableToMarkdown(title, context_entry)
        return human_readable, context, raw_response
    else:
        raise DemistoException(f'{client.integration_name} - Could not unlock vault ID: {vault_to_lock}')


def list_vaults(client: Client, args: Dict) -> Tuple[str, Dict, Dict]:
    """Lists all vaults.
    """
    max_results = int(args.get('max_results', 0))
    raw_response = client.list_vaults_request(max_results)
    vaults = raw_response.get('vault')
    if vaults:
        title = f'{client.integration_name} - Total of {len(vaults)} has been found.'
        context_entry = build_vaults_context(vaults)
        context = {f'{client.integration_context_name}.Vault(val.ID && val.ID === obj.ID)': context_entry}
        human_readable = tableToMarkdown(title, context_entry)
        return human_readable, context, raw_response
    else:
        return f'{client.integration_name} - No vaults found.', {}, {}


''' COMMANDS MANAGER / SWITCH PANEL '''


def main():  # pragma: no cover
    integration_name = 'Authentication Integration'
    # lowercase with `-` dividers
    integration_command_name = 'authentication'
    # No dividers
    integration_context_name = 'AuthenticationIntegration'
    params = demisto.params()
    server = params.get('url')
    base_suffix = '/api/v1'
    verify = not params.get('insecure', False)
    proxy = params.get('proxy') == 'true'
    client = Client(integration_name, integration_command_name, integration_context_name, server,
                    base_suffix, verify=verify, proxy=proxy)
    command = demisto.command()
    demisto.info(f'Command being called is {command}')

    # Switch case
    commands = {
        'test-module': test_module,
        'fetch-credentials': fetch_credentials,
        f'{integration_command_name}-list-accounts': list_accounts,
        f'{integration_command_name}-lock-account': lock_account,
        f'{integration_command_name}-unlock-account': unlock_account,
        f'{integration_command_name}-reset-account': reset_account,
        f'{integration_command_name}-lock-vault': lock_vault,
        f'{integration_command_name}-unlock-vault': unlock_vault,
        f'{integration_command_name}-list-vaults': list_vaults
    }
    try:
        if command == 'fetch-credentials':
            # Fetch credentials is handled, no return statement.
            commands[command](client)
        if command in commands:
            return_outputs(*commands[command](client, demisto.args()))
    # Log exceptions
    except Exception as e:
        err_msg = f'Error in {integration_name} - [{e}]'
        return_error(err_msg, error=e)


if __name__ == '__builtin__':
    main()
