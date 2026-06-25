from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import BaseDatasetCollector, ResumeGate
from ..models import NormalizedDatasetRecord, SourceDefinition
from ..utils import (
    clean_text,
    domains_from_urls,
    ensure_list,
    guess_modalities_from_text,
    parse_bool,
    parse_bytes,
    parse_datetime,
    parse_int,
    parse_kv_text_block,
    safe_get,
    unique_strings,
)


SOURCE = SourceDefinition(
    source_code="PUBLIC_DATA_PORTAL",
    source_name="공공데이터포털",
    base_url="https://www.data.go.kr",
    collection_type="CRAWL",
)

_DATASET_ID_RE = re.compile(r"/data/(\d+)/fileData\.do")
_SIZE_PATTERN = re.compile(
    r"(?i)(?:용량|데이터\s*크기|size|content\s*size|file\s*size|구축량)[^0-9]{0,24}(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB|KiB|MiB|GiB|TiB|PiB)"
)
_SIZE_VALUE_PATTERN = re.compile(
    r"(?i)(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB|KiB|MiB|GiB|TiB|PiB)"
)
_COLUMN_EMPTY_VALUES = {"", "-", "--", "N/A", "null", "None"}


class PublicDataPortalCollector(BaseDatasetCollector):
    source = SOURCE

    def iter_records(
        self, checkpoint: Dict[str, Any]
    ) -> Iterator[Tuple[NormalizedDatasetRecord, Dict[str, Any]]]:
        page = max(parse_int(checkpoint.get("page")) or 1, 1)
        start_page = page
        resume_gate = ResumeGate(checkpoint.get("last_saved_source_dataset_key"))
        seen_source_keys: Set[str] = set()
        fallback_to_first_page_attempted = False

        while True:
            detail_links: List[str] = []
            seen_detail_links: Set[str] = set()
            for list_url in self._list_url_variants(page):
                try:
                    soup = self.get_soup(list_url)
                except Exception as exc:
                    self.note_failure(f"list-page:{page}:{list_url}", exc)
                    continue
                for detail_url in self._extract_detail_links(soup):
                    if detail_url in seen_detail_links:
                        continue
                    seen_detail_links.add(detail_url)
                    detail_links.append(detail_url)
            if not detail_links:
                if not fallback_to_first_page_attempted and (
                    start_page > 1 or checkpoint.get("last_saved_source_dataset_key")
                ):
                    fallback_to_first_page_attempted = True
                    page = 1
                    start_page = 1
                    resume_gate = ResumeGate(None)
                    continue
                break

            page_new_items = 0

            for detail_url in detail_links:
                source_key = self._extract_dataset_id(detail_url)
                if not source_key:
                    continue
                if source_key in seen_source_keys:
                    continue
                if page == start_page and not resume_gate.allow(source_key):
                    continue
                seen_source_keys.add(source_key)
                page_new_items += 1

                try:
                    detail_html = self.get_text(detail_url)
                    detail_soup = BeautifulSoup(detail_html, "lxml")
                    schema_json = self._fetch_schema_json(source_key)
                    yield (
                        self._normalize(
                            source_key,
                            detail_url,
                            detail_soup,
                            schema_json,
                            detail_html=detail_html,
                        ),
                        {"page": page},
                    )
                except Exception as exc:
                    self.note_failure(source_key, exc)
                    continue

            if page_new_items == 0:
                if not fallback_to_first_page_attempted and (
                    start_page > 1 or checkpoint.get("last_saved_source_dataset_key")
                ):
                    fallback_to_first_page_attempted = True
                    page = 1
                    start_page = 1
                    resume_gate = ResumeGate(None)
                    continue
                break

            page += 1

    def _list_url_variants(self, page: int) -> List[str]:
        template = self.settings.public_data_portal_list_url_template
        base_url = template.format(page=page)
        variants: List[str] = []
        for locale_url in self._locale_url_variants(base_url):
            variants.append(locale_url)
            if "dType=" in locale_url:
                variants.append(self._replace_query_param(locale_url, "dType", "FILE"))

        return unique_strings(variants)

    def _locale_url_variants(self, url: str) -> List[str]:
        variants = [url]
        split_result = urlsplit(url)
        path = split_result.path

        if "/en/" in path:
            variants.append(
                urlunsplit(
                    (
                        split_result.scheme,
                        split_result.netloc,
                        path.replace("/en/", "/", 1),
                        split_result.query,
                        split_result.fragment,
                    )
                )
            )
        elif path.startswith("/tcs/"):
            variants.append(
                urlunsplit(
                    (
                        split_result.scheme,
                        split_result.netloc,
                        f"/en{path}",
                        split_result.query,
                        split_result.fragment,
                    )
                )
            )

        return unique_strings(variants)

    def _replace_query_param(self, url: str, key: str, value: str) -> str:
        split_result = urlsplit(url)
        query_items = parse_qsl(split_result.query, keep_blank_values=True)
        replaced = False
        updated_items: List[Tuple[str, str]] = []
        for k, v in query_items:
            if k == key:
                updated_items.append((k, value))
                replaced = True
            else:
                updated_items.append((k, v))
        if not replaced:
            updated_items.append((key, value))
        return urlunsplit(
            (
                split_result.scheme,
                split_result.netloc,
                split_result.path,
                urlencode(updated_items),
                split_result.fragment,
            )
        )

    def _extract_detail_links(self, soup: BeautifulSoup) -> List[str]:
        result: List[str] = []
        seen: Set[str] = set()
        for anchor in soup.select('a[href*="/data/"][href*="/fileData.do"]'):
            href = anchor.get("href")
            if not isinstance(href, str) or not href:
                continue
            url = urljoin(self.source.base_url, href)
            if url in seen:
                continue
            seen.add(url)
            result.append(url)
        return result

    def _extract_dataset_id(self, url: str) -> Optional[str]:
        match = _DATASET_ID_RE.search(url)
        return match.group(1) if match else None

    def _fetch_schema_json(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        schema_url = f"{self.source.base_url}/catalog/{dataset_id}/fileData.json"
        try:
            data = self.get_json(schema_url)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    def _normalize(
        self,
        source_key: str,
        detail_url: str,
        detail_soup: BeautifulSoup,
        schema_json: Optional[Dict[str, Any]],
        detail_html: Optional[str] = None,
    ) -> NormalizedDatasetRecord:
        detail_text = detail_soup.get_text(" ", strip=True)
        kv = parse_kv_text_block(detail_text)
        schema_dataset = self._extract_schema_dataset(schema_json)
        og_title = detail_soup.select_one("meta[property='og:title']")
        h1_tag = detail_soup.select_one("h1")
        h2_tag = detail_soup.select_one("h2")
        meta_description = detail_soup.select_one("meta[name='description']")

        title = (
            self._schema_text(schema_dataset, "name")
            or clean_text(og_title.get("content") if og_title else None)
            or clean_text(h1_tag.get_text(" ", strip=True) if h1_tag else None)
            or clean_text(h2_tag.get_text(" ", strip=True) if h2_tag else None)
            or source_key
        )

        description = (
            self._schema_text(schema_dataset, "description")
            or clean_text(meta_description.get("content") if meta_description else None)
            or kv.get("Description")
            or kv.get("Explanation")
        )

        keywords = unique_strings(
            self._schema_list(schema_dataset, "keywords")
            + self._split_csv(kv.get("Keyword"))
            + self._split_csv(kv.get("태그"))
        )
        domains = unique_strings(
            self._split_csv(kv.get("Classified"))
            + self._split_csv(kv.get("Classification System"))
            + self._split_csv(kv.get("분야"))
            + self._split_csv(kv.get("유형"))
        )
        tags = unique_strings(keywords + domains)

        publisher_name = (
            self._schema_org_name(schema_dataset, "publisher")
            or self._schema_org_name(schema_dataset, "creator")
            or kv.get("Provider")
            or kv.get("Department")
            or kv.get("Collected by")
            or kv.get("주관기관")
            or kv.get("수행기관")
        )

        resources = self._build_resources(schema_dataset, detail_url, kv)

        column_schema: Dict[str, Any] = {}
        try:
            column_schema = self._extract_column_schema(
                detail_url=detail_url,
                detail_soup=detail_soup,
                detail_html=detail_html,
            )
        except Exception as exc:
            self.note_failure(f"{source_key}:column-schema", exc)

        payment_text = clean_text(
            kv.get("Payment") or kv.get("결제") or kv.get("Charge Standard And Unit")
        )
        free_download_text = " ".join(
            value
            for value in [
                clean_text(detail_text),
                clean_text(kv.get("Provided")),
                clean_text(kv.get("Form Of Provision")),
            ]
            if value
        )
        payment_required = bool(
            payment_text and payment_text.casefold() not in {"free", "무료"}
        )

        login_required = False
        approval_required = False
        access_type = "OPEN"
        is_restricted = False
        if payment_required:
            access_type = "PAID"
            login_required = True
            is_restricted = True
        elif (
            "without logging in" in free_download_text.casefold()
            or "로그인 없이" in free_download_text
        ):
            access_type = "OPEN"
        else:
            access_hint = " ".join(
                value
                for value in [
                    clean_text(kv.get("Data Limit")),
                    clean_text(kv.get("Provided")),
                    clean_text(kv.get("Other")),
                ]
                if value
            )
            if any(
                token in access_hint.casefold()
                for token in ["apply", "approval", "restricted"]
            ):
                access_type = "APPROVAL"
                login_required = True
                approval_required = True
                is_restricted = True

        license_name = self._schema_text(schema_dataset, "license") or clean_text(
            kv.get("Scope of License") or kv.get("Scope Of Use")
        )
        license_url = self._schema_url(schema_dataset, "license")
        dataset_size_bytes = self._extract_dataset_size_bytes(
            schema_dataset=schema_dataset,
            resources=resources,
            kv=kv,
            detail_text=detail_text,
        )

        schema_payload: Dict[str, Any] = {
            "schema_org": schema_dataset,
        }
        columns = column_schema.get("columns")
        if isinstance(columns, list) and columns:
            schema_payload["columns"] = columns
        public_data_detail = column_schema.get("public_data_detail")
        if isinstance(public_data_detail, dict) and public_data_detail:
            schema_payload["public_data_detail"] = public_data_detail

        return NormalizedDatasetRecord(
            source_dataset_key=source_key,
            canonical_url=detail_url,
            landing_url=detail_url,
            title=title,
            description_short=description,
            description_long=description,
            publisher_name=publisher_name,
            domains=domains,
            tasks=keywords,
            modalities=guess_modalities_from_text(
                title, description, tags, [r.get("format") for r in resources]
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
            source_created_at=parse_datetime(
                kv.get("Registered")
                or kv.get("Enrollment")
                or self._schema_text(schema_dataset, "datePublished")
            ),
            source_updated_at=parse_datetime(
                kv.get("Edited")
                or kv.get("Correction")
                or self._schema_text(schema_dataset, "dateModified")
            ),
            source_version=None,
            row_count=parse_int(kv.get("All Rows") or kv.get("Whole Row")),
            dataset_size_bytes=dataset_size_bytes,
            creators_json=self._build_creators(schema_dataset, kv),
            resources_json=resources,
            schema_json=schema_payload,
            metrics_json={
                "download_count": parse_int(kv.get("Download")),
            },
            extra_json={
                "detail_kv": kv,
                "media_type": kv.get("Media Type"),
                "file_extension": kv.get("File Extension") or kv.get("Extension"),
            },
            raw_json={
                "schema_json": schema_json,
                "detail_text": detail_text,
            },
        )

    def _extract_column_schema(
        self,
        *,
        detail_url: str,
        detail_soup: BeautifulSoup,
        detail_html: Optional[str],
    ) -> Dict[str, Any]:
        html_text = detail_html or str(detail_soup)
        landing_columns, detail_keys = self._extract_columns_from_html(html_text)

        public_data_detail_pk = detail_keys.get("publicDataDetailPk")
        if public_data_detail_pk:
            detail_button_url = urljoin(
                self.source.base_url, "/tcs/dss/selectDpkDetailInfo.do"
            )
            detail_button_html = self.get_text(
                f"{detail_button_url}?publicDataDetailPk={public_data_detail_pk}"
            )
            detail_columns, _ = self._extract_columns_from_html(detail_button_html)
            if detail_columns:
                return {
                    "columns": detail_columns,
                    "public_data_detail": detail_keys,
                }

        public_data_pk = detail_keys.get("publicDataPk")
        if public_data_pk and public_data_detail_pk:
            hist_button_url = urljoin(
                self.source.base_url, "/tcs/dss/selectHistAndCsvData.do"
            )
            hist_button_html = self.get_text(
                f"{hist_button_url}?publicDataPk={public_data_pk}&publicDataDetailPk={public_data_detail_pk}"
            )
            hist_columns, _ = self._extract_columns_from_html(hist_button_html)
            if hist_columns:
                return {
                    "columns": hist_columns,
                    "public_data_detail": detail_keys,
                }

        return {
            "columns": landing_columns,
            "public_data_detail": detail_keys,
        }

    def _extract_columns_from_html(
        self, html_text: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        soup = BeautifulSoup(html_text, "lxml")
        detail_keys = self._extract_detail_keys(soup)
        table = self._pick_column_table(soup)
        if table is None:
            return [], detail_keys

        headers = [
            self._clean_header_text(th.get_text(" ", strip=True))
            for th in table.select("thead th")
        ]
        if not headers:
            first_row = table.find("tr")
            if first_row is not None:
                headers = [
                    self._clean_header_text(cell.get_text(" ", strip=True))
                    for cell in first_row.find_all(["th", "td"])
                ]

        columns: List[Dict[str, Any]] = []
        seen = set()
        for row in self._iter_data_rows(table):
            cells = [
                clean_text(cell.get_text(" ", strip=True)) or ""
                for cell in row.find_all(["th", "td"])
            ]
            if not cells:
                continue

            mapped: Dict[str, Any] = {}
            for idx, cell_value in enumerate(cells):
                if idx >= len(headers):
                    break
                header_key = self._map_header_to_key(headers[idx])
                if header_key is None:
                    continue
                value = clean_text(cell_value)
                if value in _COLUMN_EMPTY_VALUES:
                    continue
                mapped[header_key] = value

            column_name = clean_text(mapped.get("name"))
            if not column_name:
                continue

            dedup_key = (
                column_name.casefold(),
                (clean_text(mapped.get("description")) or "").casefold(),
                (clean_text(mapped.get("data_type")) or "").casefold(),
                (clean_text(mapped.get("max_length")) or "").casefold(),
                (clean_text(mapped.get("unit")) or "").casefold(),
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            columns.append(mapped)

        return columns, detail_keys

    def _extract_detail_keys(self, soup: BeautifulSoup) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for name in ("publicDataPk", "publicDataDetailPk"):
            node = soup.find("input", attrs={"name": name})
            value = clean_text(node.get("value") if node else None)
            if value:
                result[name] = value
        return result

    def _pick_column_table(self, soup: BeautifulSoup) -> Optional[Any]:
        for table in soup.find_all("table"):
            headers = [
                self._clean_header_text(th.get_text(" ", strip=True))
                for th in table.select("thead th")
            ]
            if not headers:
                first_row = table.find("tr")
                if first_row is not None:
                    headers = [
                        self._clean_header_text(cell.get_text(" ", strip=True))
                        for cell in first_row.find_all(["th", "td"])
                    ]
            if not headers:
                continue
            has_name = any(header.startswith("항목명") for header in headers)
            has_type = any(
                "데이터타입" in header or "자료형" in header for header in headers
            )
            if has_name and has_type:
                return table
        return None

    def _iter_data_rows(self, table: Any) -> List[Any]:
        tbody = table.find("tbody")
        if tbody is not None:
            return [row for row in tbody.find_all("tr")]
        rows = [row for row in table.find_all("tr")]
        return rows[1:] if len(rows) > 1 else []

    def _clean_header_text(self, value: Any) -> str:
        text = clean_text(value) or ""
        text = text.replace(" ", "").replace("\u00a0", "")
        return text

    def _map_header_to_key(self, header: str) -> Optional[str]:
        if header.startswith("항목명") and "영문" not in header:
            return "name"
        if header in {"항목설명", "설명"}:
            return "description"
        if header in {"데이터타입", "자료형"}:
            return "data_type"
        if header in {"최대길이", "길이"}:
            return "max_length"
        if header in {"단위", "측정단위"}:
            return "unit"
        return None

    def _extract_schema_dataset(
        self, schema_json: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not schema_json:
            return {}
        if isinstance(schema_json, dict):
            graph_nodes = schema_json.get("@graph")
            if isinstance(graph_nodes, list):
                for node in graph_nodes:
                    if not isinstance(node, dict):
                        continue
                    types = ensure_list(node.get("@type"))
                    if any(str(t).endswith("Dataset") for t in types):
                        return node
                return graph_nodes[0] if graph_nodes else {}
            return schema_json
        return {}

    def _schema_text(self, data: Dict[str, Any], key: str) -> Optional[str]:
        if key not in data:
            return None
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                text = self._schema_text({key: item}, key)
                if text:
                    return text
            return None
        if isinstance(value, dict):
            if value.get("@value"):
                return clean_text(value.get("@value"))
            if value.get("name"):
                return clean_text(value.get("name"))
            if value.get("@id"):
                return clean_text(value.get("@id"))
            return None
        return clean_text(value)

    def _schema_url(self, data: Dict[str, Any], key: str) -> Optional[str]:
        if key not in data:
            return None
        value = data.get(key)
        for item in ensure_list(value):
            if isinstance(item, dict):
                text = clean_text(item.get("@id") or item.get("url"))
            else:
                text = clean_text(item)
            if text and text.startswith("http"):
                return text
        return None

    def _schema_list(self, data: Dict[str, Any], key: str) -> List[str]:
        if key not in data:
            return []
        value = data.get(key)
        items: List[str] = []
        for item in ensure_list(value):
            if isinstance(item, dict):
                text = clean_text(
                    item.get("name") or item.get("@value") or item.get("@id")
                )
            else:
                text = clean_text(item)
            if text:
                items.extend(self._split_csv(text))
        return unique_strings(items)

    def _schema_org_name(self, data: Dict[str, Any], key: str) -> Optional[str]:
        value = data.get(key)
        for item in ensure_list(value):
            if isinstance(item, dict):
                name = clean_text(
                    item.get("name") or item.get("legalName") or item.get("@id")
                )
            else:
                name = clean_text(item)
            if name:
                return name
        return None

    def _split_csv(self, value: Any) -> List[str]:
        text = clean_text(value)
        if not text:
            return []
        delimiter = "," if "," in text else "/"
        return unique_strings(part.strip() for part in text.split(delimiter))

    def _build_resources(
        self, schema_dataset: Dict[str, Any], detail_url: str, kv: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        resources: List[Dict[str, Any]] = []
        distribution = (
            schema_dataset.get("distribution")
            if isinstance(schema_dataset, dict)
            else None
        )
        for item in ensure_list(distribution):
            if not isinstance(item, dict):
                continue
            resources.append(
                {
                    "title": clean_text(item.get("name")),
                    "download_url": clean_text(
                        item.get("contentUrl")
                        or item.get("url")
                        or item.get("downloadUrl")
                    ),
                    "encoding_format": clean_text(
                        item.get("encodingFormat") or item.get("fileFormat")
                    ),
                    "content_size": clean_text(item.get("contentSize")),
                    "description": clean_text(item.get("description")),
                }
            )
        if not resources:
            resources.append(
                {
                    "title": kv.get("File Name") or kv.get("Service"),
                    "download_url": detail_url,
                    "format": kv.get("File Extension") or kv.get("Extension"),
                    "content_size": None,
                }
            )
        return resources

    def _extract_dataset_size_bytes(
        self,
        *,
        schema_dataset: Dict[str, Any],
        resources: List[Dict[str, Any]],
        kv: Dict[str, str],
        detail_text: str,
    ) -> Optional[int]:
        schema_size = parse_bytes(self._schema_text(schema_dataset, "contentSize"))
        if schema_size:
            return schema_size

        total_size = 0
        matched = False
        for resource in resources:
            size_bytes = parse_bytes(resource.get("content_size"))
            if size_bytes:
                total_size += size_bytes
                matched = True
        if matched:
            return total_size

        for key in [
            "데이터 용량",
            "데이터크기",
            "용량",
            "구축량",
            "File Size",
            "Data Size",
            "Content Size",
        ]:
            size_bytes = self._extract_size_value(kv.get(key))
            if size_bytes:
                return size_bytes

        return self._extract_size_from_text(detail_text)

    def _extract_size_from_text(self, text: Any) -> Optional[int]:
        cleaned = clean_text(text)
        if not cleaned:
            return None
        match = _SIZE_PATTERN.search(cleaned)
        if not match:
            return None
        return parse_bytes(f"{match.group(1)} {match.group(2)}")

    def _extract_size_value(self, text: Any) -> Optional[int]:
        cleaned = clean_text(text)
        if not cleaned:
            return None
        match = _SIZE_VALUE_PATTERN.search(cleaned)
        if not match:
            return None
        return parse_bytes(f"{match.group(1)} {match.group(2)}")

    def _build_creators(
        self, schema_dataset: Dict[str, Any], kv: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        creators: List[Dict[str, Any]] = []
        for role_name in ["creator", "publisher", "provider"]:
            value = schema_dataset.get(role_name)
            for item in ensure_list(value):
                if not isinstance(item, dict):
                    name = clean_text(item)
                    if name:
                        creators.append({"name": name, "role": role_name})
                    continue
                creators.append(
                    {
                        "name": clean_text(
                            item.get("name") or item.get("legalName") or item.get("@id")
                        ),
                        "url": clean_text(item.get("url") or item.get("sameAs")),
                        "role": role_name,
                    }
                )
        if not creators:
            for key in [
                "Provider",
                "Department",
                "Collected by",
                "주관기관",
                "수행기관",
            ]:
                name = clean_text(kv.get(key))
                if name:
                    creators.append({"name": name, "role": key})
        return creators
