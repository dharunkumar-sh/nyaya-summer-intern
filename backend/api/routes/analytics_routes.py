"""
Analytics routes: GET /api/analytics/benchmark, GET /api/analytics/metrics.
"""
from flask import Blueprint
from api.responses import success_response
from services.analytics_service import analytics_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/benchmark", methods=["GET"])
def get_benchmark():
    """Returns system performance benchmarks, latency numbers, and KG density."""
    metrics = analytics_service.get_benchmark_metrics()
    return success_response(data=metrics, message="Retrieved benchmark metrics")


@analytics_bp.route("/metrics", methods=["GET"])
def get_metrics():
    """Alias endpoint for benchmark metrics."""
    metrics = analytics_service.get_benchmark_metrics()
    return success_response(data=metrics, message="Retrieved system metrics")


@analytics_bp.route("/dashboard", methods=["GET"])
def get_dashboard_summary():
    """Returns aggregated summary statistics for the main Overview Dashboard."""
    summary = analytics_service.get_dashboard_summary()
    return success_response(data=summary, message="Retrieved dashboard summary statistics")

