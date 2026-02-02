"""Add user_profiles and staff_roles; move profile columns from users

Revision ID: 002_user_profiles_staff
Revises: 001_audit_detail
Create Date: user_profiles (1:1), staff_roles (one table for non-employee roles), migrate profile data, drop profile columns from users

"""
from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore
from sqlalchemy import text  # type: ignore


# revision identifiers, used by Alembic.
revision = "002_user_profiles_staff"
down_revision = "001_audit_detail"
branch_labels = None
depends_on = None


def _table_exists(connection, table_name: str) -> bool:
    result = connection.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :t"
        ),
        {"t": table_name},
    )
    return result.scalar() is not None


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    result = connection.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Create user_profiles table only if it does not exist (idempotent)
    if not _table_exists(connection, "user_profiles"):
        op.create_table(
            "user_profiles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="1:1 with users"),
            sa.Column("profile_picture_url", sa.String(500), nullable=True),
            sa.Column("dob", sa.Date(), nullable=True),
            sa.Column("blood_group", sa.String(10), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("permanent_address", sa.Text(), nullable=True),
            sa.Column("father_name", sa.String(255), nullable=True),
            sa.Column("father_dob", sa.Date(), nullable=True),
            sa.Column("mother_name", sa.String(255), nullable=True),
            sa.Column("mother_dob", sa.Date(), nullable=True),
            sa.Column("spouse_name", sa.String(255), nullable=True),
            sa.Column("spouse_dob", sa.Date(), nullable=True),
            sa.Column("children_names", sa.Text(), nullable=True),
            sa.Column("emergency_contact_name", sa.String(255), nullable=True),
            sa.Column("emergency_contact_phone", sa.String(20), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        )
        op.create_index("idx_user_profile_user_id", "user_profiles", ["user_id"], unique=False)

        # 2. Copy profile data from users to user_profiles (only if users still has the columns)
        if _column_exists(connection, "users", "dob"):
            op.execute("""
                INSERT INTO user_profiles (user_id, profile_picture_url, dob, blood_group, address, permanent_address,
                    father_name, father_dob, mother_name, mother_dob, spouse_name, spouse_dob, children_names,
                    emergency_contact_name, emergency_contact_phone, created_at, updated_at)
                SELECT id, profile_picture_url, dob, blood_group, address, permanent_address,
                    father_name, father_dob, mother_name, mother_dob, spouse_name, spouse_dob, children_names,
                    emergency_contact_name, emergency_contact_phone, created_at, updated_at
                FROM users
            """)

        # 3. Drop profile columns from users (only if they exist)
        for col in (
            "profile_picture_url", "dob", "blood_group", "address", "permanent_address",
            "father_name", "father_dob", "mother_name", "mother_dob", "spouse_name", "spouse_dob",
            "children_names", "emergency_contact_name", "emergency_contact_phone",
        ):
            if _column_exists(connection, "users", col):
                op.drop_column("users", col)

    # 4. Create staff_roles table only if it does not exist (idempotent)
    if not _table_exists(connection, "staff_roles"):
        op.create_table(
            "staff_roles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="User who has this staff role"),
            sa.Column("role_type", sa.String(50), nullable=False, comment="founder, co_founder, hr, manager"),
            sa.Column("department", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.UniqueConstraint("user_id", "role_type", name="uq_staff_role_user_role"),
        )
        op.create_index("idx_staff_role_user_id", "staff_roles", ["user_id"], unique=False)
        op.create_index("idx_staff_role_role_type", "staff_roles", ["role_type"], unique=False)
        op.create_index("idx_staff_role_is_active", "staff_roles", ["is_active"], unique=False)


def downgrade() -> None:
    # Drop staff_roles table
    op.drop_index("idx_staff_role_is_active", table_name="staff_roles")
    op.drop_index("idx_staff_role_role_type", table_name="staff_roles")
    op.drop_index("idx_staff_role_user_id", table_name="staff_roles")
    op.drop_table("staff_roles")

    # Add profile columns back to users
    op.add_column("users", sa.Column("profile_picture_url", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("blood_group", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("permanent_address", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("father_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("father_dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("mother_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("mother_dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("spouse_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("spouse_dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("children_names", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("emergency_contact_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("emergency_contact_phone", sa.String(20), nullable=True))

    # Copy data back from user_profiles to users
    op.execute("""
        UPDATE users u
        INNER JOIN user_profiles p ON u.id = p.user_id
        SET u.profile_picture_url = p.profile_picture_url,
            u.dob = p.dob,
            u.blood_group = p.blood_group,
            u.address = p.address,
            u.permanent_address = p.permanent_address,
            u.father_name = p.father_name,
            u.father_dob = p.father_dob,
            u.mother_name = p.mother_name,
            u.mother_dob = p.mother_dob,
            u.spouse_name = p.spouse_name,
            u.spouse_dob = p.spouse_dob,
            u.children_names = p.children_names,
            u.emergency_contact_name = p.emergency_contact_name,
            u.emergency_contact_phone = p.emergency_contact_phone
    """)

    # Drop user_profiles table
    op.drop_index("idx_user_profile_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
