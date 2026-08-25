"""Shared device-info helper for PiggyTask entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def child_device_info(child_id: str, child_name: str) -> DeviceInfo:
    """Build the DeviceInfo grouping all entities for one child."""
    return DeviceInfo(
        identifiers={(DOMAIN, child_id)},
        name=f"PiggyTask – {child_name}",
        manufacturer="PiggyTask",
        model="Child",
        configuration_url="https://app.piggytask.de",
    )
