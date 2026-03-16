import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("ASTRA component error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: "20px",
          background: "rgba(248,113,113,0.08)",
          border: "1px solid rgba(248,113,113,0.2)",
          borderRadius: 10,
          color: "#f87171",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
        }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>
            ⚠ Component Error
          </div>
          <div style={{ opacity: 0.7, fontSize: 11 }}>
            {this.state.error.message}
          </div>
          <button
            onClick={() => this.setState({ error: null })}
            style={{
              marginTop: 12, padding: "4px 12px",
              background: "rgba(248,113,113,0.12)",
              border: "1px solid rgba(248,113,113,0.3)",
              borderRadius: 6, color: "#f87171",
              cursor: "pointer", fontSize: 11,
              fontFamily: "inherit",
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
