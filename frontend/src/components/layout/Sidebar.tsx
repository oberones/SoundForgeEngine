interface SidebarProps {
  route: "live" | "config" | "actions";
  onRouteChange: (route: "live" | "config" | "actions") => void;
  domainCount: number;
  actionCount: number;
}

const NAV_ITEMS: Array<{ id: "live" | "config" | "actions"; label: string; blurb: string }> = [
  { id: "live", label: "Live", blurb: "Performance controls and engine status" },
  { id: "config", label: "Configuration", blurb: "Browse every exposed control domain" },
  { id: "actions", label: "Actions", blurb: "Trigger semantic workflows through the shared API" }
];

export function Sidebar({ route, onRouteChange, domainCount, actionCount }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand-panel">
        <p className="eyebrow">SoundForgeEngine</p>
        <h1>Control Surface</h1>
        <p className="brand-copy">
          A single operator dashboard for shaping the running engine without dropping into raw API payloads.
        </p>
      </div>

      <nav className="nav-list" aria-label="Dashboard navigation">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={item.id === route ? "nav-item active" : "nav-item"}
            onClick={() => onRouteChange(item.id)}
            type="button"
          >
            <span className="nav-item-title">{item.label}</span>
            <span className="nav-item-copy">{item.blurb}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-meta">
        <div>
          <span className="meta-label">Domains</span>
          <strong>{domainCount}</strong>
        </div>
        <div>
          <span className="meta-label">Actions</span>
          <strong>{actionCount}</strong>
        </div>
      </div>
    </aside>
  );
}
