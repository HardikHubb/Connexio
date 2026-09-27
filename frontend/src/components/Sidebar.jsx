export default function Sidebar({
  activePage,
  onPageChange,
  onAddData,
}) {
  const navigation = [
    {
      id: "overview",
      label: "Overview",
      icon: "◈",
    },
    {
      id: "network",
      label: "Network",
      icon: "⌘",
    },
    {
      id: "cross-case",
      label: "Cross-Case",
      icon: "⇄",
    },
    {
      id: "evidence",
      label: "Evidence",
      icon: "▤",
    },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">C</div>

        <div>
          <div className="brand-name">CONNEXIO</div>
          <div className="brand-subtitle">
            Investigation Intelligence
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-label">WORKSPACE</div>

        <nav className="nav-list">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${
                activePage === item.id ? "active" : ""
              }`}
              onClick={() => onPageChange(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        <button
          className="add-data-button"
          onClick={onAddData}
        >
          <span>+</span>
          <span>Add Data</span>
        </button>

        <div className="system-status">
          
          
        </div>
      </div>
    </aside>
  );
}