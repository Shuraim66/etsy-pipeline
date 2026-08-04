// ErrorBoundary - turns a render crash into a visible message (instead of a
// blank screen) so problems are actionable.

import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // surfaced in the console for debugging
    console.error("Annotator crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, color: "#e6e8ec", fontFamily: "monospace" }}>
          <h2 style={{ color: "#ff6b6b" }}>The annotator hit an error</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{String(this.state.error?.stack || this.state.error)}</pre>
          <button
            style={{ marginTop: 12, padding: "6px 12px" }}
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
