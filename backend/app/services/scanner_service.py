import os
import re
import shutil
import json
import hashlib
import tempfile
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.models.repository import Repository
from app.models.scan import RepositoryScan
from app.models.dependency import Dependency
from app.models.readiness import RepositoryReadiness
from app.models.future import MaintenanceIssue, ActionLog
from app.services.github_service import GitHubService
from app.services.readiness_service import ReadinessService
from app.services.usage_finder_service import UsageFinderService

logger = logging.getLogger("talos.scanner")
OSV_API_BATCH_URL = "https://api.osv.dev/v1/querybatch"


class ScannerService:
    """Core scanner orchestrator managing repository cloning, dependency parsing, OSV security queries, and issue lifecycle."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        repository_id: int,
        scan_id: int,
        step: str,
        message: str,
        level: str = "INFO"
    ):
        """Append an entry to the ActionLog ledger."""
        log_entry = ActionLog(
            repository_id=repository_id,
            scan_id=scan_id,
            step=step,
            message=message,
            level=level,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        await db.commit()

    @staticmethod
    def _compute_fingerprint(repository_id: int, package_name: str, advisory_id: str, affected_range: str) -> str:
        raw = f"{repository_id}:vulnerability:{package_name}:{advisory_id}:{affected_range}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_severity(osv_severity_list: List[Dict[str, Any]], database_specific: Dict[str, Any] = None) -> str:
        """Map vulnerability severity to standard TALOS levels: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN."""
        if database_specific and "severity" in database_specific:
            sev = str(database_specific["severity"]).upper()
            if sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                return sev
            if "MODERATE" in sev:
                return "MEDIUM"

        for s in osv_severity_list or []:
            score = s.get("score")
            if score and isinstance(score, str) and score.startswith("CVSS"):
                # Quick CVSS score extraction
                match = re.search(r"/BaseScore:(\d+\.\d+)", score)
                if match:
                    val = float(match.group(1))
                    if val >= 9.0:
                        return "CRITICAL"
                    elif val >= 7.0:
                        return "HIGH"
                    elif val >= 4.0:
                        return "MEDIUM"
                    else:
                        return "LOW"

        return "HIGH"  # Default fallback for reported OSV vulnerabilities

    @staticmethod
    async def query_osv_vulnerabilities(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Query the OSV API in batch mode for package vulnerability advisories."""
        if not queries:
            return []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    OSV_API_BATCH_URL,
                    json={"queries": queries},
                    timeout=20.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("results", [])
                return []
            except Exception as exc:
                logger.error(f"OSV API batch query failed: {exc}")
                return []

    @staticmethod
    async def run_repository_scan(
        db: AsyncSession, user_id: int, repository_id: int, token: str, trigger: str = "manual"
    ) -> RepositoryScan:
        """Main pipeline executing full repository intelligence & detection.
        `trigger` (Phase 7) records provenance only — manual/scheduled_scan/
        github_push — and never changes scan behavior itself."""
        # 1. Fetch Repository record
        stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == user_id)
        result = await db.execute(stmt)
        repo = result.scalars().first()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found.")

        # 2. Create Scan record
        scan = RepositoryScan(
            repository_id=repository_id,
            status="running",
            trigger=trigger,
            started_at=datetime.now(timezone.utc)
        )
        db.add(scan)
        await db.commit()
        await db.refresh(scan)

        temp_dir = tempfile.mkdtemp(prefix=f"talos_scan_{scan.id}_")

        try:
            await ScannerService.log_action(db, repository_id, scan.id, "WATCH", f"Scan #{scan.id} initialized for {repo.full_name}")

            # 3. Retrieve/Clone Repository into isolated workspace
            clone_url_authed = repo.clone_url
            if token and "github.com" in repo.clone_url:
                clone_url_authed = repo.clone_url.replace("https://github.com/", f"https://x-access-token:{token}@github.com/")

            await ScannerService.log_action(db, repository_id, scan.id, "DETECT", "Cloning repository into isolated workspace...")
            
            # Run git clone command safely
            import subprocess
            clone_cmd = ["git", "clone", "--depth", "1", "--branch", repo.default_branch, clone_url_authed, temp_dir]
            proc = subprocess.run(clone_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            
            if proc.returncode != 0:
                # Fallback to cloning without branch specified if default branch failed
                clone_cmd_alt = ["git", "clone", "--depth", "1", clone_url_authed, temp_dir]
                proc_alt = subprocess.run(clone_cmd_alt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                if proc_alt.returncode != 0:
                    raise RuntimeError(f"Git clone failed: {proc_alt.stderr or proc.stderr}")

            await ScannerService.log_action(db, repository_id, scan.id, "DETECT", "Repository cloned successfully.")

            # 4. Project Ecosystem & Dependency Parsing
            parsed_dependencies: List[Dict[str, Any]] = []
            ecosystem = "npm"

            pkg_json_path = os.path.join(temp_dir, "package.json")
            req_txt_path = os.path.join(temp_dir, "requirements.txt")

            if os.path.exists(pkg_json_path):
                ecosystem = "npm"
                await ScannerService.log_action(db, repository_id, scan.id, "UNDERSTAND", "npm ecosystem detected (package.json)")
                try:
                    with open(pkg_json_path, "r", encoding="utf-8") as f:
                        pkg_data = json.load(f)
                        
                        deps = pkg_data.get("dependencies", {})
                        for name, ver in deps.items():
                            parsed_dependencies.append({
                                "name": name,
                                "version": str(ver).replace("^", "").replace("~", "").replace(">=", "").replace("=", ""),
                                "declared_version": str(ver),
                                "dep_type": "dependencies",
                                "ecosystem": "npm",
                                "manifest_path": "package.json"
                            })

                        dev_deps = pkg_data.get("devDependencies", {})
                        for name, ver in dev_deps.items():
                            parsed_dependencies.append({
                                "name": name,
                                "version": str(ver).replace("^", "").replace("~", "").replace(">=", "").replace("=", ""),
                                "declared_version": str(ver),
                                "dep_type": "devDependencies",
                                "ecosystem": "npm",
                                "manifest_path": "package.json"
                            })
                except Exception as e:
                    logger.error(f"Error parsing package.json: {e}")

            elif os.path.exists(req_txt_path):
                ecosystem = "pip"
                await ScannerService.log_action(db, repository_id, scan.id, "UNDERSTAND", "Python PyPI ecosystem detected (requirements.txt)")
                try:
                    with open(req_txt_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                parts = line.split("==")
                                name = parts[0].strip()
                                ver = parts[1].strip() if len(parts) > 1 else "0.0.0"
                                parsed_dependencies.append({
                                    "name": name,
                                    "version": ver,
                                    "declared_version": line,
                                    "dep_type": "dependencies",
                                    "ecosystem": "pip",
                                    "manifest_path": "requirements.txt"
                                })
                except Exception as e:
                    logger.error(f"Error parsing requirements.txt: {e}")

            # Persist parsed dependencies to database
            await db.execute(delete(Dependency).where(Dependency.repository_id == repository_id))
            for d in parsed_dependencies:
                db.add(Dependency(
                    repository_id=repository_id,
                    name=d["name"],
                    declared_version=d["declared_version"],
                    dep_type=d["dep_type"],
                    ecosystem=d["ecosystem"],
                    manifest_path=d["manifest_path"]
                ))
            await db.commit()

            scan.ecosystem = ecosystem
            scan.total_dependencies = len(parsed_dependencies)
            await ScannerService.log_action(db, repository_id, scan.id, "UNDERSTAND", f"{len(parsed_dependencies)} dependencies parsed.")

            # 5. Security Analysis (OSV Batch Query)
            await ScannerService.log_action(db, repository_id, scan.id, "PLAN", "Querying vulnerability database (OSV API)...")
            
            osv_queries = []
            osv_ecosystem_map = {"npm": "npm", "pip": "PyPI"}
            target_osv_eco = osv_ecosystem_map.get(ecosystem, "npm")

            for dep in parsed_dependencies:
                if dep["version"] and dep["version"] != "0.0.0":
                    osv_queries.append({
                        "package": {"name": dep["name"], "ecosystem": target_osv_eco},
                        "version": dep["version"]
                    })

            osv_results = await ScannerService.query_osv_vulnerabilities(osv_queries)
            
            detected_issues_data = []
            current_scan_fingerprints = set()

            for i, result_item in enumerate(osv_results):
                vulns = result_item.get("vulns", [])
                if not vulns:
                    continue

                dep_info = parsed_dependencies[i] if i < len(parsed_dependencies) else {}
                pkg_name = dep_info.get("name", "unknown")
                curr_ver = dep_info.get("version", "0.0.0")

                for vuln in vulns:
                    advisory_id = vuln.get("id", "OSV-UNKNOWN")
                    summary = vuln.get("summary") or vuln.get("details", f"Security vulnerability in {pkg_name}")
                    details_text = vuln.get("details", "")

                    # Extract recommended fixed version if available
                    recommended_ver = None
                    affected_ranges_str = ""
                    for affected in vuln.get("affected", []):
                        for r in affected.get("ranges", []):
                            for event in r.get("events", []):
                                if "fixed" in event:
                                    recommended_ver = event["fixed"]
                                if "introduced" in event:
                                    affected_ranges_str += f">={event['introduced']} "

                    if not affected_ranges_str:
                        affected_ranges_str = f"<{recommended_ver}" if recommended_ver else f"at version {curr_ver}"

                    severity = ScannerService._normalize_severity(vuln.get("severity", []), vuln.get("database_specific", {}))
                    fingerprint = ScannerService._compute_fingerprint(repository_id, pkg_name, advisory_id, affected_ranges_str)
                    current_scan_fingerprints.add(fingerprint)

                    # Find affected source code files
                    affected_files = UsageFinderService.find_package_usages(temp_dir, pkg_name)

                    detected_issues_data.append({
                        "fingerprint": fingerprint,
                        "title": f"Vulnerability in {pkg_name}: {summary[:100]}",
                        "description": details_text or summary,
                        "severity": severity,
                        "category": "vulnerability",
                        "package_name": pkg_name,
                        "current_version": curr_ver,
                        "affected_range": affected_ranges_str.strip(),
                        # "latest" (not a human-readable label) — this value flows straight
                        # into deterministic package-manager upgrade commands in Phase 3,
                        # so it must always be a string npm/pip can actually resolve.
                        "recommended_version": recommended_ver or "latest",
                        "advisory_id": advisory_id,
                        "source": "OSV / Advisory",
                        "affected_files": affected_files,
                        "details": vuln
                    })

            # 6. Issue Normalization & Deduplication Lifecycle
            await ScannerService.log_action(db, repository_id, scan.id, "PATCH", f"Processing {len(detected_issues_data)} detected security findings...")
            
            # Fetch existing issues for repository
            stmt_issues = select(MaintenanceIssue).where(MaintenanceIssue.repository_id == repository_id)
            res_issues = await db.execute(stmt_issues)
            existing_issues = {iss.fingerprint: iss for iss in res_issues.scalars().all() if iss.fingerprint}

            now_utc = datetime.now(timezone.utc)

            for issue_data in detected_issues_data:
                fp = issue_data["fingerprint"]
                if fp in existing_issues:
                    # Update existing issue
                    existing_issue = existing_issues[fp]
                    existing_issue.last_seen_at = now_utc
                    existing_issue.status = "OPEN"
                    existing_issue.affected_files = issue_data["affected_files"]
                    existing_issue.recommended_version = issue_data["recommended_version"]
                else:
                    # Create new issue
                    new_issue = MaintenanceIssue(
                        repository_id=repository_id,
                        fingerprint=fp,
                        title=issue_data["title"],
                        description=issue_data["description"],
                        severity=issue_data["severity"],
                        category="vulnerability",
                        status="OPEN",
                        package_name=issue_data["package_name"],
                        current_version=issue_data["current_version"],
                        affected_range=issue_data["affected_range"],
                        recommended_version=issue_data["recommended_version"],
                        advisory_id=issue_data["advisory_id"],
                        source=issue_data["source"],
                        affected_files=issue_data["affected_files"],
                        details=issue_data["details"],
                        detected_at=now_utc,
                        last_seen_at=now_utc
                    )
                    db.add(new_issue)

            # Mark issues no longer detected as RESOLVED
            for fp, existing_issue in existing_issues.items():
                if fp not in current_scan_fingerprints and existing_issue.status == "OPEN":
                    existing_issue.status = "RESOLVED"
                    existing_issue.resolved_at = now_utc

            await db.commit()

            # 7. Evaluate Automation Readiness
            readiness_data = ReadinessService.evaluate_repository(temp_dir)
            
            stmt_readiness = select(RepositoryReadiness).where(RepositoryReadiness.repository_id == repository_id)
            res_readiness = await db.execute(stmt_readiness)
            existing_readiness = res_readiness.scalars().first()

            if existing_readiness:
                existing_readiness.manifest_found = readiness_data["manifest_found"]
                existing_readiness.lockfile_found = readiness_data["lockfile_found"]
                existing_readiness.build_script_found = readiness_data["build_script_found"]
                existing_readiness.test_script_found = readiness_data["test_script_found"]
                existing_readiness.lint_script_found = readiness_data["lint_script_found"]
                existing_readiness.typecheck_script_found = readiness_data["typecheck_script_found"]
                existing_readiness.ci_config_found = readiness_data["ci_config_found"]
                existing_readiness.score_level = readiness_data["score_level"]
                existing_readiness.details = readiness_data["details"]
                existing_readiness.updated_at = now_utc
            else:
                db.add(RepositoryReadiness(
                    repository_id=repository_id,
                    manifest_found=readiness_data["manifest_found"],
                    lockfile_found=readiness_data["lockfile_found"],
                    build_script_found=readiness_data["build_script_found"],
                    test_script_found=readiness_data["test_script_found"],
                    lint_script_found=readiness_data["lint_script_found"],
                    typecheck_script_found=readiness_data["typecheck_script_found"],
                    ci_config_found=readiness_data["ci_config_found"],
                    score_level=readiness_data["score_level"],
                    details=readiness_data["details"],
                    updated_at=now_utc
                ))

            # 8. Complete Scan Record
            scan.status = "completed"
            scan.issues_detected = len(detected_issues_data)
            scan.completed_at = now_utc
            repo.last_scanned_at = now_utc
            
            await db.commit()

            await ScannerService.log_action(
                db, repository_id, scan.id, "VERIFY",
                f"Scan completed cleanly. Discovered {len(detected_issues_data)} vulnerability issues. Readiness level: {readiness_data['score_level']}."
            )

            return scan

        except Exception as exc:
            logger.error(f"Scan failed for repo {repository_id}: {exc}")
            scan.status = "failed"
            scan.error_message = str(exc)
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
            
            await ScannerService.log_action(db, repository_id, scan.id, "ESCALATE", f"Scan failed: {str(exc)}", level="ERROR")
            raise exc
        finally:
            # Clean up temporary isolated workspace
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
