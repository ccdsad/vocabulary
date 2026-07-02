from piccolo.conf.apps import AppRegistry

from db.engine import DB  # noqa: F401

APP_REGISTRY = AppRegistry(
    apps=[
        'db.piccolo_app',
    ],
)
