# from .token import Token
# from .user import User
# from .table import Table
# from .project import Project

# # lazy imports
# User = None
# Token = None
# Project = None
# Table = None

# def lazy_load():
#     global User, Token, Project, Table
#     from .user import User
#     from .token import Token
#     from .project import Project
#     from .table import Table

# lazy_load()
# del lazy_load

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .token import Token
    from .project import Project
    from .table import Table
else:
    User = None
    Token = None
    Project = None
    Table = None

def lazy_load():
    global User, Token, Project, Table
    from .user import User
    from .token import Token
    from .project import Project
    from .table import Table

__all__ = ["User", "Token", "Project", "Table", "lazy_load"]
