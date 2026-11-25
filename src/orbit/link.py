import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ORBIT_CONFIG = ROOT / "config" / "orbit.json"
OUTPUT_DIR = ROOT / "outputs" / "orbit"


def calculate_link_budget():
    with open(ORBIT_CONFIG, "r", encoding="utf-8") as file:
        config = json.load(file)

    link = config["link_budget"]
    frequency_hz = link["frequency_hz"]
    eirp_dbw = link["eirp_dbw"]
    receiver_gain_dbi = link["receiver_gain_dbi"]
    losses_db = link["total_losses_db"]
    system_temp_k = link["system_temperature_k"]
    bit_rate_bps = link["bit_rate_bps"]
    required_eb_n0_db = link["required_eb_n0_db"]

    # Calculate Free Space Path Loss (FSPL)
    # Distance will be taken from the orbit simulation
    orbit_file = OUTPUT_DIR / "orbit_result.json"

    with open(orbit_file, "r", encoding="utf-8") as file:
        orbit_data = json.load(file)

    passes = orbit_data.get("passes", [])

    if not passes:
        raise ValueError("No Bengaluru ground station passes found.")

    best_pass = max(passes, key=lambda p: p["maximum_elevation_deg"])
    slant_range_km = best_pass["slant_range_at_max_elevation_km"]

    # FSPL formula (frequency in Hz, distance in km)
    fspl_db = (
        20 * math.log10(slant_range_km)
        + 20 * math.log10(frequency_hz)
        - 147.55
    )

    received_power_dbw = (
        eirp_dbw
        + receiver_gain_dbi
        - fspl_db
        - losses_db
    )

    # Boltzmann constant in dBW/K/Hz
    boltzmann_db = -228.6

    cn0_dbhz = (
        received_power_dbw
        - 10 * math.log10(system_temp_k)
        - boltzmann_db
    )

    ebn0_db = cn0_dbhz - 10 * math.log10(bit_rate_bps)

    link_margin_db = ebn0_db - required_eb_n0_db

    # Data transmitted during the best pass
    contact_duration_seconds = best_pass["duration_seconds"]

    data_bits = bit_rate_bps * contact_duration_seconds
    data_mb = data_bits / (8 * 1_000_000)

    result = {
        "data_status": "SIMULATED",
        "assumption_label": "LINK BUDGET VALUES ARE ASSUMPTIONS",
        "frequency_hz": frequency_hz,
        "slant_range_km": slant_range_km,
        "fspl_db": fspl_db,
        "received_power_dbw": received_power_dbw,
        "cn0_dbhz": cn0_dbhz,
        "ebn0_db": ebn0_db,
        "required_ebn0_db": required_eb_n0_db,
        "link_margin_db": link_margin_db,
        "bit_rate_bps": bit_rate_bps,
        "contact_duration_seconds": contact_duration_seconds,
        "estimated_data_per_pass_mb": data_mb,
        "best_pass_max_elevation_deg": best_pass["maximum_elevation_deg"],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "link_result.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    print("\n--- FLOODSENTINEL LINK BUDGET ---")
    print(f"Slant Range: {slant_range_km:.2f} km")
    print(f"FSPL: {fspl_db:.2f} dB")
    print(f"Received Power: {received_power_dbw:.2f} dBW")
    print(f"C/N0: {cn0_dbhz:.2f} dB-Hz")
    print(f"Eb/N0: {ebn0_db:.2f} dB")
    print(f"Link Margin: {link_margin_db:.2f} dB")
    print(f"Estimated Data per Pass: {data_mb:.2f} MB")
    print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    calculate_link_budget()
    