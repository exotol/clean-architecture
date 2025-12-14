from dynaconf import Dynaconf

from app.core.constants import PATH_TO_ENVS, PATH_TO_SECRETS, PATH_TO_SETTINGS


def load_settings() -> Dynaconf:
    return Dynaconf(
        envvar_prefix=False,
        settings_file=[PATH_TO_SETTINGS, PATH_TO_SECRETS, PATH_TO_ENVS],
        environments=True,
        load_dotenv=False,
        merge_enabled=True,
    )
