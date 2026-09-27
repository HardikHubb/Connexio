import { useState } from "react";
import { createCase } from "../api/client";

export default function CreateInvestigation({
  onCreated,
  onCancel,
}) {
  const [name, setName] = useState("");
  const [caseId, setCaseId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedCaseId = caseId.trim();

    if (!trimmedName) {
      setError("Investigation name is required.");
      return;
    }

    try {
      setError("");
      setLoading(true);

      const payload = {
        name: trimmedName,
      };

      if (trimmedCaseId) {
        payload.case_id = trimmedCaseId;
      }

      const createdCase = await createCase(payload);

      onCreated(createdCase);
    } catch (err) {
      setError(err.message || "Failed to create investigation.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="main-content">
      <div className="create-investigation">
        <div className="eyebrow">NEW INVESTIGATION</div>

        <h1>Create Investigation</h1>

        <p className="page-description">
          Create an investigation and prepare it for source
          records and network analysis.
        </p>

        <form
          className="create-investigation-form"
          onSubmit={handleSubmit}
        >
          <div className="form-field">
            <label htmlFor="investigation-name">
              Investigation name
            </label>

            <input
              id="investigation-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Operation Nexus"
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="form-field">
            <label htmlFor="case-id">
              Case ID
              <span className="optional-label">Optional</span>
            </label>

            <input
              id="case-id"
              type="text"
              value={caseId}
              onChange={(event) => setCaseId(event.target.value)}
              placeholder="Leave empty to generate automatically"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="error-banner">
              <strong>Unable to create investigation</strong>
              <span>{error}</span>
            </div>
          )}

          <div className="form-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={onCancel}
              disabled={loading}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="primary-button"
              disabled={loading || !name.trim()}
            >
              {loading ? "Creating..." : "Create Investigation"}
              {!loading && <span>→</span>}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}