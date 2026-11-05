from alembic import op
from app.models import ProjectValueHistory

revision = "0002_project_value_history"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ProjectValueHistory.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    ProjectValueHistory.__table__.drop(bind=op.get_bind(), checkfirst=True)