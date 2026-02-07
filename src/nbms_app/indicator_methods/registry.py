from __future__ import annotations

from nbms_app.indicator_methods.methods import (
    BinaryQuestionnaireMethod,
    BirdieApiConnectorMethod,
    CsvAggregationMethod,
    SpatialOverlayMethod,
)


METHOD_REGISTRY = {
    BinaryQuestionnaireMethod.key: BinaryQuestionnaireMethod(),
    CsvAggregationMethod.key: CsvAggregationMethod(),
    SpatialOverlayMethod.key: SpatialOverlayMethod(),
    BirdieApiConnectorMethod.key: BirdieApiConnectorMethod(),
}


def get_method(implementation_key):
    return METHOD_REGISTRY.get((implementation_key or "").strip())


def register_method(implementation_key):
    def _decorator(method_cls):
        METHOD_REGISTRY[(implementation_key or "").strip()] = method_cls()
        return method_cls

    return _decorator
