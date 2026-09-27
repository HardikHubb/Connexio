import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { getCaseNetwork, getEntity } from "../api/client";

function getNodeId(node) {
  return String(
    node.id ||
      node.canonical_id ||
      node.number ||
      node.account_number ||
      node.registration_number ||
      node.name ||
      node.value
  );
}

function getNodeLabel(node) {
  return (
    node.label ||
    node.name ||
    node.number ||
    node.account_number ||
    node.registration_number ||
    node.value ||
    "Unknown"
  );
}

function getNodeType(node) {
  if (node.entity_type) {
    return node.entity_type;
  }

  if (node.labels && node.labels.length > 0) {
    return node.labels[node.labels.length - 1].toUpperCase();
  }

  return "ENTITY";
}

function getEndpointId(endpoint) {
  if (typeof endpoint === "string") {
    return endpoint;
  }

  if (endpoint && typeof endpoint === "object") {
    return getNodeId(endpoint);
  }

  return null;
}

function getEntityValue(properties) {
  return (
    properties.registration_number ||
    properties.number ||
    properties.account_number ||
    properties.name ||
    properties.normalized_value ||
    properties.aliases?.[0] ||
    "Unknown"
  );
}

export default function Network({ caseId = "101" }) {
  const graphContainerRef = useRef(null);
  const graphRef = useRef(null);

  const [network, setNetwork] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [graphSize, setGraphSize] = useState({
    width: 800,
    height: 600,
  });

  useEffect(() => {
    const container = graphContainerRef.current;

    if (!container) {
      return undefined;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];

      if (!entry) {
        return;
      }

      const width = Math.floor(entry.contentRect.width);
      const height = Math.floor(entry.contentRect.height);

      if (width > 0 && height > 0) {
        setGraphSize({
          width,
          height,
        });
      }
    });

    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadNetwork() {
      try {
        setLoading(true);
        setError("");
        setSelectedNode(null);
        setSelectedEntity(null);

        const data = await getCaseNetwork(caseId);

        if (!cancelled) {
          setNetwork(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.message || "Failed to load investigation network."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadNetwork();

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  async function handleNodeClick(node) {
    setSelectedNode(node);
    setSelectedEntity(null);

    const entityId = getNodeId(node);

    try {
      const entity = await getEntity(entityId);

      setSelectedEntity(entity);
    } catch (err) {
      console.error("Failed to load entity:", err);
    }
  }

  if (loading) {
    return (
      <div className="network-page">
        <div className="network-loading">
          Loading investigation network...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="network-page">
        <div className="network-error">
          {error}
        </div>
      </div>
    );
  }

  if (!network) {
    return (
      <div className="network-page">
        <div className="network-error">
          No network data available.
        </div>
      </div>
    );
  }

  const nodes = (network.nodes || []).map((node) => {
    const properties = node.properties || {};

    const flattenedNode = {
      ...node,
      ...properties,
    };

    return {
      ...flattenedNode,
      id: getNodeId(flattenedNode),
      label: getNodeLabel(flattenedNode),
    };
  });

  const nodeIds = new Set(
    nodes.map((node) => node.id)
  );

  const links = (network.edges || [])
    .map((edge) => {
      const source = getEndpointId(
        edge.source ?? edge.source_id
      );

      const target = getEndpointId(
        edge.target ?? edge.target_id
      );

      return {
        ...edge,
        source,
        target,
        label:
          edge.relationship_type ||
          edge.type ||
          edge.label ||
          "RELATED",
      };
    })
    .filter(
      (link) =>
        link.source &&
        link.target &&
        nodeIds.has(link.source) &&
        nodeIds.has(link.target)
    );

  const graphData = {
    nodes,
    links,
  };

  const selectedProperties =
    selectedEntity?.properties || {};

  const selectedValue =
    selectedNode?.label ||
    getEntityValue(selectedProperties);

  return (
    <div className="network-page">
      <header className="network-header">
        <div>
          <div className="network-eyebrow">
            INVESTIGATION NETWORK
          </div>

          <h1>Case {caseId}</h1>

          <div className="network-stats">
            <span>
              {nodes.length} entities
            </span>

            <span>
              {links.length} relationships
            </span>
          </div>
        </div>
      </header>

      <div className="network-workspace">
        <section
          className="graph-panel"
          ref={graphContainerRef}
        >
          <ForceGraph2D
            ref={graphRef}
            width={graphSize.width}
            height={graphSize.height}
            graphData={graphData}
            backgroundColor="#0d1014"

            nodeLabel={(node) =>
              `${getNodeType(node)} — ${node.label}`
            }

            nodeColor={(node) => {
              const type = getNodeType(node);

              if (type === "PERSON") {
                return "#e5e7eb";
              }

              if (type === "PHONE") {
                return "#60a5fa";
              }

              if (type === "ACCOUNT") {
                return "#34d399";
              }

              if (type === "VEHICLE") {
                return "#f59e0b";
              }

              if (type === "LOCATION") {
                return "#a78bfa";
              }

              if (type === "ORGANIZATION") {
                return "#f472b6";
              }

              return "#cbd5e1";
            }}

            nodeRelSize={6}

            linkColor={() =>
              "rgba(130, 138, 150, 0.55)"
            }

            linkWidth={1.5}

            linkDirectionalArrowLength={5}

            linkDirectionalArrowRelPos={1}

            onNodeClick={handleNodeClick}

            cooldownTicks={180}

            warmupTicks={40}

            d3AlphaDecay={0.04}

            d3VelocityDecay={0.35}

            onEngineStop={() => {
              if (graphRef.current) {
                graphRef.current.zoomToFit(
                  700,
                  70
                );
              }
            }}
          />

          <div className="graph-toolbar">
            <button
              type="button"
              onClick={() => {
                if (graphRef.current) {
                  graphRef.current.zoomToFit(
                    500,
                    70
                  );
                }
              }}
            >
              Fit graph
            </button>
          </div>
        </section>

        <aside className="network-detail-panel">
          {selectedNode ? (
            <>
              <div className="detail-eyebrow">
                SELECTED ENTITY
              </div>

              <h2>
                {selectedValue}
              </h2>

              <div className="detail-type">
                {getNodeType(selectedNode)}
              </div>

              {selectedEntity ? (
                <div className="detail-content">

                  <div className="detail-row">
                    <span>
                      Canonical ID
                    </span>

                    <strong>
                      {selectedProperties.canonical_id ||
                        selectedEntity.id ||
                        "—"}
                    </strong>
                  </div>

                  <div className="detail-row">
                    <span>
                      Value
                    </span>

                    <strong>
                      {getEntityValue(
                        selectedProperties
                      )}
                    </strong>
                  </div>

                  <div className="detail-row">
                    <span>
                      Case
                    </span>

                    <strong>
                      {selectedProperties.case_id ||
                        caseId}
                    </strong>
                  </div>

                  <div className="detail-row">
                    <span>
                      Mentions
                    </span>

                    <strong>
                      {selectedProperties.mention_count ??
                        "—"}
                    </strong>
                  </div>

                  {Array.isArray(
                    selectedProperties.aliases
                  ) &&
                    selectedProperties.aliases.length >
                      0 && (
                      <div className="detail-section">
                        <div className="detail-section-title">
                          Aliases
                        </div>

                        {selectedProperties.aliases.map(
                          (alias) => (
                            <div
                              className="source-chip"
                              key={alias}
                            >
                              {alias}
                            </div>
                          )
                        )}
                      </div>
                    )}

                  {Array.isArray(
                    selectedProperties.source_ids
                  ) &&
                    selectedProperties.source_ids.length >
                      0 && (
                      <div className="detail-section">
                        <div className="detail-section-title">
                          Sources
                        </div>

                        {selectedProperties.source_ids.map(
                          (sourceId) => (
                            <div
                              className="source-chip"
                              key={sourceId}
                            >
                              {sourceId}
                            </div>
                          )
                        )}
                      </div>
                    )}
                </div>
              ) : (
                <div className="detail-loading">
                  Loading entity details...
                </div>
              )}
            </>
          ) : (
            <div className="detail-empty">
              <div className="detail-eyebrow">
                ENTITY DETAILS
              </div>

              <h2>
                Select an entity
              </h2>

              <p>
                Click any node in the investigation
                network to inspect its details and
                source references.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}