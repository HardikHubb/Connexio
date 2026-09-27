
import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Overview from "./pages/Overview";
import Network from "./pages/Network";
import AddData from "./components/AddData";
import CreateInvestigation from "./components/CreateInvestigation";
import "./styles.css";

function App() {
  const [activePage, setActivePage] = useState("overview");
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [showCreateInvestigation, setShowCreateInvestigation] =
    useState(false);

  function handlePageChange(page) {
    setShowCreateInvestigation(false);
    setActivePage(page);
  }

  function handleAddData() {
    setShowCreateInvestigation(false);
    setActivePage("add-data");
  }

  function handleInvestigationCreated(createdCase) {
    setShowCreateInvestigation(false);
    setActivePage("overview");
    setSelectedCaseId(createdCase.case_id);
  }

  function renderPage() {
    if (showCreateInvestigation) {
      return (
        <CreateInvestigation
          onCreated={handleInvestigationCreated}
          onCancel={() => setShowCreateInvestigation(false)}
        />
      );
    }

    if (activePage === "network") {
  return (
    <Network
      caseId={selectedCaseId}
    />
  );
}

    if (activePage === "overview") {
      return (
        <Overview
          selectedCaseId={selectedCaseId}
          onSelectCase={setSelectedCaseId}
          onOpenNetwork={() => setActivePage("network")}
        />
      );
    }

    if (activePage === "add-data") {
      return (
        <main className="main-content">
          <AddData
            caseId={selectedCaseId}
            onUploadComplete={() => {
              // Automatic refresh will be connected in the next step.
            }}
          />
        </main>
      );
    }

    return (
      <main className="main-content">
        <div className="placeholder-page">
          <div className="eyebrow">STAGE 9</div>

          <h1>
            {activePage === "network" && "Network"}
            {activePage === "cross-case" && "Cross-Case"}
            {activePage === "evidence" && "Evidence"}
          </h1>

          <p>
            This workspace will be implemented in the
            following Stage 9 groups.
          </p>

          <button
            className="secondary-button"
            onClick={() => setActivePage("overview")}
          >
            ← Back to Overview
          </button>
        </div>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        onPageChange={handlePageChange}
        onAddData={handleAddData}
      />

      <div className="page-area">
        {renderPage()}
      </div>
    </div>
  );
}

export default App;

