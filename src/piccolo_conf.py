from piccolo.conf.apps import AppRegistry

from db.engine import DB


APP_REGISTRY = AppRegistry(
    apps=[
        "db.piccolo_app",
    ],
)
