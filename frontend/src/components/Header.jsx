export default function Header() {
  return (
    <header className="topbar">
      <a className="brand" href="#hero">
        <span className="brand-mark" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </span>
        <span>Spectre</span>
      </a>
      <nav className="nav-links" aria-label="Primary navigation">
        <a href="#bridge">Product</a>
        <a href="#tracks">Use cases</a>
        <a href="#integrations">Institutions</a>
        <a href="#demo">Demo</a>
      </nav>
      <div className="top-actions">
        <a className="ghost-link" href="#demo">Sign in</a>
        <a className="primary-link" href="#demo">Get Started</a>
      </div>
    </header>
  );
}
