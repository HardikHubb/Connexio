import { useRef, useState } from "react";
import { uploadCaseFile } from "../api/client";

const SOURCE_TYPES = [
  {
    value: "FIR",
    label: "FIR / Case Report",
    extensions: ".txt",
  },
  {
    value: "CDR",
    label: "Call Detail Record",
    extensions: ".csv",
  },
  {
    value: "TRANSACTION",
    label: "Transaction Record",
    extensions: ".csv",
  },
  {
    value: "VEHICLE",
    label: "Vehicle Record",
    extensions: ".csv",
  },
  {
    value: "LOCATION",
    label: "Location Record",
    extensions: ".csv",
  },
  {
    value: "REPORT",
    label: "Investigation Report",
    extensions: ".txt",
  },
];

export default function AddData({ caseId, onUploadComplete }) {
  const fileInputRef = useRef(null);

  const [sourceType, setSourceType] = useState("FIR");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedSource = SOURCE_TYPES.find(
    (source) => source.value === sourceType
  );

  function handleFileChange(event) {
    const file = event.target.files?.[0] || null;

    setSelectedFile(file);
    setMessage("");
    setError("");
  }

  async function handleUpload(event) {
    event.preventDefault();

    setMessage("");
    setError("");

    if (!caseId) {
      setError("No investigation case is selected.");
      return;
    }

    if (!selectedFile) {
      setError("Select a file before uploading.");
      return;
    }

    try {
      setUploading(true);

      const result = await uploadCaseFile(
        caseId,
        sourceType,
        selectedFile
      );

      setMessage(
        `${result.source_type} uploaded successfully. Source ID: ${result.source_id}`
      );

      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="add-data-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">DATA INGESTION</span>
          <h2>Add investigation data</h2>
          <p>
            Upload source records into the selected investigation.
          </p>
        </div>

        <div className="case-badge">
          CASE {caseId || "—"}
        </div>
      </div>

      <form className="upload-form" onSubmit={handleUpload}>
        <div className="form-field">
          <label htmlFor="source-type">Source type</label>

          <select
            id="source-type"
            value={sourceType}
            onChange={(event) => {
              setSourceType(event.target.value);
              setSelectedFile(null);
              setMessage("");
              setError("");

              if (fileInputRef.current) {
                fileInputRef.current.value = "";
              }
            }}
            disabled={uploading}
          >
            {SOURCE_TYPES.map((source) => (
              <option key={source.value} value={source.value}>
                {source.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="source-file">Source file</label>

          <input
            ref={fileInputRef}
            id="source-file"
            type="file"
            accept={selectedSource?.extensions}
            onChange={handleFileChange}
            disabled={uploading}
          />

          <span className="field-hint">
            Expected format: {selectedSource?.extensions}
          </span>
        </div>

        {selectedFile && (
          <div className="selected-file">
            <span className="selected-file-label">
              Selected
            </span>

            <span className="selected-file-name">
              {selectedFile.name}
            </span>

            <span className="selected-file-size">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </span>
          </div>
        )}

        {error && (
          <div className="upload-message upload-error">
            {error}
          </div>
        )}

        {message && (
          <div className="upload-message upload-success">
            {message}
          </div>
        )}

        <button
          type="submit"
          className="primary-button"
          disabled={uploading || !selectedFile}
        >
          {uploading ? "Uploading…" : "Upload source"}
        </button>
      </form>
    </section>
  );
}