from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.db.session import get_db
from app.models.user import User
from app.models.future import MaintenanceIssue, ActionLog, MaintenanceJob, VerificationRun, PullRequest
from app.models.scan import RepositoryScan
from app.models.readiness import RepositoryReadiness
from app.api.deps import get_current_user
from app.schemas.repository import (
    RepositoryResponse,
    ConnectRepositoryRequest,
    ToggleMonitoringRequest,
    DashboardStatsResponse,
    GitHubRepoImportItem,
    LatestCommitSchema
)
from app.schemas.scan import (
    RepositoryScanResponse,
    MaintenanceIssueResponse,
    RepositoryReadinessResponse,
    ActionLogResponse
)
from app.schemas.patch import MaintenanceJobResponse
from app.schemas.verification import VerificationRunResponse
from app.schemas.delivery import PullRequestResponse
from app.services.repository_service import RepositoryService
from app.services.github_service import GitHubService
from app.services.scanner_service import ScannerService
from app.services.patch_service import PatchService
from app.services.verification.verification_service import VerificationService
from app.services.delivery_service import DeliveryService

router = APIRouter()


def _to_repository_response(repo) -> RepositoryResponse:
    latest_commit = LatestCommitSchema(
        sha=repo.latest_commit_sha,
        message=repo.latest_commit_message,
        author=repo.latest_commit_author,
        date=repo.latest_commit_date
    )
    return RepositoryResponse(
        id=repo.id,
        user_id=repo.user_id,
        github_repo_id=repo.github_repo_id,
        name=repo.name,
        full_name=repo.full_name,
        owner=repo.owner,
        default_branch=repo.default_branch,
        primary_language=repo.primary_language,
        visibility=repo.visibility,
        clone_url=repo.clone_url,
        html_url=repo.html_url,
        latest_commit=latest_commit,
        monitoring_status=repo.monitoring_status,
        connection_status=repo.connection_status,
        last_checked_at=repo.last_checked_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at
    )


@router.get("/available", response_model=List[GitHubRepoImportItem])
async def list_available_github_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    token = await RepositoryService.get_user_github_token(db, current_user.id)
    gh_repos = await GitHubService.fetch_user_repositories(token)

    connected_repos = await RepositoryService.list_connected_repositories(db, current_user.id)
    connected_ids = {r.github_repo_id for r in connected_repos}

    items = []
    for r in gh_repos:
        repo_id_str = str(r.get("id"))
        items.append(
            GitHubRepoImportItem(
                github_repo_id=repo_id_str,
                name=r.get("name"),
                full_name=r.get("full_name"),
                owner=r.get("owner", {}).get("login", ""),
                default_branch=r.get("default_branch", "main"),
                primary_language=r.get("language"),
                visibility="private" if r.get("private") else "public",
                clone_url=r.get("clone_url", ""),
                html_url=r.get("html_url", ""),
                description=r.get("description"),
                is_connected=(repo_id_str in connected_ids)
            )
        )
    return items


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repos = await RepositoryService.list_connected_repositories(db, current_user.id)
    return [_to_repository_response(r) for r in repos]


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stats = await RepositoryService.get_dashboard_stats(db, current_user.id)
    return DashboardStatsResponse(**stats)


@router.post("/connect", response_model=RepositoryResponse)
async def connect_repository(
    payload: ConnectRepositoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await RepositoryService.connect_repository(
        db=db,
        user_id=current_user.id,
        github_repo_id=payload.github_repo_id,
        full_name=payload.full_name
    )
    return _to_repository_response(repo)


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository_detail(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await RepositoryService.get_repository_by_id(db, current_user.id, repository_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    return _to_repository_response(repo)


@router.delete("/{repository_id}")
async def remove_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect a repository from TALOS. GitHub is never touched — this only
    means TALOS stops tracking/monitoring the repository. Scan history, issues,
    and action logs are preserved (soft-delete)."""
    await RepositoryService.remove_repository(db, current_user.id, repository_id)
    return {"message": "Repository disconnected from TALOS.", "repository_id": repository_id}


@router.post("/{repository_id}/sync", response_model=RepositoryResponse)
async def sync_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await RepositoryService.sync_repository_metadata(db, current_user.id, repository_id)
    return _to_repository_response(repo)


@router.patch("/{repository_id}/monitoring", response_model=RepositoryResponse)
async def toggle_monitoring(
    repository_id: int,
    payload: ToggleMonitoringRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await RepositoryService.toggle_monitoring_status(
        db, current_user.id, repository_id, payload.monitoring_status
    )
    return _to_repository_response(repo)


# ==========================================
# PHASE 2: SCAN & ISSUE ENDPOINTS
# ==========================================

@router.post("/{repository_id}/scan", response_model=RepositoryScanResponse)
async def trigger_repository_scan(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger a repository scan for vulnerabilities and readiness."""
    repo = await RepositoryService.get_repository_by_id(db, current_user.id, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    token = await RepositoryService.get_user_github_token(db, current_user.id)
    scan = await ScannerService.run_repository_scan(db, current_user.id, repository_id, token)
    return scan


@router.get("/{repository_id}/scans", response_model=List[RepositoryScanResponse])
async def list_repository_scans(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RepositoryScan).where(RepositoryScan.repository_id == repository_id).order_by(desc(RepositoryScan.started_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{repository_id}/issues", response_model=List[MaintenanceIssueResponse])
async def list_repository_issues(
    repository_id: int,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(MaintenanceIssue).where(MaintenanceIssue.repository_id == repository_id)
    if status_filter:
        stmt = stmt.where(MaintenanceIssue.status == status_filter)
    stmt = stmt.order_by(desc(MaintenanceIssue.detected_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{repository_id}/issues/{issue_id}", response_model=MaintenanceIssueResponse)
async def get_issue_detail(
    repository_id: int,
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(MaintenanceIssue).where(MaintenanceIssue.id == issue_id, MaintenanceIssue.repository_id == repository_id)
    res = await db.execute(stmt)
    issue = res.scalars().first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    return issue


@router.get("/{repository_id}/readiness", response_model=Optional[RepositoryReadinessResponse])
async def get_repository_readiness(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RepositoryReadiness).where(RepositoryReadiness.repository_id == repository_id)
    res = await db.execute(stmt)
    return res.scalars().first()


@router.get("/{repository_id}/logs", response_model=List[ActionLogResponse])
async def get_repository_logs(
    repository_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ActionLog).where(ActionLog.repository_id == repository_id).order_by(desc(ActionLog.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


# ==========================================
# PHASE 3: PLANNING & PATCH GENERATION
# ==========================================

@router.post("/{repository_id}/issues/{issue_id}/prepare-fix", response_model=MaintenanceJobResponse)
async def prepare_fix(
    repository_id: int,
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run the real Phase 3 workflow for one maintenance issue: gather context,
    analyze, plan, assess risk, create an isolated workspace + TALOS branch, and
    generate a patch. Never touches the repository's primary branch and never
    pushes or opens a pull request."""
    token = await RepositoryService.get_user_github_token(db, current_user.id)
    try:
        job = await PatchService.prepare_fix(db, current_user.id, repository_id, issue_id, token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prepare fix failed: {exc}")
    return await PatchService.to_response_dict(db, job)


@router.get("/{repository_id}/issues/{issue_id}/jobs", response_model=List[MaintenanceJobResponse])
async def list_issue_jobs(
    repository_id: int,
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(MaintenanceJob)
        .where(MaintenanceJob.repository_id == repository_id, MaintenanceJob.issue_id == issue_id)
        .order_by(desc(MaintenanceJob.created_at))
    )
    res = await db.execute(stmt)
    jobs = res.scalars().all()
    return [await PatchService.to_response_dict(db, job) for job in jobs]


@router.get("/{repository_id}/jobs/{job_id}", response_model=MaintenanceJobResponse)
async def get_job_detail(
    repository_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(MaintenanceJob).where(MaintenanceJob.id == job_id, MaintenanceJob.repository_id == repository_id)
    res = await db.execute(stmt)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Maintenance job not found.")
    return await PatchService.to_response_dict(db, job)


# ==========================================
# PHASE 4: VERIFICATION ENGINE
# ==========================================

@router.post("/{repository_id}/jobs/{job_id}/verify", response_model=VerificationRunResponse)
async def verify_job(
    repository_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run the real Phase 4 verification pipeline against a PATCH_READY job:
    isolated sandbox, deterministic checks (install/build/typecheck/lint/test/
    security audit), and a re-scan confirming the original vulnerability is
    actually gone. Never merges or pushes anywhere — only decides
    VERIFIED vs VERIFICATION_FAILED."""
    run = await VerificationService.run_verification(db, current_user.id, repository_id, job_id)
    return await VerificationService.to_response_dict(db, run)


@router.get("/{repository_id}/jobs/{job_id}/verification-runs", response_model=List[VerificationRunResponse])
async def list_verification_runs(
    repository_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(VerificationRun)
        .join(MaintenanceJob, VerificationRun.maintenance_job_id == MaintenanceJob.id)
        .where(MaintenanceJob.id == job_id, MaintenanceJob.repository_id == repository_id)
        .order_by(desc(VerificationRun.started_at))
    )
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [await VerificationService.to_response_dict(db, run) for run in runs]


@router.get("/{repository_id}/verification-runs/{run_id}", response_model=VerificationRunResponse)
async def get_verification_run(
    repository_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(VerificationRun)
        .join(MaintenanceJob, VerificationRun.maintenance_job_id == MaintenanceJob.id)
        .where(VerificationRun.id == run_id, MaintenanceJob.repository_id == repository_id)
    )
    res = await db.execute(stmt)
    run = res.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Verification run not found.")
    return await VerificationService.to_response_dict(db, run)


# ==========================================
# PHASE 5: GITHUB DELIVERY & PULL REQUESTS
# ==========================================

@router.post("/{repository_id}/jobs/{job_id}/deliver", response_model=PullRequestResponse)
async def deliver_job(
    repository_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deliver a VERIFIED patch as a real GitHub pull request: reuse the exact
    commit that passed Phase 4 verification (never regenerated), push it on its
    TALOS branch, and open a PR against the repository's default branch. TALOS
    never merges — a human always reviews. Safe to call repeatedly: an already
    delivered job returns its existing pull request instead of creating a
    duplicate, and a partially-failed delivery resumes rather than restarting."""
    token = await RepositoryService.get_user_github_token(db, current_user.id)
    pr = await DeliveryService.deliver(db, current_user.id, repository_id, job_id, token)
    return DeliveryService.to_response_dict(pr)


@router.get("/{repository_id}/jobs/{job_id}/pull-request", response_model=Optional[PullRequestResponse])
async def get_job_pull_request(
    repository_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(PullRequest)
        .where(PullRequest.maintenance_job_id == job_id, PullRequest.repository_id == repository_id)
        .order_by(desc(PullRequest.created_at))
    )
    res = await db.execute(stmt)
    pr = res.scalars().first()
    return DeliveryService.to_response_dict(pr) if pr else None


@router.get("/{repository_id}/pull-requests", response_model=List[PullRequestResponse])
async def list_repository_pull_requests(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compact operational history of every PR TALOS has opened for this repository."""
    stmt = (
        select(PullRequest)
        .where(PullRequest.repository_id == repository_id, PullRequest.status == "delivered")
        .order_by(desc(PullRequest.created_at))
    )
    res = await db.execute(stmt)
    prs = res.scalars().all()
    return [DeliveryService.to_response_dict(pr) for pr in prs]


@router.post("/{repository_id}/pull-requests/{pr_id}/refresh-status", response_model=PullRequestResponse)
async def refresh_pull_request_status(
    repository_id: int,
    pr_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Secondary/best-effort: pull real OPEN/MERGED/CLOSED state from GitHub."""
    token = await RepositoryService.get_user_github_token(db, current_user.id)
    pr = await DeliveryService.refresh_status(db, current_user.id, repository_id, pr_id, token)
    return DeliveryService.to_response_dict(pr)
