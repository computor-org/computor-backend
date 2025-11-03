"""API endpoints for bulk course member import."""
import logging
from typing import Annotated, List
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.api.exceptions import BadRequestException
from computor_backend.utils.excel_xml_parser import parse_course_member_xml
from computor_backend.business_logic.course_member_import import import_course_members

from computor_types.course_member_import import (
    CourseMemberImportRequest,
    CourseMemberImportResponse,
    CourseMemberImportRow,
)

logger = logging.getLogger(__name__)

course_member_import_router = APIRouter(
    prefix="/course-member-import",
    tags=["course-member-import"]
)


@course_member_import_router.post(
    "/upload/{course_id}",
    response_model=CourseMemberImportResponse,
)
async def upload_course_member_file(
    course_id: str,
    file: UploadFile = File(..., description="Excel XML file (.xml)"),
    default_role: str = Form("_student", description="Default course role ID"),
    update_existing: bool = Form(False, description="Update existing users"),
    create_missing_groups: bool = Form(True, description="Auto-create missing groups"),
    username_strategy: str = Form("name", description="Username generation strategy: 'name' or 'email'"),
    batch_size: int = Form(5, description="Batch size for GitLab operations"),
    batch_delay_seconds: int = Form(10, description="Delay between batches (seconds)"),
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
) -> CourseMemberImportResponse:
    """Upload and import course members from Excel XML file.

    This endpoint accepts an Excel-compatible XML file (SpreadsheetML format)
    and imports the members into the specified course.

    **Required Permissions**: Lecturer role or higher (_lecturer, _maintainer, _owner)

    Expected columns in the XML file:
    - E-Mail (required): Email address used as unique identifier
    - Vorname (optional): Given name / first name
    - Familienname (optional): Family name / last name
    - Matrikelnummer (optional): Student ID number
    - Gruppe (optional): Course group name

    Args:
        course_id: ID of the course to import members into
        file: Excel XML file upload
        default_role: Default course role (default: "_student")
        update_existing: Whether to update existing users (default: False)
        create_missing_groups: Auto-create missing course groups (default: True)
        permissions: Current user's permissions
        db: Database session

    Returns:
        Import response with detailed results

    Raises:
        BadRequestException: If file format is invalid
        ForbiddenException: If user lacks lecturer role or higher
    """
    # Validate file
    if not file.filename.lower().endswith('.xml'):
        raise BadRequestException(
            "Invalid file format. Only Excel XML (.xml) files are supported."
        )

    # Read file content
    try:
        content = await file.read()
        logger.info(f"Received file {file.filename} ({len(content)} bytes)")
    except Exception as e:
        raise BadRequestException(f"Failed to read file: {e}")

    # Parse XML
    try:
        parsed_rows = parse_course_member_xml(content)
        logger.info(f"Parsed {len(parsed_rows)} rows from XML")
    except Exception as e:
        logger.error(f"Failed to parse XML: {e}", exc_info=True)
        raise BadRequestException(f"Failed to parse XML file: {e}")

    # Convert to import rows
    import_rows = []
    for row in parsed_rows:
        try:
            import_row = CourseMemberImportRow(
                email=row.get('email', ''),
                given_name=row.get('given_name'),
                family_name=row.get('family_name'),
                student_id=row.get('student_id'),
                course_group_title=row.get('course_group_title'),
                course_role_id=default_role,
                incoming=row.get('incoming'),
                study_id=row.get('study_id'),
                study_name=row.get('study_name'),
                semester=int(row['semester']) if row.get('semester') and row['semester'].isdigit() else None,
                registration_date=row.get('registration_date'),
                notes=row.get('notes'),
            )
            import_rows.append(import_row)
        except Exception as e:
            logger.warning(f"Failed to parse row {row}: {e}")
            # Continue with other rows

    if not import_rows:
        raise BadRequestException("No valid rows found in the file")

    logger.info(f"Processing {len(import_rows)} valid rows")

    # Import members
    try:
        result = await import_course_members(
            course_id=course_id,
            members=import_rows,
            default_course_role_id=default_role,
            update_existing=update_existing,
            create_missing_groups=create_missing_groups,
            permissions=permissions,
            db=db,
            username_strategy=username_strategy,
            batch_size=batch_size,
            batch_delay_seconds=batch_delay_seconds,
        )

        # Commit transaction if successful
        db.commit()
        logger.info(
            f"Import completed: {result.success} success, "
            f"{result.errors} errors, {result.updated} updated"
        )

        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}", exc_info=True)
        raise


@course_member_import_router.post(
    "/import/{course_id}",
    response_model=CourseMemberImportResponse,
)
async def import_course_members_json(
    course_id: str,
    request: CourseMemberImportRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
) -> CourseMemberImportResponse:
    """Import course members from JSON payload.

    This endpoint accepts a JSON payload with course member data and imports them
    into the specified course.

    **Required Permissions**: Lecturer role or higher (_lecturer, _maintainer, _owner)

    Args:
        course_id: ID of the course to import members into
        request: Import request with member data
        permissions: Current user's permissions
        db: Database session

    Returns:
        Import response with detailed results

    Raises:
        ForbiddenException: If user lacks lecturer role or higher
    """
    logger.info(f"Importing {len(request.members)} members to course {course_id}")

    try:
        result = await import_course_members(
            course_id=course_id,
            members=request.members,
            default_course_role_id=request.default_course_role_id,
            update_existing=request.update_existing,
            create_missing_groups=request.create_missing_groups,
            permissions=permissions,
            db=db,
            username_strategy=request.username_strategy,
            batch_size=request.batch_size,
            batch_delay_seconds=request.batch_delay_seconds,
        )

        # Commit transaction if successful
        db.commit()
        logger.info(
            f"Import completed: {result.success} success, "
            f"{result.errors} errors, {result.updated} updated"
        )

        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}", exc_info=True)
        raise
