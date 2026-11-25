import json
import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import brentq


# --------------------------------------------------
# PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = ROOT / "config" / "orbit.json"
OUTPUT_DIR = ROOT / "outputs" / "orbit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

SECONDS_PER_DAY = 86400
EARTH_ROTATION_RAD_S = 7.292115e-5


# --------------------------------------------------
# LOAD CONFIGURATION
# --------------------------------------------------

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

altitude_km = config["altitude_km"]
earth_radius_km = config["earth_radius_km"]
mu = config["earth_mu_m3_s2"]
J2 = config["earth_j2"]

eccentricity = config["orbit"]["eccentricity"]

station = config["ground_station"]

station_lat = math.radians(station["latitude_deg"])
station_lon = math.radians(station["longitude_deg"])


# --------------------------------------------------
# ORBIT CALCULATIONS
# --------------------------------------------------

a_km = earth_radius_km + altitude_km
a_m = a_km * 1000

p_m = a_m * (1 - eccentricity**2)

mean_motion = math.sqrt(mu / a_m**3)

orbital_period_s = (2 * math.pi) / mean_motion
orbital_period_min = orbital_period_s / 60

orbital_velocity_m_s = math.sqrt(mu / a_m)


# --------------------------------------------------
# SUN-SYNCHRONOUS INCLINATION
# --------------------------------------------------

target_nodal_precession = (
    2 * math.pi / (365.2422 * SECONDS_PER_DAY)
)


def nodal_precession(inclination_rad):
    return (
        -1.5
        * J2
        * mean_motion
        * (earth_radius_km * 1000 / p_m) ** 2
        * math.cos(inclination_rad)
    )


def inclination_equation(inclination_rad):
    return (
        nodal_precession(inclination_rad)
        - target_nodal_precession
    )


# Numerical solution, not a hardcoded inclination
inclination_rad = brentq(
    inclination_equation,
    math.radians(90.01),
    math.radians(179.99)
)

inclination_deg = math.degrees(inclination_rad)


# --------------------------------------------------
# SATELLITE PROPAGATION
# Simplified circular orbit model
# --------------------------------------------------

raan = math.radians(config["orbit"]["raan_deg"])

initial_anomaly = math.radians(
    config["orbit"]["initial_true_anomaly_deg"]
)

argument_perigee = math.radians(
    config["orbit"]["argument_of_perigee_deg"]
)

simulation_step = 60  # seconds

times = np.arange(
    0,
    SECONDS_PER_DAY + simulation_step,
    simulation_step
)

latitudes = []
longitudes = []
elevations = []
slant_ranges = []


# Ground station ECEF position (spherical Earth model)
station_radius_m = (
    earth_radius_km + station["altitude_m"] / 1000
) * 1000

station_x = (
    station_radius_m
    * math.cos(station_lat)
    * math.cos(station_lon)
)

station_y = (
    station_radius_m
    * math.cos(station_lat)
    * math.sin(station_lon)
)

station_z = station_radius_m * math.sin(station_lat)

station_ecef = np.array(
    [station_x, station_y, station_z]
)


for t in times:

    # Satellite orbital angle
    u = (
        initial_anomaly
        + argument_perigee
        + mean_motion * t
    )

    # Satellite position in orbital plane
    x_orbit = a_m * math.cos(u)
    y_orbit = a_m * math.sin(u)

    # Rotate orbital plane by inclination and RAAN
    x_eci = (
        x_orbit * math.cos(raan)
        - y_orbit * math.sin(raan) * math.cos(inclination_rad)
    )

    y_eci = (
        x_orbit * math.sin(raan)
        + y_orbit * math.cos(raan) * math.cos(inclination_rad)
    )

    z_eci = y_orbit * math.sin(inclination_rad)

    # Earth rotation: ECI to simplified ECEF
    theta = EARTH_ROTATION_RAD_S * t

    x_ecef = (
        x_eci * math.cos(theta)
        + y_eci * math.sin(theta)
    )

    y_ecef = (
        -x_eci * math.sin(theta)
        + y_eci * math.cos(theta)
    )

    z_ecef = z_eci

    satellite_ecef = np.array(
        [x_ecef, y_ecef, z_ecef]
    )

    # Satellite geocentric latitude/longitude
    radius = np.linalg.norm(satellite_ecef)

    latitude = math.degrees(
        math.asin(z_ecef / radius)
    )

    longitude = math.degrees(
        math.atan2(y_ecef, x_ecef)
    )

    # Ground station line-of-sight vector
    los = satellite_ecef - station_ecef

    slant_range = np.linalg.norm(los)

    # Convert line of sight to local East-North-Up
    east = (
        -math.sin(station_lon) * los[0]
        + math.cos(station_lon) * los[1]
    )

    north = (
        -math.sin(station_lat) * math.cos(station_lon) * los[0]
        -math.sin(station_lat) * math.sin(station_lon) * los[1]
        +math.cos(station_lat) * los[2]
    )

    up = (
        math.cos(station_lat) * math.cos(station_lon) * los[0]
        +math.cos(station_lat) * math.sin(station_lon) * los[1]
        +math.sin(station_lat) * los[2]
    )

    elevation = math.degrees(
        math.atan2(up, math.sqrt(east**2 + north**2))
    )

    latitudes.append(latitude)
    longitudes.append(longitude)
    elevations.append(elevation)
    slant_ranges.append(slant_range / 1000)


latitudes = np.array(latitudes)
longitudes = np.array(longitudes)
elevations = np.array(elevations)
slant_ranges = np.array(slant_ranges)


# --------------------------------------------------
# BENGALURU PASS DETECTION
# --------------------------------------------------

minimum_elevation = config["minimum_elevation_deg"]

visible = elevations >= minimum_elevation

passes = []

in_pass = False
pass_start = None

for i, is_visible in enumerate(visible):

    if is_visible and not in_pass:
        in_pass = True
        pass_start = i

    elif not is_visible and in_pass:

        pass_end = i - 1

        pass_indices = np.arange(pass_start, pass_end + 1)

        max_elevation_index = pass_indices[
            np.argmax(elevations[pass_indices])
        ]

        passes.append({
            "start_seconds": float(times[pass_start]),
            "end_seconds": float(times[pass_end]),
            "duration_seconds": float(
                times[pass_end] - times[pass_start]
            ),
            "maximum_elevation_deg": float(
                elevations[max_elevation_index]
            ),
            "maximum_elevation_time_seconds": float(
                times[max_elevation_index]
            ),
            "slant_range_at_max_elevation_km": float(
                slant_ranges[max_elevation_index]
            )
        })

        in_pass = False


# Handle pass extending to end of simulation
if in_pass:

    pass_end = len(times) - 1

    pass_indices = np.arange(pass_start, pass_end + 1)

    max_elevation_index = pass_indices[
        np.argmax(elevations[pass_indices])
    ]

    passes.append({
        "start_seconds": float(times[pass_start]),
        "end_seconds": float(times[pass_end]),
        "duration_seconds": float(
            times[pass_end] - times[pass_start]
        ),
        "maximum_elevation_deg": float(
            elevations[max_elevation_index]
        ),
        "maximum_elevation_time_seconds": float(
            times[max_elevation_index]
        ),
        "slant_range_at_max_elevation_km": float(
            slant_ranges[max_elevation_index]
        )
    })


# --------------------------------------------------
# GROUND TRACK PLOT
# --------------------------------------------------

plt.figure(figsize=(12, 6))

plt.plot(
    longitudes,
    latitudes,
    label="Satellite ground track"
)

plt.scatter(
    station["longitude_deg"],
    station["latitude_deg"],
    marker="*",
    s=150,
    label="Bengaluru ground station"
)

plt.xlabel("Longitude (degrees)")
plt.ylabel("Latitude (degrees)")
plt.title("FloodSentinel - 24 Hour Satellite Ground Track")

plt.xlim(-180, 180)
plt.ylim(-90, 90)

plt.grid(True)
plt.legend()
plt.tight_layout()

plot_path = OUTPUT_DIR / "orbit_groundtrack.png"

plt.savefig(plot_path, dpi=200)
plt.close()


# --------------------------------------------------
# OUTPUT JSON
# --------------------------------------------------

orbit_result = {
    "module": "orbit",
    "status": "ok",
    "data_status": "SIMULATED",
    "model": "simplified circular orbit with J2 SSO inclination",
    "altitude_km": altitude_km,
    "semi_major_axis_km": a_km,
    "mean_motion_rad_s": mean_motion,
    "mean_motion_rev_day": mean_motion * SECONDS_PER_DAY / (2 * math.pi),
    "period_seconds": orbital_period_s,
    "period_min": orbital_period_min,
    "orbital_velocity_m_s": orbital_velocity_m_s,
    "earth_j2": J2,
    "earth_radius_km": earth_radius_km,
    "p_km": p_m / 1000,
    "target_nodal_precession_rad_s": target_nodal_precession,
    "target_nodal_precession_deg_day": math.degrees(
        target_nodal_precession
    ) * SECONDS_PER_DAY,
    "sso_inclination_deg": inclination_deg,
    "ground_station": station,
    "minimum_elevation_deg": minimum_elevation,
    "passes_per_day": len(passes),
    "passes": passes,
    "ground_track": {
        "time_seconds": times.tolist(),
        "latitude_deg": latitudes.tolist(),
        "longitude_deg": longitudes.tolist()
    },
    "plot": "outputs/orbit/orbit_groundtrack.png",
    "assumptions": [
        "Circular orbit",
        "Simplified orbital propagation",
        "J2 used to calculate sun-synchronous inclination",
        "Earth rotation approximated as constant",
        "Spherical Earth model for ground station geometry",
        "No drag, higher-order gravity, or perturbation modelling",
        "Simulation is not flight-dynamics validation"
    ]
}


json_path = OUTPUT_DIR / "orbit_result.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(orbit_result, f, indent=4)


# --------------------------------------------------
# PRINT SUMMARY
# --------------------------------------------------

print("\n========== FLOODSENTINEL ORBIT SIMULATION ==========\n")

print(f"Altitude: {altitude_km:.2f} km")
print(f"Semi-major axis: {a_km:.2f} km")
print(f"Mean motion: {mean_motion:.8f} rad/s")
print(f"Orbital period: {orbital_period_min:.2f} minutes")
print(f"Orbital velocity: {orbital_velocity_m_s:.2f} m/s")

print(
    f"Calculated SSO inclination: "
    f"{inclination_deg:.4f} degrees"
)

print(
    f"Target nodal precession: "
    f"{math.degrees(target_nodal_precession) * SECONDS_PER_DAY:.6f} deg/day"
)

print(f"\nBengaluru passes found: {len(passes)}")

for index, satellite_pass in enumerate(passes, start=1):

    print(f"\nPass {index}")
    print(
        f"Duration: "
        f"{satellite_pass['duration_seconds'] / 60:.2f} minutes"
    )
    print(
        f"Maximum elevation: "
        f"{satellite_pass['maximum_elevation_deg']:.2f} degrees"
    )
    print(
        f"Slant range at max elevation: "
        f"{satellite_pass['slant_range_at_max_elevation_km']:.2f} km"
    )

print(f"\nJSON saved to: {json_path}")
print(f"Plot saved to: {plot_path}")

print("\nSimulation completed successfully.")