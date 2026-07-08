"""Deploy course content types and (recursively) course contents."""

import click

from computor_cli.auth import get_computor_client
from computor_client import SyncComputorClient
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async

from computor_types.deployment_config import HierarchicalCourseConfig
from computor_types.course_contents import CourseContentQuery
from computor_types.course_content_types import (
    CourseContentTypeQuery,
    CourseContentTypeCreate,
)
from computor_types.course_content_kind import CourseContentKindQuery
from computor_types.example import ExampleQuery


def _deploy_course_content_types(course_id: str, content_types_config: list, auth: CLIAuthConfig):
    """Deploy course content types for a course via API."""
    if not content_types_config:
        return

    client = run_async(get_computor_client(auth))
    content_type_client = client.course_content_types

    created_count = 0
    existing_count = 0

    for content_type_config in content_types_config:
        try:
            # Check if content type already exists
            existing_types = run_async(content_type_client.list(CourseContentTypeQuery(
                course_id=course_id,
                slug=content_type_config.slug
            )))

            if existing_types:
                click.echo(f"    ℹ️  Content type already exists: {content_type_config.slug}")
                existing_count += 1
                continue

            # Create new content type
            content_type_create = CourseContentTypeCreate(
                slug=content_type_config.slug,
                title=content_type_config.title,
                description=content_type_config.description,
                color=content_type_config.color or "green",
                properties=content_type_config.properties or {},
                course_id=course_id,
                course_content_kind_id=content_type_config.kind
            )

            run_async(content_type_client.create(content_type_create))
            click.echo(f"    ✅ Created content type: {content_type_config.slug}")
            created_count += 1

        except Exception as e:
            click.echo(f"    ❌ Failed to create content type {content_type_config.slug}: {e}")

    if created_count > 0 or existing_count > 0:
        click.echo(f"    📊 Content types: {created_count} created, {existing_count} existing")


def _deploy_course_contents(course_id: str, course_config: HierarchicalCourseConfig, auth: CLIAuthConfig, parent_path: str = None, position_counter: list = None, deployed_services: dict = None):
    """Deploy course contents for a course."""


    client = run_async(get_computor_client(auth))

    if not course_config.contents:
        return
    
    # Initialize position counter if not provided
    if position_counter is None:
        position_counter = [1.0]
    
    # Get API clients
    content_client = client.course_contents
    content_type_client = client.course_content_types
    content_kind_client = client.course_content_kinds
    example_client = client.examples
    # backend_client = client.execution_backends  # REMOVED: execution_backends deprecated
    custom_client = SyncComputorClient.from_client(client)
    
    for content_config in course_config.contents:
        try:
            # We may generate the full path later if not provided
            full_path = None
            
            # Find the content type
            content_types = run_async(content_type_client.list(CourseContentTypeQuery(
                course_id=course_id,
                slug=content_config.content_type
            )))
            
            if not content_types:
                click.echo(f"    ⚠️  Content type not found: {content_config.content_type}")
                continue
            
            content_type = content_types[0]
            
            # Determine if submittable by content kind (needed to fetch example metadata)
            is_submittable = False
            if content_type.course_content_kind_id:
                content_kinds = run_async(content_kind_client.list(CourseContentKindQuery(
                    id=content_type.course_content_kind_id
                )))
                if content_kinds and len(content_kinds) > 0:
                    is_submittable = content_kinds[0].submittable
            
            # Prefetch example/version to derive defaults when missing
            example = None
            version = None
            meta_title = None
            meta_description = None
            ex_title = None
            if is_submittable and content_config.example_identifier:
                try:
                    examples = run_async(example_client.list(ExampleQuery(
                        identifier=content_config.example_identifier
                    )))
                    if examples:
                        example = examples[0]
                        ex_title = getattr(example, 'title', None)
                        version_tag = content_config.example_version_tag or "latest"
                        try:
                            # Backend now handles normalization and "latest" tag
                            all_versions = custom_client.list(
                                f"examples/{example.id}/versions",
                                params={"version_tag": version_tag}
                            ) or []
                        except Exception:
                            all_versions = []
                        if version_tag == "latest" and all_versions:
                            version = all_versions[0]
                        else:
                            for v in all_versions:
                                if v.get('version_tag') == version_tag:
                                    version = v
                                    break
                        # Fetch full version details if the list view didn't carry
                        # title/description (the GET version response always does).
                        if version and version.get('title') is None and version.get('description') is None:
                            try:
                                version = custom_client.get(f"examples/versions/{version['id']}") or version
                            except Exception:
                                pass
                        if version:
                            meta_title = version.get('title')
                            meta_description = version.get('description')
                except Exception:
                    pass

            # Decide path: prefer provided path, otherwise generate from title/meta/example id and ensure uniqueness
            if content_config.path:
                full_path = f"{parent_path}.{content_config.path}" if parent_path else content_config.path
            else:
                # Determine effective title now (may still be None)
                identifier_last = None
                if content_config.example_identifier:
                    try:
                        identifier_last = content_config.example_identifier.split('.')[-1]
                    except Exception:
                        identifier_last = content_config.example_identifier
                eff_title_src = content_config.title or meta_title or ex_title or identifier_last or 'content'
                import re
                seg = re.sub(r"[^a-z0-9_]+", "", re.sub(r"[\s-]+", "_", (eff_title_src or 'content').lower().strip())) or 'content'
                candidate = f"{parent_path}.{seg}" if parent_path else seg
                idx = 1
                while True:
                    existing = run_async(content_client.list(CourseContentQuery(course_id=course_id, path=candidate)))
                    if not existing:
                        full_path = candidate
                        break
                    idx += 1
                    seg_try = f"{seg}_{idx}"
                    candidate = f"{parent_path}.{seg_try}" if parent_path else seg_try

            # Helper to humanize a slug/segment to a friendly title
            def _humanize(seg: str) -> str:
                try:
                    return ' '.join([w.capitalize() for w in seg.replace('_', ' ').replace('-', ' ').split() if w]) or seg
                except Exception:
                    return seg

            # Check if content already exists
            # Use custom_client to bypass Pydantic validation issues
            existing_contents = custom_client.list("course-contents", params={
                "course_id": course_id,
                "path": full_path
            })

            if existing_contents:
                # Convert to object for easier access
                from types import SimpleNamespace
                content = SimpleNamespace(**existing_contents[0])
                click.echo(f"    ℹ️  Content already exists: {content.title} ({full_path})")

                # Patch testing_service_id if missing and a service is available
                if not getattr(content, 'testing_service_id', None) and deployed_services and is_submittable:
                    # Find the first deployed service for this course
                    for svc_ref in (getattr(course_config, 'services', None) or []):
                        slug = svc_ref.slug if hasattr(svc_ref, 'slug') else svc_ref
                        if slug in deployed_services:
                            svc_id = deployed_services[slug]["id"]
                            try:
                                custom_client.update(f"course-contents/{content.id}", {"testing_service_id": svc_id})
                                click.echo(f"      🔗 Linked testing service: {slug}")
                            except Exception as e:
                                click.echo(f"      ⚠️  Failed to link testing service: {e}")
                            break

                to_update = {}
                if content_config.description is not None:
                    if content_config.description != getattr(content, 'description', None):
                        to_update['description'] = content_config.description
                elif is_submittable and not getattr(content, 'description', None) and meta_description:
                    to_update['description'] = meta_description
                # Opportunistically improve title if it's empty or looks like a slug and we have a better source
                current_title = getattr(content, 'title', None)
                fallback_seg = full_path.split('.')[-1]
                friendly_fallback = _humanize(fallback_seg)
                better_title = content_config.title or meta_title or ex_title or friendly_fallback
                if (current_title is None) or (current_title == fallback_seg) or (current_title == friendly_fallback and better_title not in [None, friendly_fallback]):
                    if better_title and better_title != current_title:
                        to_update['title'] = better_title

                if to_update:
                    try:
                        # Use custom_client to bypass Pydantic validation issues
                        custom_client.update(f"course-contents/{content.id}", to_update)
                        update_msg = ", ".join(to_update.keys())
                        click.echo(f"      ✏️  Updated content: {update_msg}")
                    except Exception as e:
                        click.echo(f"      ⚠️  Failed to update content: {e}")
            else:
                # Determine position
                position = content_config.position if content_config.position is not None else position_counter[0]
                position_counter[0] += 1.0

                # Derive title/description defaults: description only from meta_yaml when not given
                fallback_seg = None
                try:
                    fallback_seg = full_path.split('.')[-1]
                except Exception:
                    fallback_seg = full_path
                effective_title = content_config.title or meta_title or ex_title or _humanize(fallback_seg)
                effective_description = content_config.description if content_config.description is not None else meta_description

                # Resolve testing_service_id from deployed services
                resolved_testing_service_id = None
                if is_submittable and deployed_services:
                    for svc_ref in (getattr(course_config, 'services', None) or []):
                        slug = svc_ref.slug if hasattr(svc_ref, 'slug') else svc_ref
                        if slug in deployed_services:
                            resolved_testing_service_id = deployed_services[slug]["id"]
                            break

                # Create the content
                content_create_data = {
                    "title": effective_title,
                    "description": effective_description,
                    "path": full_path,
                    "course_id": course_id,
                    "course_content_type_id": str(content_type.id),
                    "position": position,
                    "max_group_size": content_config.max_group_size or 1,
                    "max_test_runs": content_config.max_test_runs,
                    "max_submissions": content_config.max_submissions,
                    "testing_service_id": resolved_testing_service_id,
                    "properties": content_config.properties.model_dump() if content_config.properties else None
                }

                # Use custom_client to bypass Pydantic validation issues with deployment field
                content = custom_client.create("course-contents", content_create_data)
                # Convert to object for easier access
                from types import SimpleNamespace
                content = SimpleNamespace(**content)
                click.echo(f"    ✅ Created content: {effective_title} ({full_path})")
            
            # Handle example deployment for submittable content
            # Version semantics from deployment YAML:
            #   example_version_tag: null/missing  → first-time assign only, skip if already deployed
            #   example_version_tag: "latest"      → always update to the latest available version
            #   example_version_tag: "1.2.0"       → update only if current version differs
            if is_submittable and content_config.example_identifier:
                # Check existing deployment state
                try:
                    deployment_info = custom_client.get(f"course-contents/deployment/{content.id}")
                    has_deployment = deployment_info and deployment_info.get('deployment_status') not in [None, 'unassigned']
                except Exception:
                    deployment_info = None
                    has_deployment = False

                current_version = deployment_info.get('version_tag') if deployment_info else None
                requested_version = content_config.example_version_tag  # None, "latest", or "1.2.0"

                # Determine whether to assign/update
                if has_deployment and not requested_version:
                    # No version specified → skip existing deployment
                    click.echo(f"      ℹ️  Deployment already exists for example: {content_config.example_identifier} ({current_version})")
                elif has_deployment and requested_version != "latest" and current_version == requested_version:
                    # Pinned version matches current → skip
                    click.echo(f"      ℹ️  Deployment already at requested version: {content_config.example_identifier} ({current_version})")
                else:
                    # Need to assign or update — resolve example and version
                    resolve_version_tag = requested_version or "latest"

                    # Resolve example if not prefetched
                    if not example:
                        examples = run_async(example_client.list(ExampleQuery(
                            identifier=content_config.example_identifier
                        )))
                        if examples:
                            example = examples[0]
                        else:
                            # Example not in DB — try direct identifier-based assignment
                            if requested_version and requested_version != "latest":
                                try:
                                    assign_payload = {
                                        "example_identifier": content_config.example_identifier,
                                        "version_tag": requested_version
                                    }
                                    custom_client.create(f"lecturers/course-contents/{content.id}/assign-example", assign_payload)
                                    click.echo(f"      ✅ Assigned example: {content_config.example_identifier} ({requested_version})")
                                except Exception as e:
                                    click.echo(f"      ⚠️  Failed to assign example: {e}")
                            else:
                                click.echo(f"      ⚠️  Example not found in DB: {content_config.example_identifier}")
                            example = None  # Ensure we skip the block below

                    if example:
                        # Resolve the example ID (could be Pydantic object or dict)
                        ex_id = example.id if hasattr(example, 'id') else example['id']

                        # Resolve version
                        if not version or requested_version:
                            try:
                                all_versions = custom_client.list(
                                    f"examples/{ex_id}/versions",
                                    params={"version_tag": resolve_version_tag}
                                ) or []
                            except Exception:
                                all_versions = []

                            version = None
                            if resolve_version_tag == "latest" and all_versions:
                                version = all_versions[0]
                            else:
                                for v in all_versions:
                                    if v.get('version_tag') == resolve_version_tag:
                                        version = v
                                        break

                        if version:
                            desired_version = version.get('version_tag') if isinstance(version, dict) else getattr(version, 'version_tag', resolve_version_tag)

                            if has_deployment and current_version == desired_version:
                                click.echo(f"      ℹ️  Deployment already at latest version: {content_config.example_identifier} ({current_version})")
                            else:
                                try:
                                    assign_payload = {
                                        "example_id": str(ex_id),
                                        "version_tag": desired_version
                                    }
                                    custom_client.create(f"lecturers/course-contents/{content.id}/assign-example", assign_payload)
                                    if has_deployment:
                                        click.echo(f"      ✅ Updated example: {content_config.example_identifier} ({current_version} → {desired_version})")
                                    else:
                                        click.echo(f"      ✅ Assigned example: {content_config.example_identifier} ({desired_version})")
                                except Exception as e:
                                    click.echo(f"      ⚠️  Failed to assign example: {e}")
                        else:
                            click.echo(f"      ⚠️  Example version not found: {content_config.example_identifier} ({resolve_version_tag})")
            
            # Recursively deploy nested contents
            if content_config.contents:
                # Create a temporary course config with just the nested contents
                nested_config = type('obj', (object,), {'contents': content_config.contents, 'services': getattr(course_config, 'services', None)})()
                _deploy_course_contents(course_id, nested_config, auth, full_path, position_counter, deployed_services)
                
        except Exception as e:
            click.echo(f"    ❌ Failed to create content {content_config.title}: {e}")
