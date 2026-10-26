
import { useEffect, useState } from "react";
import {
  Activity,
  BrainCircuit,
  Radio,
  Users,
  MessageSquareText,
  RefreshCw,
  Play,
} from "lucide-react";

import "./App.css";

const RUN_ID = "df4762c8-3dca-4176-8200-1473f1092b98";

type Team = {
  team_id: string;
  pass_attempts: number;
  pass_completions: number;
  pass_completion_pct: number;
  shots: number;
  goals: number;
  xg: number;
};

type Analysis = {
  coach: string;
  broadcast: string;
  fan: string;
};

type Panel = "coach" | "broadcast" | "fan";

const PANELS: {
  id: Panel;
  label: string;
  icon: typeof Activity;
}[] = [
  {
    id: "coach",
    label: "Coach Intelligence",
    icon: BrainCircuit,
  },
  {
    id: "broadcast",
    label: "Broadcast Analysis",
    icon: Radio,
  },
  {
    id: "fan",
    label: "Fan Experience",
    icon: Users,
  },
];

function matchClock(seconds: number): string {
  const minute = Math.floor(seconds / 60);
  const second = Math.floor(seconds % 60);

  return (
    `${String(minute).padStart(2, "0")}:` +
    `${String(second).padStart(2, "0")}`
  );
}

export default function App() {
  const [time, setTime] = useState(5400);

  const [teams, setTeams] = useState<Team[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);

  const [panel, setPanel] = useState<Panel>("coach");

  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);

  const [error, setError] = useState("");

  const [fanLevel, setFanLevel] = useState("beginner");
  const [preferredTeam, setPreferredTeam] = useState("BLU");

  // Retrieve verified match statistics from Microsoft Fabric.
  useEffect(() => {
    const controller = new AbortController();

    async function loadStats() {
      setLoadingStats(true);
      setError("");
      setTeams([]);
      setAnalysis(null);

      try {
        const response = await fetch(
          `/api/v1/matches/${RUN_ID}/stats?as_of_second=${time}`,
          {
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(
            `Unable to retrieve match statistics (${response.status})`
          );
        }

        const data = await response.json();

        if (!controller.signal.aborted) {
          setTeams(data.teams ?? []);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to retrieve match statistics."
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingStats(false);
        }
      }
    }

    loadStats();

    return () => {
      controller.abort();
    };
  }, [time]);

  // Run the existing Coach -> Broadcast -> Fan workflow.
  async function runAnalysis() {
    setLoadingAI(true);
    setError("");
    setAnalysis(null);

    try {
      const response = await fetch(
        "/api/v1/intelligence/analyse",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            run_id: RUN_ID,
            as_of_second: time,
            fan_level: fanLevel,
            preferred_team: preferredTeam,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Unable to generate intelligence (${response.status})`
        );
      }

      const data: Analysis = await response.json();

      setAnalysis(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to generate match intelligence."
      );
    } finally {
      setLoadingAI(false);
    }
  }

  const red = teams.find((team) => team.team_id === "RED");
  const blu = teams.find((team) => team.team_id === "BLU");

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={24} />
          </div>

          <div>
            <strong>FSI</strong>
            <small>FOOTBALL SUPER INTELLIGENCE</small>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <div className="nav-active">
          <Activity size={18} />
          Match Centre
        </div>

        <div className="nav-item">
          <BrainCircuit size={18} />
          Intelligence
        </div>

        <div className="nav-item">
          <MessageSquareText size={18} />
          Commentary
        </div>

        <div className="sidebar-footer">
          Powered by Microsoft Fabric + Foundry
        </div>
      </aside>

      {/* Main Dashboard */}
      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">
              FSI / MATCH CENTRE
            </div>

            <h1>Football Intelligence</h1>

            <p>
              Explainable insights from synthetic football events.
            </p>
          </div>

          <span className="status">
            <span className="status-dot" />
            MATCH REPLAY
          </span>
        </header>

        {/* Error messages */}
        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {/* Match Scoreboard */}
        <section className="match-card">
          <div className="match-heading">
            <span>SYNTHETIC MATCH</span>
            <span className="clock">
              {matchClock(time)}
            </span>
          </div>

          <div className="scoreboard">
            <div className="team">
              <div className="team-badge red">
                R
              </div>
              <strong>RED</strong>
            </div>

            <div className="score">
              {red?.goals ?? "–"}
              <span> : </span>
              {blu?.goals ?? "–"}
            </div>

            <div className="team">
              <div className="team-badge blue">
                B
              </div>
              <strong>BLU</strong>
            </div>
          </div>

          {/* Match Time Selector */}
          <div className="timeline">
            <div className="timeline-head">
              <span>Match timeline</span>
              <strong>{matchClock(time)}</strong>
            </div>

            <input
              type="range"
              min="0"
              max="5400"
              step="30"
              value={time}
              onChange={(event) => {
                setTime(Number(event.target.value));
              }}
            />

            <div className="timeline-head muted">
              <span>00:00</span>
              <span>45:00</span>
              <span>90:00</span>
            </div>
          </div>
        </section>

        {/* Match Statistics */}
        <section className="stats-grid">
          <div className="stat-card">
            <span>SHOTS</span>
            <strong>
              {red?.shots ?? "–"}
              <i> vs </i>
              {blu?.shots ?? "–"}
            </strong>
          </div>

          <div className="stat-card">
            <span>EXPECTED GOALS (xG)</span>
            <strong>
              {red?.xg?.toFixed(2) ?? "–"}
              <i> vs </i>
              {blu?.xg?.toFixed(2) ?? "–"}
            </strong>
          </div>

          <div className="stat-card">
            <span>PASS ATTEMPTS</span>
            <strong>
              {red?.pass_attempts ?? "–"}
              <i> vs </i>
              {blu?.pass_attempts ?? "–"}
            </strong>
          </div>
        </section>

        {/* AI Intelligence */}
        <section className="intelligence-section">
          <div className="section-title">
            <div>
              <div className="eyebrow">
                MICROSOFT FOUNDRY
              </div>

              <h2>Match Intelligence</h2>
            </div>

            <button
              className="primary-btn"
              onClick={runAnalysis}
              disabled={
                loadingAI ||
                loadingStats ||
                teams.length === 0
              }
            >
              {loadingAI ? (
                <RefreshCw
                  size={16}
                  className="spin"
                />
              ) : (
                <Play size={16} />
              )}

              {loadingAI
                ? "Analysing..."
                : "Analyse Match"}
            </button>
          </div>

          {/* Fan Preferences */}
          <div className="preferences">
            <label>
              Fan level

              <select
                value={fanLevel}
                onChange={(event) =>
                  setFanLevel(event.target.value)
                }
              >
                <option value="beginner">
                  Beginner
                </option>

                <option value="enthusiast">
                  Enthusiast
                </option>

                <option value="advanced">
                  Advanced
                </option>
              </select>
            </label>

            <label>
              Preferred team

              <select
                value={preferredTeam}
                onChange={(event) =>
                  setPreferredTeam(event.target.value)
                }
              >
                <option value="RED">
                  RED
                </option>

                <option value="BLU">
                  BLU
                </option>
              </select>
            </label>
          </div>

          {/* Intelligence Tabs */}
          <div className="tabs">
            {PANELS.map(
              ({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setPanel(id)}
                  className={
                    panel === id
                      ? "tab active"
                      : "tab"
                  }
                >
                  <Icon size={17} />
                  {label}
                </button>
              )
            )}
          </div>

          {/* AI Output */}
          <div className="analysis-content">
            {loadingAI
              ? (
                "Retrieving verified intelligence and running the FSI agent workflow..."
              )
              : analysis
                ? analysis[panel]
                : (
                  "Select a match time and click Analyse Match to generate evidence-based football intelligence."
                )
            }
          </div>
        </section>

        <footer>
          {loadingStats
            ? "Loading Fabric statistics..."
            : "Data source: Microsoft Fabric Eventhouse"}
        </footer>
      </main>
    </div>
  );
}