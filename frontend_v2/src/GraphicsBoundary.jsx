import React from "react";
// Curriculum facts remain available in the ledger if a GPU or chunk fails.
export class GraphicsBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback || null : this.props.children; }
}
