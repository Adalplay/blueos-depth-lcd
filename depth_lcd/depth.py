from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DepthSample:
    depth_m: float
    source: str


def depth_from_message(message, preferred_source: str = "AUTO") -> DepthSample | None:
    """Convert common ArduSub MAVLink messages into positive-down depth."""
    message_type = message.get_type()
    preferred_source = preferred_source.upper()

    if preferred_source not in ("AUTO", message_type):
        return None

    if message_type == "GLOBAL_POSITION_INT":
        # relative_alt is millimetres, positive upwards from the home surface.
        return DepthSample(max(0.0, -float(message.relative_alt) / 1000.0), message_type)

    if message_type == "LOCAL_POSITION_NED":
        # NED Z is positive down, in metres.
        return DepthSample(max(0.0, float(message.z)), message_type)

    if message_type == "VFR_HUD":
        # ArduSub reports altitude below the surface as a negative value.
        return DepthSample(max(0.0, -float(message.alt)), message_type)

    return None


def depth_from_mavlink2rest(payload: dict, preferred_source: str) -> DepthSample:
    """Encontra a mensagem desejada na árvore JSON fornecida pelo MAVLink2Rest."""
    candidates = (
        [preferred_source]
        if preferred_source != "AUTO"
        else ["GLOBAL_POSITION_INT", "VFR_HUD", "LOCAL_POSITION_NED"]
    )
    for vehicle in payload.get("vehicles", {}).values():
        for component in vehicle.get("components", {}).values():
            messages = component.get("messages", {})
            for source in candidates:
                entry = messages.get(source)
                if not entry:
                    continue
                message = entry.get("message", {})
                if source == "GLOBAL_POSITION_INT":
                    return DepthSample(
                        max(0.0, -float(message["relative_alt"]) / 1000.0), source
                    )
                if source == "VFR_HUD":
                    return DepthSample(max(0.0, -float(message["alt"])), source)
                if source == "LOCAL_POSITION_NED":
                    return DepthSample(max(0.0, float(message["z"])), source)
    raise LookupError(f"Mensagem {preferred_source} não encontrada")
