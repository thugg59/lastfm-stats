
// =========================
// Data loading
// =========================

async function loadData(file) {
    const response = await fetch(`data/${file}`);

    if (!response.ok) {
        throw new Error(`Failed to load ${file}`);
    }

    return response.json();
}


// =========================
// Statistics
// =========================

function updateStatistics(overview) {
    document.getElementById("total-scrobbles").textContent =
        Number(overview.total_scrobbles).toLocaleString();

    document.getElementById("unique-artists").textContent =
        Number(overview.unique_artists).toLocaleString();

    document.getElementById("top-artist").textContent =
        overview.top_artist ?? "—";

    document.getElementById("top-track").textContent =
        overview.top_track
            ? `${overview.top_track_artist} — ${overview.top_track}`
            : "—";
}


// =========================
// Charts
// =========================

function createTopArtistsChart(data) {
    // SQL already limits this data to the top 10 artists.
    const labels = data.map(row => row.artist);
    const values = data.map(row => Number(row.play_count));

    new Chart(document.getElementById("top-artists-chart"), {
        type: "bar",

        data: {
            labels: labels,

            datasets: [{
                label: "Scrobbles",
                data: values
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                x: {
                    ticks: {
                        autoSkip: false
                    }
                },

                y: {
                    beginAtZero: true
                }
            }
        }
    });
}


function createTopTracksChart(data) {
    // SQL already limits this data to the top 10 tracks.
    const labels = data.map(
        row => `${row.artist} — ${row.track}`
    );

    const values = data.map(
        row => Number(row.play_count)
    );

    new Chart(document.getElementById("top-tracks-chart"), {
        type: "bar",

        data: {
            labels: labels,

            datasets: [{
                label: "Scrobbles",
                data: values
            }]
        },

        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}


function createYearlyListeningChart(data) {
    const labels = data.map(row => String(row.year));
    const values = data.map(row => Number(row.scrobble_count));

    new Chart(document.getElementById("yearly-listening-chart"), {
        type: "bar",

        data: {
            labels: labels,

            datasets: [{
                label: "Scrobbles",
                data: values
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}


function createMonthlyListeningChart(data) {
    // "2008-03-01" -> "2008-03"
    const labels = data.map(row => String(row.month).slice(0, 7));
    const values = data.map(row => Number(row.scrobble_count));

    new Chart(document.getElementById("monthly-listening-chart"), {
        type: "line",

        data: {
            labels: labels,

            datasets: [{
                label: "Scrobbles",
                data: values,
                tension: 0.2,
                pointRadius: 0
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}


function createHourlyListeningChart(data) {
    const labels = data.map(
        row => `${String(row.hour_of_day).padStart(2, "0")}:00`
    );

    const values = data.map(
        row => Number(row.scrobble_count)
    );

    new Chart(document.getElementById("hourly-listening-chart"), {
        type: "bar",

        data: {
            labels: labels,

            datasets: [{
                label: "Scrobbles",
                data: values
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}


// =========================
// Initialize dashboard
// =========================

async function initializeDashboard() {
    try {
        const [
            overviewRows,
            topArtists,
            topTracks,
            yearlySummary,
            monthlySummary,
            hourlyListening
        ] = await Promise.all([
            loadData("overview.json"),
            loadData("top_artists.json"),
            loadData("top_tracks.json"),
            loadData("yearly_summary.json"),
            loadData("monthly_summary.json"),
            loadData("hourly_listening_pattern.json")
        ]);

        updateStatistics(overviewRows[0]);

        createTopArtistsChart(topArtists);
        createTopTracksChart(topTracks);
        createYearlyListeningChart(yearlySummary);
        createMonthlyListeningChart(monthlySummary);
        createHourlyListeningChart(hourlyListening);

    } catch (error) {
        console.error("Failed to initialize dashboard:", error);
    }
}


initializeDashboard();

