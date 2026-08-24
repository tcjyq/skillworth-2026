"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

export class CanvasBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("skill_field_webgl_initialization_failed", error.message, info.componentStack);
  }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}
