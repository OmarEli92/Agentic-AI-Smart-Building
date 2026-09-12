from contextlib import ExitStack
from tb_ce_client import ThingsboardClient
from agentic_bim_iot.config.settings import Settings


def create_thingsboard_client(*,settings: Settings,resources: ExitStack) -> ThingsboardClient:
    """ Create the ThingsBoard client."""
    api_key = (settings.thingsboard_api_key.get_secret_value().strip() if settings.thingsboard_api_key else None)
    if api_key:
        return resources.enter_context(ThingsboardClient(settings.thingsboard_url,api_key=api_key))

    username = (settings.thingsboard_username.strip() if settings.thingsboard_username else None)
    password = (settings.thingsboard_password.get_secret_value().strip() if settings.thingsboard_password else None)
    if not username or not password:
        raise RuntimeError("ThingsBoard authentication is not configured.")

    client = ThingsboardClient(settings.thingsboard_url,username=username,password=password)
    token = client.get_token()
    if not token:
        client.close()
        raise RuntimeError("ThingsBoard authentication did not return an access token.")
    configuration = client.api_client.configuration
    configuration.api_key["ApiKeyForm"] = token
    configuration.api_key_prefix["ApiKeyForm"] = "Bearer"
    return resources.enter_context(client)