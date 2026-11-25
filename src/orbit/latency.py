import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "outputs" / "orbit"

# Simulation assumptions
RAW_IMAGE_SIZE_MB = 100
INSIGHT_PACKET_SIZE_KB = 250
DOWNLINK_RATE_BPS = 10_000_000

GROUND_PROCESSING_SECONDS = 300
ONBOARD_PROCESSING_SECONDS = 60

WAIT_FOR_CONTACT_SECONDS = 1800


def calculate_latency():

    # Raw image and insight packet sizes
    raw_mb = RAW_IMAGE_SIZE_MB
    insight_kb = INSIGHT_PACKET_SIZE_KB

    raw_bytes = raw_mb * 1_000_000
    insight_bytes = insight_kb * 1_000

    # Downlink time calculations
    raw_downlink_seconds = (
        raw_bytes * 8 / DOWNLINK_RATE_BPS
    )

    insight_downlink_seconds = (
        insight_bytes * 8 / DOWNLINK_RATE_BPS
    )

    # Ground processing total latency
    ground_total_seconds = (
        WAIT_FOR_CONTACT_SECONDS
        + raw_downlink_seconds
        + GROUND_PROCESSING_SECONDS
    )

    # Onboard processing total latency
    onboard_total_seconds = (
        WAIT_FOR_CONTACT_SECONDS
        + insight_downlink_seconds
        + ONBOARD_PROCESSING_SECONDS
    )

    # Data reduction
    reduction_factor = raw_bytes / insight_bytes

    result = {
        "data_status": "SIMULATED",
        "assumption_label": "LATENCY VALUES ARE SIMULATION ASSUMPTIONS",

        "raw_MB": raw_mb,
        "insight_kB": insight_kb,

        "downlink_rate_bps": DOWNLINK_RATE_BPS,

        "raw_downlink_seconds": raw_downlink_seconds,
        "insight_downlink_seconds": insight_downlink_seconds,

        "ground_processing_seconds": GROUND_PROCESSING_SECONDS,
        "onboard_processing_seconds": ONBOARD_PROCESSING_SECONDS,

        "waiting_for_contact_seconds": WAIT_FOR_CONTACT_SECONDS,

        "ground_total_seconds": ground_total_seconds,
        "onboard_total_seconds": onboard_total_seconds,

        "reduction_factor": reduction_factor,

        "latency_improvement_seconds": (
            ground_total_seconds - onboard_total_seconds
        ),

        "latency_improvement_percent": (
            (ground_total_seconds - onboard_total_seconds)
            / ground_total_seconds * 100
        )
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "latency_result.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    print("\n--- FLOODSENTINEL LATENCY COMPARISON ---")

    print(f"Raw Image Size: {raw_mb:.2f} MB")
    print(f"Insight Packet Size: {insight_kb:.2f} KB")

    print(f"\nRaw Image Downlink: {raw_downlink_seconds:.2f} seconds")
    print(f"Insight Downlink: {insight_downlink_seconds:.2f} seconds")

    print(f"\nGround Processing: {GROUND_PROCESSING_SECONDS} seconds")
    print(f"Onboard Processing: {ONBOARD_PROCESSING_SECONDS} seconds")

    print(f"\nGround Total Latency: {ground_total_seconds:.2f} seconds")
    print(f"Onboard Total Latency: {onboard_total_seconds:.2f} seconds")

    print(f"\nData Reduction: {reduction_factor:.0f}x")
    print(
        f"Latency Improvement: "
        f"{result['latency_improvement_percent']:.2f}%"
    )

    print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    calculate_latency()