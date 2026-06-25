from __future__ import annotations

import logging
import threading
import time
from typing import Any

import psycopg
from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily
from psycopg.rows import dict_row


logger = logging.getLogger(__name__)


class DatasetCollectionMetricsCollector:
    def __init__(self, dsn: str, env: str, cache_ttl_seconds: int = 300) -> None:
        self._dsn = dsn
        self._env = env
        self._cache_ttl_seconds = cache_ttl_seconds
        self._snapshot_cache: dict[str, list[dict[str, Any]]] | None = None
        self._snapshot_cache_expires_at = 0.0
        self._cache_lock = threading.Lock()

    def collect(self):
        scrape_success = GaugeMetricFamily(
            "soda_dataset_metrics_scrape_success",
            "Whether dataset collection metrics scrape succeeded",
            labels=["env"],
        )

        if not self._dsn:
            scrape_success.add_metric([self._env], 0)
            yield scrape_success
            return

        try:
            snapshot = self._get_snapshot()
        except Exception:
            logger.exception("dataset collection metrics scrape failed")
            scrape_success.add_metric([self._env], 0)
            yield scrape_success
            return

        scrape_success.add_metric([self._env], 1)
        yield scrape_success

        running_metric = GaugeMetricFamily(
            "soda_dataset_collection_running",
            "Whether the latest run for a source is still RUNNING",
            labels=["env", "source"],
        )
        last_status_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_status",
            "One-hot encoded latest collection status by source",
            labels=["env", "source", "status"],
        )
        last_run_started_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_run_started_timestamp_seconds",
            "Latest dataset collection run start timestamp",
            labels=["env", "source"],
        )
        last_run_finished_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_run_finished_timestamp_seconds",
            "Latest dataset collection run finish timestamp",
            labels=["env", "source"],
        )
        last_duration_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_duration_seconds",
            "Latest dataset collection run duration in seconds",
            labels=["env", "source"],
        )
        last_collected_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_collected_total",
            "Collected count from latest dataset collection run",
            labels=["env", "source"],
        )
        last_upserted_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_upserted_total",
            "Upserted count from latest dataset collection run",
            labels=["env", "source"],
        )
        last_failed_metric = GaugeMetricFamily(
            "soda_dataset_collection_last_failed_total",
            "Failed count from latest dataset collection run",
            labels=["env", "source"],
        )
        source_active_metric = GaugeMetricFamily(
            "soda_dataset_source_active",
            "Whether a dataset source is active",
            labels=["env", "source", "collection_type"],
        )
        active_records_metric = GaugeMetricFamily(
            "soda_dataset_active_records_total",
            "Active dataset records currently stored per source",
            labels=["env", "source"],
        )
        error_records_metric = GaugeMetricFamily(
            "soda_dataset_error_records_total",
            "Dataset records currently marked ERROR per source",
            labels=["env", "source"],
        )
        total_size_metric = GaugeMetricFamily(
            "soda_dataset_active_total_size_bytes",
            "Total active dataset size bytes per source",
            labels=["env", "source"],
        )
        last_ingested_metric = GaugeMetricFamily(
            "soda_dataset_last_ingested_timestamp_seconds",
            "Latest dataset last_ingested_at timestamp per source",
            labels=["env", "source"],
        )
        recent_runs_metric = GaugeMetricFamily(
            "soda_dataset_collection_runs_last_24h",
            "Dataset collection runs in the last 24 hours by source and status",
            labels=["env", "source", "status"],
        )

        known_statuses = ("RUNNING", "SUCCESS", "PARTIAL_SUCCESS", "FAILED", "STOPPED")
        latest_rows = {row["source_code"]: row for row in snapshot["latest_runs"]}
        inventory_rows = {row["source_code"]: row for row in snapshot["inventory"]}

        for source_code, latest_row in latest_rows.items():
            source_labels = [self._env, source_code]
            collection_type = latest_row["collection_type"]
            source_active_metric.add_metric(
                [self._env, source_code, collection_type],
                1.0 if latest_row["is_active"] else 0.0,
            )

            running_metric.add_metric(
                source_labels,
                1.0 if latest_row.get("last_status") == "RUNNING" else 0.0,
            )

            last_status = latest_row.get("last_status")
            for status in known_statuses:
                last_status_metric.add_metric(
                    [self._env, source_code, status],
                    1.0 if last_status == status else 0.0,
                )

            self._add_metric_if_present(
                last_run_started_metric,
                source_labels,
                latest_row.get("last_run_started_at_epoch"),
            )
            self._add_metric_if_present(
                last_run_finished_metric,
                source_labels,
                latest_row.get("last_run_finished_at_epoch"),
            )
            self._add_metric_if_present(
                last_duration_metric,
                source_labels,
                latest_row.get("last_duration_seconds"),
            )

            last_collected_metric.add_metric(
                source_labels,
                float(latest_row.get("last_collected_count") or 0),
            )
            last_upserted_metric.add_metric(
                source_labels,
                float(latest_row.get("last_upserted_count") or 0),
            )
            last_failed_metric.add_metric(
                source_labels,
                float(latest_row.get("last_failed_count") or 0),
            )

            inventory_row = inventory_rows.get(source_code, {})
            active_records_metric.add_metric(
                source_labels,
                float(inventory_row.get("active_record_count") or 0),
            )
            error_records_metric.add_metric(
                source_labels,
                float(inventory_row.get("error_record_count") or 0),
            )
            total_size_metric.add_metric(
                source_labels,
                float(inventory_row.get("active_total_size_bytes") or 0),
            )
            self._add_metric_if_present(
                last_ingested_metric,
                source_labels,
                inventory_row.get("last_ingested_at_epoch"),
            )

        for row in snapshot["recent_runs"]:
            recent_runs_metric.add_metric(
                [self._env, row["source_code"], row["status"]],
                float(row["run_count"]),
            )

        yield running_metric
        yield last_status_metric
        yield last_run_started_metric
        yield last_run_finished_metric
        yield last_duration_metric
        yield last_collected_metric
        yield last_upserted_metric
        yield last_failed_metric
        yield source_active_metric
        yield active_records_metric
        yield error_records_metric
        yield total_size_metric
        yield last_ingested_metric
        yield recent_runs_metric

    def _add_metric_if_present(
        self,
        metric_family: GaugeMetricFamily,
        labels: list[str],
        value: Any,
    ) -> None:
        if value is None:
            return
        metric_family.add_metric(labels, float(value))

    def _get_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        if self._cache_ttl_seconds <= 0:
            return self._fetch_snapshot()

        now = time.monotonic()
        cached_snapshot = self._snapshot_cache
        if cached_snapshot is not None and now < self._snapshot_cache_expires_at:
            return cached_snapshot

        with self._cache_lock:
            now = time.monotonic()
            cached_snapshot = self._snapshot_cache
            if cached_snapshot is not None and now < self._snapshot_cache_expires_at:
                return cached_snapshot

            snapshot = self._fetch_snapshot()
            self._snapshot_cache = snapshot
            self._snapshot_cache_expires_at = now + self._cache_ttl_seconds
            return snapshot

    def _fetch_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with psycopg.connect(
            self._dsn,
            row_factory=dict_row,
            connect_timeout=5,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH latest_runs AS (
                      SELECT
                        ds.source_code,
                        ds.collection_type,
                        ds.is_active,
                        cd.status AS last_status,
                        EXTRACT(EPOCH FROM cd.run_started_at) AS last_run_started_at_epoch,
                        EXTRACT(EPOCH FROM cd.run_finished_at) AS last_run_finished_at_epoch,
                        EXTRACT(EPOCH FROM (COALESCE(cd.run_finished_at, NOW()) - cd.run_started_at)) AS last_duration_seconds,
                        cd.collected_count AS last_collected_count,
                        cd.upserted_count AS last_upserted_count,
                        cd.failed_count AS last_failed_count,
                        ROW_NUMBER() OVER (
                          PARTITION BY ds.id
                          ORDER BY cd.run_started_at DESC NULLS LAST, cd.id DESC NULLS LAST
                        ) AS rn
                      FROM dataset_sources ds
                      LEFT JOIN collection_datasets cd
                        ON cd.dataset_source_id = ds.id
                    )
                    SELECT
                      source_code,
                      collection_type,
                      is_active,
                      last_status,
                      last_run_started_at_epoch,
                      last_run_finished_at_epoch,
                      last_duration_seconds,
                      last_collected_count,
                      last_upserted_count,
                      last_failed_count
                    FROM latest_runs
                    WHERE rn = 1
                    ORDER BY source_code
                    """
                )
                latest_runs = list(cur.fetchall())

                cur.execute(
                    """
                    SELECT
                      ds.source_code,
                      COUNT(d.id) FILTER (WHERE d.status = 'ACTIVE') AS active_record_count,
                      COUNT(d.id) FILTER (WHERE d.status = 'ERROR') AS error_record_count,
                      COALESCE(SUM(d.dataset_size_bytes) FILTER (WHERE d.status = 'ACTIVE'), 0) AS active_total_size_bytes,
                      EXTRACT(EPOCH FROM MAX(d.last_ingested_at) FILTER (WHERE d.status = 'ACTIVE')) AS last_ingested_at_epoch
                    FROM dataset_sources ds
                    LEFT JOIN datasets d
                      ON d.dataset_source_id = ds.id
                    GROUP BY ds.source_code
                    ORDER BY ds.source_code
                    """
                )
                inventory = list(cur.fetchall())

                cur.execute(
                    """
                    SELECT
                      ds.source_code,
                      cd.status,
                      COUNT(*) AS run_count
                    FROM collection_datasets cd
                    JOIN dataset_sources ds
                      ON ds.id = cd.dataset_source_id
                    WHERE cd.run_started_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY ds.source_code, cd.status
                    ORDER BY ds.source_code, cd.status
                    """
                )
                recent_runs = list(cur.fetchall())

        return {
            "latest_runs": latest_runs,
            "inventory": inventory,
            "recent_runs": recent_runs,
        }


_REGISTERED = False


def register_dataset_collection_metrics(dsn: str, env: str) -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    REGISTRY.register(DatasetCollectionMetricsCollector(dsn=dsn, env=env))
    _REGISTERED = True
