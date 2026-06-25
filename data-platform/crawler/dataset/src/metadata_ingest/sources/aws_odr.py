from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Dict, Iterator, List, Optional, Tuple

import yaml

from ..base import BaseDatasetCollector, ResumeGate
from ..models import NormalizedDatasetRecord, SourceDefinition
from ..utils import (
    clean_text,
    domains_from_urls,
    ensure_list,
    guess_modalities_from_text,
    parse_bool,
    parse_bytes,
    parse_int,
    unique_strings,
)


SOURCE = SourceDefinition(
    source_code="AWS_ODR",
    source_name="AWS Open Data Registry",
    base_url="https://registry.opendata.aws",
    collection_type="API",
)


class AwsOdrCollector(BaseDatasetCollector):
    source = SOURCE
    _SIZE_PATTERN = re.compile(
        r"(?i)(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB|KiB|MiB|GiB|TiB|PiB)"
    )
    _SIZE_HINT_KEYWORDS = [
        "size",
        "dataset",
        "data",
        "storage",
        "volume",
        "compressed",
        "uncompressed",
    ]
    _JUNK_JSON_RE = re.compile(
        r"^JSON\s+활용신청\s+\d+\s+데이터\s+한계\s+키워드(?:\s+.+)?$"
    )

    def iter_records(
        self, checkpoint: Dict[str, Any]
    ) -> Iterator[Tuple[NormalizedDatasetRecord, Dict[str, Any]]]:
        default_branch = self._get_default_branch()
        files = self._list_dataset_yaml_files(default_branch)
        start_index = max(parse_int(checkpoint.get("index")) or 0, 0)
        resume_gate = ResumeGate(checkpoint.get("last_saved_source_dataset_key"))

        for idx, file_meta in enumerate(files[start_index:], start=start_index):
            path = file_meta.get("path") or ""
            source_key = str(path)
            if idx == start_index and not resume_gate.allow(source_key):
                continue
            try:
                raw_yaml = self.get_text(
                    self._raw_file_url(default_branch, path),
                    headers=self._github_headers(raw=False),
                )
                payload = yaml.safe_load(raw_yaml) or {}
                if not isinstance(payload, dict):
                    payload = {"raw": payload}
                yield (
                    self._normalize(payload, path=path, blob_sha=file_meta.get("sha")),
                    {"index": idx},
                )
            except Exception as exc:
                self.note_failure(source_key, exc)
                continue

    def _get_default_branch(self) -> str:
        headers = self._github_headers()
        payload = self.get_json(
            "https://api.github.com/repos/awslabs/open-data-registry", headers=headers
        )
        return clean_text(payload.get("default_branch")) or "main"

    def _list_dataset_yaml_files(self, branch: str) -> List[Dict[str, Any]]:
        headers = self._github_headers()
        payload = self.get_json(
            f"https://api.github.com/repos/awslabs/open-data-registry/git/trees/{branch}",
            params={"recursive": 1},
            headers=headers,
        )
        tree = payload.get("tree") or []
        files = [
            item
            for item in tree
            if isinstance(item, dict)
            and str(item.get("path", "")).startswith("datasets/")
            and str(item.get("path", "")).lower().endswith((".yaml", ".yml"))
        ]
        files.sort(key=lambda item: str(item.get("path", "")))
        return files

    def _github_headers(self, raw: bool = True) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        if raw:
            headers["Accept"] = "application/vnd.github+json"
        return headers

    def _raw_file_url(self, branch: str, path: str) -> str:
        return f"https://raw.githubusercontent.com/awslabs/open-data-registry/{branch}/{path}"

    def _normalize(
        self, raw: Dict[str, Any], *, path: str, blob_sha: Any
    ) -> NormalizedDatasetRecord:
        path_obj = PurePosixPath(path)
        slug = path_obj.stem
        source_key = path
        landing_url = f"https://registry.opendata.aws/{slug}/"
        title = clean_text(raw.get("Name")) or slug
        description = clean_text(raw.get("Description"))
        tags = self._safe_terms(
            unique_strings(
                ensure_list(raw.get("Tags")) + ensure_list(raw.get("ADXCategories"))
            )
        )

        resources: List[Dict[str, Any]] = []
        total_size = 0
        account_required = False
        controlled_access = False
        requester_pays = False
        for item in raw.get("Resources") or []:
            if not isinstance(item, dict):
                continue
            account_required = account_required or bool(
                parse_bool(item.get("AccountRequired"))
            )
            controlled_access = controlled_access or bool(
                parse_bool(item.get("ControlledAccess"))
            )
            requester_pays = requester_pays or bool(
                parse_bool(item.get("RequesterPays"))
            )
            size_bytes = parse_bytes(
                item.get("Size") or item.get("SizeBytes") or item.get("size")
            ) or parse_int(
                item.get("Size") or item.get("SizeBytes") or item.get("size")
            )
            if size_bytes:
                total_size += size_bytes
            resources.append(
                {
                    "description": clean_text(item.get("Description")),
                    "arn": clean_text(item.get("ARN") or item.get("Arn")),
                    "region": clean_text(item.get("Region")),
                    "type": clean_text(item.get("Type")),
                    "explore_url": clean_text(
                        item.get("Explore") or item.get("ExploreUrl")
                    ),
                    "size_bytes": size_bytes,
                    "account_required": parse_bool(item.get("AccountRequired")),
                    "controlled_access": parse_bool(item.get("ControlledAccess")),
                    "requester_pays": parse_bool(item.get("RequesterPays")),
                }
            )

        access_type = "OPEN"
        login_required = False
        approval_required = False
        payment_required = False
        is_restricted = False
        if controlled_access:
            access_type = "RESTRICTED"
            login_required = True
            approval_required = True
            is_restricted = True
        elif requester_pays:
            access_type = "PAID"
            login_required = True
            payment_required = True
            is_restricted = True
        elif account_required:
            access_type = "REGISTERED"
            login_required = True
            is_restricted = True

        creators = []
        contact = clean_text(raw.get("Contact"))
        if contact:
            creators.append({"name": contact, "role": "contact"})
        managed_by = clean_text(raw.get("ManagedBy"))
        if managed_by:
            creators.append({"name": managed_by, "role": "manager"})
        documentation = clean_text(raw.get("Documentation"))
        if documentation:
            creators.append({"url": documentation, "role": "documentation"})

        license_name = None
        license_url = None
        license_value = raw.get("License")
        license_name, license_url = self._normalize_license(license_value)
        dataset_size_bytes = (
            total_size
            or parse_bytes(raw.get("SizeBytes") or raw.get("DatasetSizeBytes"))
            or parse_int(raw.get("SizeBytes") or raw.get("DatasetSizeBytes"))
        )
        if not dataset_size_bytes:
            dataset_size_bytes = self._extract_size_from_text(
                clean_text(raw.get("Description")),
                clean_text(raw.get("Documentation")),
                clean_text(raw.get("Name")),
            )

        return NormalizedDatasetRecord(
            source_dataset_key=source_key,
            canonical_url=landing_url,
            landing_url=landing_url,
            title=title,
            description_short=description,
            description_long=description,
            publisher_name=managed_by or contact,
            domains=self._safe_terms(
                unique_strings(ensure_list(raw.get("ADXCategories")))
            ),
            tasks=tags,
            modalities=guess_modalities_from_text(
                title, description, tags, [r.get("type") for r in resources]
            ),
            tags=tags,
            languages=[],
            license_name=license_name,
            license_url=license_url,
            access_type=access_type,
            login_required=login_required,
            approval_required=approval_required,
            payment_required=payment_required,
            is_restricted=is_restricted,
            source_created_at=None,
            source_updated_at=None,
            source_version=clean_text(blob_sha),
            row_count=parse_int(raw.get("RecordCount") or raw.get("Rows")),
            dataset_size_bytes=dataset_size_bytes,
            creators_json=creators,
            resources_json=resources,
            schema_json={},
            metrics_json={},
            extra_json={
                "documentation": documentation,
                "citation": raw.get("Citation"),
                "deprecated_notice": raw.get("DeprecatedNotice"),
                "managed_by": managed_by,
                "contact": contact,
                "yaml_path": path,
            },
            raw_json=raw,
        )

    def _safe_terms(self, values: List[str]) -> List[str]:
        result: List[str] = []
        for term in values:
            text = clean_text(term)
            if not text:
                continue
            if self._JUNK_JSON_RE.match(text):
                continue
            if len(text) > 45 and len(text.split()) >= 6:
                continue
            result.append(text)
        return unique_strings(result)

    def _normalize_license(self, value: Any) -> Tuple[Optional[str], Optional[str]]:
        if value is None:
            return None, None

        if isinstance(value, dict):
            name, url = self._normalize_license(value.get("Name") or value.get("name"))
            if url:
                return name, url
            raw_url = clean_text(value.get("Url") or value.get("url"))
            if raw_url and raw_url.startswith("http"):
                return name, raw_url
            return name, None

        cleaned = clean_text(value)
        if not cleaned:
            return None, None

        markdown_name, markdown_url = self._parse_markdown_link(cleaned)
        if markdown_url:
            return markdown_name, markdown_url
        if cleaned.startswith("http"):
            return None, cleaned
        return cleaned, None

    def _parse_markdown_link(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        match = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", text)
        if not match:
            return None, None
        normalized_name = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)
        return clean_text(normalized_name), clean_text(match.group(2))

    def _extract_size_from_text(self, *texts: Optional[str]) -> Optional[int]:
        candidates: List[int] = []
        for text in texts:
            if not text:
                continue
            for match in self._SIZE_PATTERN.finditer(text):
                start = max(0, match.start() - 28)
                end = min(len(text), match.end() + 28)
                context = text[start:end].casefold()
                if not any(token in context for token in self._SIZE_HINT_KEYWORDS):
                    continue
                size_bytes = parse_bytes(f"{match.group(1)} {match.group(2)}")
                if size_bytes:
                    candidates.append(size_bytes)
        return max(candidates) if candidates else None
