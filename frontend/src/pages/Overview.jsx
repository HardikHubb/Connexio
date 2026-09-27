import { useEffect, useState } from "react";
import { getCaseNetwork, getCases } from "../api/client";

export default function Overview({
  selectedCaseId,
  onSelectCase,
  onOpenNetwork,
}) {
  const [cases, setCases] = useState([]);
  const [network, setNetwork] = useState(null);

  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingNetwork, setLoadingNetwork] = useState(false);

  const [error, setError] = useState("");

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (!selectedCaseId) {
      setNetwork(null);
      return;
    }

    loadNetwork(selectedCaseId);
  }, [selectedCaseId]);

  async function loadCases() {
    try {
      setError("");
      setLoadingCases(true);

      const data = await getCases();

      setCases(data);

      if (data.length > 0 && !selectedCaseId) {
        onSelectCase(data[0].case_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCases(false);
    }
  }

  async function loadNetwork(caseId) {
    try {
      setError("");
      setLoadingNetwork(true);

      const data = await getCaseNetwork(caseId);

      setNetwork(data);
    } catch (err) {
      setError(err.message);
      setNetwork(null);
    } finally {
      setLoadingNetwork(false);
    }
  }

  const selectedCase = cases.find(
    (item) => item.case_id === selectedCaseId
  );

  return (
    <main className="main-content">
      <header className="topbar">
        <div>
          <div className="eyebrow">INVESTIGATION WORKSPACE</div>

          <h1>Overview</h1>

         
        </div>

        <div className="case-selector">
          <span className="case-selector-label">
            ACTIVE INVESTIGATION
          </span>

          <select
            value={selectedCaseId || ""}
            onChange={(event) =>
              onSelectCase(event.target.value)
            }
          >
            {loadingCases && (
              <option value="">Loading cases...</option>
            )}

            {!loadingCases && cases.length === 0 && (
              <option value="">No investigations</option>
            )}

            {cases.map((item) => (
              <option
                key={item.case_id}
                value={item.case_id}
              >
                {item.name} · #{item.case_id}
              </option>
            ))}
          </select>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Backend connection error</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="hero-panel">
        <div>
          <div className="panel-kicker">
            ACTIVE INVESTIGATION
          </div>

          <h2>
            {selectedCase?.name || "No investigation selected"}
          </h2>

          <p>
            {selectedCase
              ? `Case ${selectedCase.case_id} is connected to the investigation graph.`
              : "Create an investigation and add source records to begin."}
          </p>
        </div>

        <button
          className="primary-button"
          onClick={onOpenNetwork}
          disabled={!selectedCaseId}
        >
          Open Network
          <span>→</span>
        </button>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Sources"
          value={
            selectedCase
              ? selectedCase.source_count
              : "—"
          }
          loading={loadingCases}
        />

        <StatCard
          label="Entities"
          value={network ? network.node_count : "—"}
          loading={loadingNetwork}
        />

        <StatCard
          label="Relationships"
          value={network ? network.edge_count : "—"}
          loading={loadingNetwork}
        />

        <StatCard
          label="Case ID"
          value={selectedCaseId || "—"}
          loading={false}
        />
      </section>

      <section className="overview-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-kicker">NETWORK STATUS</div>
              <h3>Knowledge graph</h3>
            </div>

            <span className="live-badge">
              <span />
              LIVE
            </span>
          </div>

          {loadingNetwork ? (
            <div className="empty-state">
              Loading investigation network...
            </div>
          ) : network ? (
            <div className="network-summary">
              <div className="network-number">
                {network.node_count}
              </div>

              <div>
                <div className="network-title">
                  entities connected to this investigation
                </div>

                <div className="network-meta">
                  {network.edge_count} observed relationships
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              Select an investigation to inspect its network.
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-kicker">DATA SOURCES</div>
              <h3>Investigation records</h3>
            </div>
          </div>

          {selectedCase ? (
            <div className="source-list">
              <SourceRow
                label="Case"
                value={`#${selectedCase.case_id}`}
              />

              <SourceRow
                label="Registered sources"
                value={`${selectedCase.source_count}`}
              />

              <SourceRow
                label="Graph status"
                value="Connected"
              />
            </div>
          ) : (
            <div className="empty-state">
              No investigation selected.
            </div>
          )}
        </div>
      </section>

      <div className="prototype-note">
        <span>ⓘ</span>

        <span>
          Prototype data is synthetic. The interface displays
          information retrieved from the FastAPI and Neo4j-backed
          investigation system.
        </span>
      </div>
    </main>
  );
}

function StatCard({ label, value, loading }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>

      <div className="stat-value">
        {loading ? "…" : value}
      </div>
    </div>
  );
}

function SourceRow({ label, value }) {
  return (
    <div className="source-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}