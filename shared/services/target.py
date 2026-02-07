import csv
import io
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Organization,
    OrganizationSummary,
    Project,
    Tag,
    TagSummary,
    Target,
    TargetBulkCreate,
    TargetBulkCreateResponse,
    TargetCreate,
    TargetImportItem,
    TargetImportRequest,
    TargetImportResult,
    TargetRead,
    TargetType,
    TargetUpdate,
)
from shared.services import get_or_create_organization, get_or_create_tag
from shared.utils.datetime import utc_now
from shared.utils.validation import validate_target

MAX_TARGETS_IMPORT = 500


@dataclass
class BulkTargetResult:
    """Result of processing a single target in bulk operations."""

    import_result: TargetImportResult
    target: Target | None = None


class TargetService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_target_value(self, target_value: str) -> TargetType | None:
        return validate_target(target_value)

    async def get_target_counts(self, project_slug: str) -> dict[str, int]:
        project = await self._get_project_by_slug(project_slug)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await self.session.execute(
            select(Target.target_type, func.count(Target.id))
            .where(Target.project_id == project.id)
            .group_by(Target.target_type)
        )

        counts = {
            "all": 0,
            "domain": 0,
            "ip": 0,
            "ip_range": 0,
            "asn": 0,
            "url": 0,
        }

        for target_type, count in result.all():
            counts[target_type.value] = count
            counts["all"] += count

        return counts

    async def search_targets_by_value(
        self,
        target_value: str,
        project_slug: str | None = None,
    ) -> select:
        """
        Search for targets by their target_value.
        Returns query that can be paginated.
        """
        query = select(Target).where(Target.target_value == target_value)

        if project_slug:
            project = await self._get_project_by_slug(project_slug)
            if project:
                query = query.where(Target.project_id == project.id)
            else:
                query = query.where(Target.id is None)

        return query

    async def get_targets_by_value(self, target_value: str) -> list[Target]:
        """
        Get all targets matching a specific target_value across all projects.
        Returns actual Target objects
        """
        result = await self.session.execute(
            select(Target).where(Target.target_value == target_value)
        )
        return list(result.scalars().all())

    async def list_targets(
        self,
        project_slug: str | None = None,
        organization_slug: str | None = None,
        target_type: TargetType | None = None,
    ) -> select:
        query = select(Target)

        if project_slug:
            project = await self._get_project_by_slug(project_slug)
            if project:
                query = query.where(Target.project_id == project.id)
            else:
                query = query.where(Target.id is None)

        if organization_slug:
            org = await self._get_organization_by_slug(organization_slug)
            if org:
                query = query.join(Target.organizations).where(
                    Organization.id == org.id
                )
            else:
                query = query.where(Target.id is None)

        if target_type:
            query = query.where(Target.target_type == target_type)

        return query

    async def create_target(self, target_in: TargetCreate, user_id: str) -> TargetRead:
        target_type = validate_target(target_in.target_value)
        if not target_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target format",
            )

        project = await self._get_project_by_slug(target_in.project_slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        await self._check_duplicate_target(target_in.target_value, project.id)

        organizations = await self._get_or_create_organizations(
            target_in.organization_names, project.id, user_id
        )
        tags = await self._get_or_create_tags(target_in.tag_names, project.id, user_id)

        target = Target(
            target_value=target_in.target_value,
            target_type=target_type,
            display_name=target_in.display_name or target_in.target_value,
            project_id=project.id,
            created_by=user_id,
            organizations=organizations,
            tags=tags,
        )
        self.session.add(target)
        await self.session.commit()
        await self.session.refresh(target)

        await self._post_create_actions(target)

        return self._to_target_read(target)

    async def bulk_create_targets(
        self, bulk_in: TargetBulkCreate, user_id: str
    ) -> TargetBulkCreateResponse:
        project = await self._get_project_by_slug(bulk_in.project_slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        existing_targets_result = await self.session.execute(
            select(Target.target_value).where(Target.project_id == project.id)
        )
        existing_target_values = set(existing_targets_result.scalars().all())

        organizations = await self._get_or_create_organizations(
            bulk_in.organization_names, project.id, user_id
        )
        tags = await self._get_or_create_tags(bulk_in.tag_names, project.id, user_id)

        results: list[TargetImportResult] = []
        imported_count = 0
        failed_count = 0
        skipped_duplicates = 0
        seen_in_batch: set[str] = set()
        created_targets: list[Target] = []

        for target_value in bulk_in.targets:
            result = await self._process_bulk_target(
                target_value=target_value,
                project_id=project.id,
                user_id=user_id,
                organizations=organizations,
                tags=tags,
                existing_target_values=existing_target_values,
                seen_in_batch=seen_in_batch,
            )

            results.append(result.import_result)

            if result.import_result.success:
                imported_count += 1
                if result.target:
                    created_targets.append(result.target)
            elif "duplicate" in result.import_result.error.lower():
                skipped_duplicates += 1
            else:
                failed_count += 1

        await self.session.commit()

        for target in created_targets:
            await self._post_create_actions(target)

        return TargetBulkCreateResponse(
            total=len(bulk_in.targets),
            imported=imported_count,
            failed=failed_count,
            skipped_duplicates=skipped_duplicates,
            results=results,
        )

    async def get_target(self, target_id: str) -> TargetRead:
        result = await self.session.execute(
            select(Target).where(Target.id == target_id)
        )
        target = result.scalar_one_or_none()

        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target not found",
            )

        return self._to_target_read(target)

    async def update_target(
        self, target_id: str, target_in: TargetUpdate, user_id: str
    ) -> TargetRead:
        result = await self.session.execute(
            select(Target).where(Target.id == target_id)
        )
        target = result.scalar_one_or_none()

        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target not found",
            )

        if target_in.display_name is not None:
            target.display_name = target_in.display_name

        if target_in.organization_names is not None:
            organizations = await self._get_or_create_organizations(
                target_in.organization_names, target.project_id, user_id
            )
            target.organizations = organizations

        if target_in.tag_names is not None:
            tags = await self._get_or_create_tags(
                target_in.tag_names, target.project_id, user_id
            )
            target.tags = tags

        target.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(target)

        return self._to_target_read(target)

    async def delete_target(self, target_id: str) -> None:
        result = await self.session.execute(
            select(Target).where(Target.id == target_id)
        )
        target = result.scalar_one_or_none()

        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target not found",
            )

        await self.session.delete(target)
        await self.session.commit()

    async def _get_project_by_slug(self, slug: str) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.slug == slug))
        return result.scalar_one_or_none()

    async def _get_organization_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _check_duplicate_target(self, target_value: str, project_id: str) -> None:
        existing_target = await self.session.execute(
            select(Target).where(
                Target.target_value == target_value,
                Target.project_id == project_id,
            )
        )

        if existing_target.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Target already exists in this project",
            )

    async def _get_or_create_organizations(
        self, org_names: list[str], project_id: str, user_id: str
    ) -> list[Organization]:
        organizations = []
        for org_name in org_names:
            org = await get_or_create_organization(
                org_name, project_id, user_id, self.session
            )
            organizations.append(org)
        return organizations

    async def _get_or_create_tags(
        self, tag_names: list[str], project_id: str, user_id: str
    ) -> list[Tag]:
        tags = []
        for tag_name in tag_names:
            tag = await get_or_create_tag(tag_name, project_id, user_id, self.session)
            tags.append(tag)
        return tags

    async def _process_bulk_target(
        self,
        target_value: str,
        project_id: str,
        user_id: str,
        organizations: list[Organization],
        tags: list[Tag],
        existing_target_values: set[str],
        seen_in_batch: set[str],
    ) -> "BulkTargetResult":
        _target_value = target_value.strip()

        if not _target_value:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Empty target value",
                )
            )

        if _target_value in seen_in_batch:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Duplicate within import batch",
                )
            )

        if _target_value in existing_target_values:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Target already exists in project",
                )
            )

        target_type = validate_target(_target_value)
        if not target_type:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=_target_value,
                    success=False,
                    error="Invalid target format",
                )
            )

        target = Target(
            target_value=_target_value,
            target_type=target_type,
            display_name=_target_value,
            project_id=project_id,
            created_by=user_id,
            organizations=organizations,
            tags=tags,
        )
        self.session.add(target)

        seen_in_batch.add(_target_value)
        existing_target_values.add(_target_value)

        return BulkTargetResult(
            import_result=TargetImportResult(
                target_value=_target_value,
                success=True,
                target_type=target_type,
                target_id=target.id,
            ),
            target=target,
        )

    def _to_target_read(self, target: Target) -> TargetRead:
        return TargetRead(
            **target.model_dump(exclude={"organizations", "tags"}),
            organizations=[
                OrganizationSummary(
                    id=org.id,
                    name=org.name,
                    slug=org.slug,
                )
                for org in target.organizations
            ],
            tags=[
                TagSummary(
                    id=tag.id,
                    name=tag.name,
                    slug=tag.slug,
                    color=tag.color,
                )
                for tag in target.tags
            ],
        )

    async def import_targets_csv(
        self, project_slug: str, file: UploadFile, user_id: str
    ) -> TargetBulkCreateResponse:
        """
        Import targets from a CSV file.

        CSV Format Options:
        1. Simple (single column): target_value
        2. With tags: target_value, tags (comma-separated)
        3. With organizations: target_value, organizations (comma-separated)
        4. Full: target_value, tags, organizations, display_name

        Headers are optional but recommended. If no headers, assumes first column is target_value.
        """
        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file",
            )

        # Read and decode file
        try:
            content = await file.read()
            csv_text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be UTF-8 encoded",
            ) from e

        # Parse CSV into TargetImportItem objects
        targets_data = self._parse_csv_to_targets(csv_text)

        if not targets_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid targets found in CSV file",
            )

        if len(targets_data) > MAX_TARGETS_IMPORT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many targets in CSV file. Maximum is {MAX_TARGETS_IMPORT}, found {len(targets_data)}",
            )

        # Use the structured import logic
        import_request = TargetImportRequest(
            project_slug=project_slug,
            targets=targets_data,
        )

        return await self.import_targets_structured(import_request, user_id)

    async def import_targets_structured(
        self, import_request: TargetImportRequest, user_id: str
    ) -> TargetBulkCreateResponse:
        """
        Import targets from structured data (CSV/JSON) with per-target customization.

        Each target can have its own tags and organizations, for both csv and json.
        """
        project = await self._get_project_by_slug(import_request.project_slug)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        existing_targets_result = await self.session.execute(
            select(Target.target_value).where(Target.project_id == project.id)
        )
        existing_target_values = set(existing_targets_result.scalars().all())

        results: list[TargetImportResult] = []
        imported_count = 0
        failed_count = 0
        skipped_duplicates = 0
        seen_in_batch: set[str] = set()
        created_targets: list[Target] = []

        for item in import_request.targets:
            result = await self._process_import_item(
                item=item,
                project_id=project.id,
                user_id=user_id,
                existing_target_values=existing_target_values,
                seen_in_batch=seen_in_batch,
            )

            results.append(result.import_result)

            if result.import_result.success:
                imported_count += 1
                if result.target:
                    created_targets.append(result.target)
            elif "duplicate" in result.import_result.error.lower():
                skipped_duplicates += 1
            else:
                failed_count += 1

        await self.session.commit()

        for target in created_targets:
            await self._post_create_actions(target)

        return TargetBulkCreateResponse(
            total=len(import_request.targets),
            imported=imported_count,
            failed=failed_count,
            skipped_duplicates=skipped_duplicates,
            results=results,
        )

    async def _process_import_item(
        self,
        item: TargetImportItem,
        project_id: str,
        user_id: str,
        existing_target_values: set[str],
        seen_in_batch: set[str],
    ) -> "BulkTargetResult":
        """Process a single target for structured import (CSV/JSON with per-target tags/orgs)"""

        target_value = item.target_value.strip()

        # Skip empty values
        if not target_value:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Empty target value",
                )
            )

        # Check duplicates in current batch
        if target_value in seen_in_batch:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Duplicate within import batch",
                )
            )

        # Check duplicates in existing project targets
        if target_value in existing_target_values:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Target already exists in project",
                )
            )

        # Validate target format
        target_type = validate_target(target_value)
        if not target_type:
            return BulkTargetResult(
                import_result=TargetImportResult(
                    target_value=target_value,
                    success=False,
                    error="Invalid target format",
                )
            )

        # Get or create organizations for this specific target
        organizations = []
        for org_name in item.organizations:
            if org_name.strip():
                org = await get_or_create_organization(
                    org_name.strip(), project_id, user_id, self.session
                )
                organizations.append(org)

        # Get or create tags for this specific target
        tags = []
        for tag_name in item.tags:
            if tag_name.strip():
                tag = await get_or_create_tag(
                    tag_name.strip(), project_id, user_id, self.session
                )
                tags.append(tag)

        # Create the target
        target = Target(
            target_value=target_value,
            target_type=target_type,
            display_name=item.display_name or target_value,
            project_id=project_id,
            created_by=user_id,
            organizations=organizations,
            tags=tags,
        )
        self.session.add(target)

        seen_in_batch.add(target_value)
        existing_target_values.add(target_value)

        return BulkTargetResult(
            import_result=TargetImportResult(
                target_value=target_value,
                success=True,
                target_type=target_type,
                target_id=target.id,
            ),
            target=target,
        )

    # csv imports parser
    def _parse_csv_to_targets(self, csv_text: str) -> list[TargetImportItem]:
        csv_reader = csv.DictReader(io.StringIO(csv_text))

        # If no headers detected,read it as simple list
        if csv_reader.fieldnames is None or not csv_reader.fieldnames:
            csv_reader = csv.reader(io.StringIO(csv_text))
            targets_data = [
                TargetImportItem(target_value=row[0].strip())
                for row in csv_reader
                if row and row[0].strip()
            ]
        else:
            fieldnames = [field.lower().strip() for field in csv_reader.fieldnames]

            targets_data = []
            for row in csv_reader:
                if not any(row.values()):
                    continue

                # Get target value supported with key target_value, target, value, domain, or ip (required)
                target_value = None
                for key in ["target_value", "target", "value", "domain", "ip"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        target_value = row.get(orig_key, "").strip()
                        break

                if not target_value:
                    continue

                # Get tags supported with key tags or tag (optional)
                tags = []
                for key in ["tags", "tag"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        tags_str = row.get(orig_key, "").strip()
                        if tags_str:
                            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                        break

                # Get organizations supported with key organizations, organization, orgs, org (optional)
                organizations = []
                for key in ["organizations", "organization", "orgs", "org"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        orgs_str = row.get(orig_key, "").strip()
                        if orgs_str:
                            organizations = [
                                o.strip() for o in orgs_str.split(",") if o.strip()
                            ]
                        break

                # Get display name supported with key display_name or name (optional)
                display_name = None
                for key in ["display_name", "name"]:
                    if key in fieldnames:
                        idx = fieldnames.index(key)
                        orig_key = csv_reader.fieldnames[idx]
                        display_name = row.get(orig_key, "").strip() or None
                        break

                targets_data.append(
                    TargetImportItem(
                        target_value=target_value,
                        tags=tags,
                        organizations=organizations,
                        display_name=display_name,
                    )
                )

        return targets_data

    async def _post_create_actions(self, target: Target) -> None:
        pass
