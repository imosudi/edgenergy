import logging

logger = logging.getLogger(__name__)

APPLIANCE_SIGNATURES = {
    "fridge": {
        "min_power": 60.0,
        "max_power": 200.0,
        "min_delta": 50.0,
        "max_delta": 220.0,
        "name": "Refrigerator"
    },
    "microwave": {
        "min_power": 800.0,
        "max_power": 1600.0,
        "min_delta": 750.0,
        "max_delta": 1650.0,
        "name": "Microwave Oven"
    },
    "hvac": {
        "min_power": 1800.0,
        "max_power": 3500.0,
        "min_delta": 1700.0,
        "max_delta": 3600.0,
        "name": "HVAC System"
    }
}

def match_signature(delta_p: float, active_power: float) -> str:
    """
    Attempts to match a transient delta power and aggregate active power to a known appliance signature.
    Returns the appliance key (e.g. 'fridge', 'microwave', 'hvac') or None if unmatched.
    """
    abs_delta = abs(delta_p)
    
    # We check each signature to see if the delta matches
    # Since we can transition ON (positive delta) or OFF (negative delta)
    for app_id, sig in APPLIANCE_SIGNATURES.items():
        # Check if the power jump magnitude matches the signature's expected transient delta
        if sig["min_delta"] <= abs_delta <= sig["max_delta"]:
            logger.info(f"Signature match found: {app_id} (delta_p={delta_p:.1f}W)")
            return app_id
            
    return None
