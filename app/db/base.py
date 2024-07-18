# Import all the models, so that Base has them before being
# imported by Alembic
from .base_class import Base  # noqa
from models.user import User  # noqa
from models.token import Token  # noqa
from models.table import Table  # noqa
from models.project import Project  # noqa