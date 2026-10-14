from .detector import (
    detect_frame,
    is_demo_mode,
    is_ai_active,
    is_ai_offline,
    get_ai_mode,
    get_model_classes,
    get_inference_device,
    get_confidence_threshold,
    get_model_info,
    load_model,
    get_model_capabilities,
    enrich_detections,
    classify_event,
    SUPPORTED_EVENT_TYPES,
)

from .risk_engine import (
    calculate_risk,
    get_risk_level,
    get_risk_color,
    get_risk_description,
    get_alert_cooldown_manager,
    RISK_LEVELS,
)

from .alert_service import (
    generate_alert,
    list_alerts,
    get_alert,
    acknowledge,
    resolve,
    delete,
    clear_all,
    get_summary,
    get_detection_stats,
    get_analytics_data,
    get_risk_trend,
    get_alert_counts,
)

from .storage import (
    store_event,
    get_detection_history,
    get_connection,
    init_db,
)
