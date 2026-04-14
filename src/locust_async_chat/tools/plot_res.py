"""Plot load test results: users vs latency."""

from pathlib import Path

import matplotlib.pyplot as plt


def plot_loadtest_results(
    median_data: dict[int, float],
    p95_data: dict[int, float],
    avg_messages_data: dict[int, float],
    april_01_median_data: dict[int, float],
    april_01_p95_data: dict[int, float],
    *,
    title: str = "Load Test Results",
    output_path: str | Path | None = None,
) -> None:
    """Plot load test results with users on x-axis and latency on y-axis.

    Args:
        median_data: Dict mapping number of users -> median latency in seconds.
        p95_data: Dict mapping number of users -> 95th percentile latency in seconds.
        avg_messages_data: Dict mapping number of users -> avg messages sent per user.
        title: Chart title.
        output_path: If set, save the figure to this path.
    """
    users = list(median_data.keys())
    median_seconds = list(median_data.values()) if median_data else []
    p95_seconds = list(p95_data.values()) if p95_data else []
    avg_messages = list(avg_messages_data.values()) if avg_messages_data else []

    fig, ax = plt.subplots(figsize=(10, 6))

    if median_seconds:
        ax.plot(
            users,
            median_seconds,
            marker="o",
            linewidth=2.5,
            markersize=8,
            color="#2563EB",
            label="Mar W3 Median",
        )
    if p95_seconds:
        ax.plot(
            users,
            p95_seconds,
            marker="s",
            linewidth=2.5,
            markersize=8,
            color="#DC2626",
            label="Mar W3 P95",
        )
    if avg_messages:
        ax.plot(
            users,
            avg_messages,
            marker="^",
            linewidth=2,
            markersize=8,
            color="#059669",
            label="Mar W3 Avg Msgs/User",
        )
    if april_01_median_data:
        ax.plot(
            list(april_01_median_data.keys()),
            list(april_01_median_data.values()),
            marker="D",
            linewidth=2.5,
            markersize=8,
            linestyle="--",
            color="#60A5FA",
            label="Apr W1 Median",
        )
    if april_01_p95_data:
        ax.plot(
            list(april_01_p95_data.keys()),
            list(april_01_p95_data.values()),
            marker="X",
            linewidth=2.5,
            markersize=8,
            linestyle="--",
            color="#F87171",
            label="Apr W1 P95",
        )

    all_users = sorted(
        set(users) | set(april_01_median_data.keys()) | set(april_01_p95_data.keys())
    )
    ax.set_xlabel("Number of Users")
    ax.set_ylabel("Latency (seconds)")
    ax.set_title(title)
    ax.set_xticks(all_users)
    ax.grid(True, alpha=0.3)

    lines, labels = ax.get_legend_handles_labels()
    ax.legend(lines, labels)

    if output_path:
        save_path = Path(output_path)
        if not save_path.is_absolute():
            save_path = Path(__file__).resolve().parent / save_path

        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {save_path}")

    plt.show()


if __name__ == "__main__":
    # --- Paste your data here: {users: latency_seconds} ---
    # March week 03
    march_03_median_data = {
        1: 13.3,
        10: 13.5,
        20: 13.6,
        30: 13.0,
        40: 15.0,
        50: 16.5,
        60: 17.0,
        # 70: 19.0,
        # 80: 20.0,
        # 90: 21.0,
        # 100: 22.0,
        # 110: 26.0,
        # 120: 35.0,
    }

    march_03_p95_data = {
        1: 19.0,
        10: 21.25,
        20: 22.33,
        30: 23.0,
        40: 23.0,
        50: 22.5,
        60: 23.0,
        # 70: 25.5,
        # 80: 28.0,
        # 90: 29.0,
        # 100: 30.0,
        # 110: 35.0,
        # 120: 41.0,
    }

    march_03_avg_messages_data = {
        1: 7.0,
        10: 4.0,
        20: 4.76,
        30: 4.45,
        40: 4.76,
        50: 3.59,
        60: 4.10,
        70: 2.73,
        80: 2.38,
        90: 1.84,
        100: 1.84,
        110: 1.27,
        120: 1.20,
    }

    # April week 01
    april_01_median_data = {
        1: 10.0,
        30: 11.0,
        40: 11.0,
        60: 22.0,
    }

    april_01_p95_data = {
        1: 14.0,
        30: 16.0,
        40: 13.0,
        60: 27.0,
    }

    # --- Run the plot ---
    plot_loadtest_results(
        median_data=march_03_median_data,
        p95_data=march_03_p95_data,
        avg_messages_data={},
        april_01_median_data=april_01_median_data,
        april_01_p95_data=april_01_p95_data,
        title="Load Test: Users vs Latency",
        output_path="loadtest_results_wk3.png",  # set to None to skip saving
    )
