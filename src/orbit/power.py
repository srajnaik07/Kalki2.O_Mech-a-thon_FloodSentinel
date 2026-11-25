import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ORBIT_CONFIG = ROOT / "config" / "orbit.json"
POWER_CONFIG = ROOT / "config" / "power.json"
OUTPUT_DIR = ROOT / "outputs" / "orbit"


def calculate_power():
    with open(ORBIT_CONFIG, "r", encoding="utf-8") as file:
        orbit_config = json.load(file)

    with open(POWER_CONFIG, "r", encoding="utf-8") as file:
        power_config = json.load(file)

    # Orbit parameters
    altitude_km = orbit_config["altitude_km"]
    earth_radius_km = orbit_config["earth_radius_km"]

    orbital_radius_km = earth_radius_km + altitude_km

    # Calculate orbital period
    mu = orbit_config["earth_mu_m3_s2"]
    orbital_radius_m = orbital_radius_km * 1000

    orbital_period_seconds = (
        2 * math.pi
        * math.sqrt(orbital_radius_m**3 / mu)
    )

    # Eclipse calculation (circular orbit, beta angle assumed 0 degrees)
    eclipse_angle = math.asin(earth_radius_km / orbital_radius_km)

    eclipse_fraction = eclipse_angle / math.pi
    sunlight_fraction = 1 - eclipse_fraction

    eclipse_seconds = orbital_period_seconds * eclipse_fraction
    sunlight_seconds = orbital_period_seconds * sunlight_fraction

    # Solar power generation
    panel_area = power_config["solar_panel_area_m2"]
    solar_irradiance = power_config["solar_irradiance_w_m2"]
    efficiency = power_config["solar_panel_efficiency"]
    losses = power_config["power_system_loss_fraction"]

    solar_power_w = (
        panel_area
        * solar_irradiance
        * efficiency
        * (1 - losses)
    )

    sunlight_average_power_w = solar_power_w * sunlight_fraction

    # Satellite load
    bus_power = power_config["bus_power_w"]
    payload_power = power_config["payload_power_w"]
    compute_power = power_config["onboard_compute_power_w"]

    total_load_w = bus_power + payload_power + compute_power

    # Battery parameters
    battery_capacity_wh = power_config["battery_capacity_wh"]
    initial_soc = power_config["initial_battery_soc_percent"]

    initial_energy_wh = battery_capacity_wh * initial_soc / 100

    simulation_hours = power_config["simulation_duration_hours"]

    # Average energy balance
    generated_energy_wh = sunlight_average_power_w * simulation_hours
    consumed_energy_wh = total_load_w * simulation_hours

    net_energy_wh = generated_energy_wh - consumed_energy_wh

    final_energy_wh = initial_energy_wh + net_energy_wh

    # Limit battery energy between 0 and capacity
    final_energy_wh = max(
        0,
        min(battery_capacity_wh, final_energy_wh)
    )

    final_soc = (final_energy_wh / battery_capacity_wh) * 100

    result = {
        "data_status": "SIMULATED",
        "assumption_label": power_config["assumption_label"],
        "orbital_period_seconds": orbital_period_seconds,
        "eclipse_fraction": eclipse_fraction,
        "sunlight_fraction": sunlight_fraction,
        "eclipse_duration_seconds": eclipse_seconds,
        "sunlight_duration_seconds": sunlight_seconds,
        "solar_power_w": solar_power_w,
        "sunlight_average_power_w": sunlight_average_power_w,
        "total_load_power_w": total_load_w,
        "initial_battery_energy_wh": initial_energy_wh,
        "generated_energy_wh": generated_energy_wh,
        "consumed_energy_wh": consumed_energy_wh,
        "net_energy_wh": net_energy_wh,
        "final_battery_energy_wh": final_energy_wh,
        "initial_battery_soc_percent": initial_soc,
        "final_battery_soc_percent": final_soc,
        "simulation_duration_hours": simulation_hours,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "power_result.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    print("\n--- FLOODSENTINEL POWER & ECLIPSE MODEL ---")
    print(f"Orbital Period: {orbital_period_seconds / 60:.2f} minutes")
    print(f"Eclipse Duration: {eclipse_seconds / 60:.2f} minutes")
    print(f"Sunlight Duration: {sunlight_seconds / 60:.2f} minutes")
    print(f"Eclipse Fraction: {eclipse_fraction * 100:.2f}%")
    print(f"Solar Power: {solar_power_w:.2f} W")
    print(f"Satellite Load: {total_load_w:.2f} W")
    print(f"Initial Battery SOC: {initial_soc:.2f}%")
    print(f"Final Battery SOC: {final_soc:.2f}%")
    print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    calculate_power()