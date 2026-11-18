# NetScope – Technical Decisions Record

## Decision Log

### 1. Framework Selection

**Decision:** Use FastAPI for backend Python framework instead of Flask or Django

**Rationale:**
- Async support for concurrent scanning operations
- Automatic OpenAPI documentation
- Pydantic integration for data validation
- Better performance for I/O-bound operations
- Modern type hints and async/await support

**Alternatives Considered:**
- Flask: Synchronous, less suitable for concurrent operations
- Django: Overkill for this application, too opinionated

**Date:** 2026-11-16
**Status:** Approved

---

### 2. Database Choice

**Decision:** Use SQLite with SQLAlchemy for local data storage

**Rationale:**
- No external database server required
- Single file database, easy to backup
- SQLAlchemy provides ORM abstraction
- SQLite handles concurrent reads well with WAL mode
- Perfect for desktop application use case

**Alternatives Considered:**
- PostgreSQL: Requires server setup, overkill for desktop
- MongoDB: Not ideal for relational data
- MariaDB: Server dependency

**Date:** 2026-11-16
**Status:** Approved

---

### 3. Frontend Framework

**Decision:** React with TypeScript for frontend

**Rationale:**
- Component-based architecture fits dashboard UI
- Strong TypeScript ecosystem
- Large community and library support
- Excellent integration with Tailwind CSS
- Proven track record for data-heavy applications

**Alternatives Considered:**
- Vue.js: Smaller ecosystem
- Svelte: Less mature tooling

**Date:** 2026-11-16
**Status:** Approved

---

### 4. Desktop Framework

**Decision:** Use Tauri 2 for macOS desktop application

**Rationale:**
- Native macOS performance
- Small binary size (<10MB)
- Access to native macOS APIs
- Built-in auto-update support
- Rust backend provides security
- Active development and community

**Alternatives Considered:**
- Electron: Larger binary, performance concerns
- Flutter Desktop: Less mature macOS support

**Date:** 2026-11-16
**Status:** Approved

---

### 5. Build Tool

**Decision:** Use Vite for frontend build

**Rationale:**
- Fast development server with HMR
- Optimized production builds
- Rollup for bundling
- Native ES modules support
- Excellent TypeScript integration

**Alternatives Considered:**
- Webpack: Slower development experience
- Parcel: Less configuration flexibility

**Date:** 2026-11-16
**Status:** Approved

---

### 6. Styling Approach

**Decision:** Use Tailwind CSS with shadcn/ui primitives

**Rationale:**
- Utility-first approach for rapid development
- Consistent design system
- Tailored dark theme support
- shadcn/ui provides accessible primitives
- Fully customizable design tokens

**Alternatives Considered:**
- CSS-in-JS (Emotion, Styled Components): Runtime overhead
- Bootstrap: Overly opinionated, not SOC-style

**Date:** 2026-11-16
**Status:** Approved

---

### 7. Data Fetching Library

**Decision:** Use TanStack Query (React Query) for data fetching

**Rationale:**
- Built-in caching and refetching
- Optimistic updates
- Request deduplication
- Excellent TypeScript support
- Handles loading/error states

**Alternatives Considered:**
- SWR: Less feature-rich
- Manual fetch: Repetitive boilerplate

**Date:** 2026-11-16
**Status:** Approved

---

### 8. State Management

**Decision:** Use Zustand for state management

**Rationale:**
- Minimal boilerplate
- Native TypeScript support
- Devtools integration
- Subscriptions without React context Provider
- Suitable for simple to moderate complexity

**Alternatives Considered:**
- Redux: Verbose for this use case
- Jotai: More complex for global state

**Date:** 2026-11-16
**Status:** Approved

---

### 9. Chart Library

**Decision:** Use Apache ECharts for charts and visualizations

**Rationale:**
- Comprehensive chart types
- Excellent performance with large datasets
- Rich interaction capabilities
- Production-ready for security dashboards
- Active maintenance

**Alternatives Considered:**
- Chart.js: Limited chart types
- D3.js: Too complex for dashboard charts

**Date:** 2026-11-16
**Status:** Approved

---

### 10. Network Topology Visualization

**Decision:** Use Cytoscape.js for network topology

**Rationale:**
- Purpose-built for graph visualization
- Multiple layout algorithms
- Rich interaction capabilities
- Well-maintained library

**Alternatives Considered:**
- vis.js: Less feature-rich
- Sigma: Smaller ecosystem

**Date:** 2026-11-16
**Status:** Approved

---

### 11. Security Architecture Decision

**Decision:** Never run as root, only request elevated privileges when necessary

**Rationale:**
- Security best practice
- Reduces attack surface
- macOS security model compliance
- Clear user experience for permission requests

**Alternatives Considered:**
- Always running as root: High security risk
- No privilege separation: Cannot perform required operations

**Date:** 2026-11-16
**Status:** Approved

---

### 12. Nmap Integration Strategy

**Decision:** Use subprocess to invoke system Nmap, parse XML output

**Rationale:**
- Nmap already handles complex scanning logic
- XML output is stable and well-documented
- No need to reimplement scanning algorithms
- Supports all Nmap features immediately

**Alternatives Considered:**
- Python socket scanning: Reimplementation of existing functionality
- Third-party Nmap libraries: Limited feature support

**Date:** 2026-11-16
**Status:** Approved

---

### 13. Vulnerability Data Storage

**Decision:** Store vulnerability data locally in SQLite with intelligence sync system

**Rationale:**
- Works offline
- Fast local queries with proper indexing
- Version history preserved
-可控 caching layer for API responses

**Alternatives Considered:**
- Cache-only in memory: Loses data between sessions
- Always query API: Rate limits, offline不可行

**Date:** 2026-11-16
**Status:** Approved

---

### 14. Real-time Communication

**Decision:** Use WebSockets for real-time updates (scan progress, events)

**Rationale:**
- Push updates from backend to frontend
- Efficient for frequent updates
- Native FastAPI and React support

**Alternatives Considered:**
- Server-sent events: One-way communication
- Polling: Inefficient for real-time updates

**Date:** 2026-11-16
**Status:** Approved

---

### 15. Testing Strategy

**Decision:** Implement pytest for backend and Vitest for frontend

**Rationale:**
- Python standard testing framework
- Fast test execution with pytest fixtures
- Vitest works well with Vite projects

**Alternatives Considered:**
- Rust tests for backend: Not suitable for Python code
- Jest for frontend: Slower than Vitest

**Date:** 2026-11-16
**Status:** Approved

---

### 16. Scan Cancellation Implementation

**Decision:** Use subprocess signals (SIGTERM, SIGINT) for scan cancellation

**Rationale:**
- Native signal handling in Python
- Clean termination of scanning processes
- Platform-consistent behavior

**Alternatives Considered:**
- Process kill (SIGKILL): Data loss risk
- Custom process wrapper: Unnecessary complexity

**Date:** 2026-11-16
**Status:** Approved

---

### 17. API Versioning Strategy

**Decision:** Use /api/v1/ path prefix for versioning

**Rationale:**
- Clear version identification
- Easy to maintain multiple API versions
- Industry standard approach

**Alternatives Considered:**
- Query parameter versioning: Less RESTful
- Header-based versioning: Harder to test

**Date:** 2026-11-16
**Status:** Approved

---

### 18. Dependency Management

**Decision:** Use Homebrew for external tool installation on macOS

**Rationale:**
- Standard macOS package manager
- Easy dependency management
- Automatic updates
- Well-documented

**Alternatives Considered:**
- Direct downloads: Manual management complexity
- MacPorts: Less popular than Homebrew

**Date:** 2026-11-16
**Status:** Approved

---

### 19. Error Handling Approach

**Decision:** Use structured error responses with consistent format

**Rationale:**
- Clear error messages for users
- Consistent API responses
- Better debugging experience

**Alternatives Considered:**
- Exception propagation: No user-friendly messages
- Error codes only: Hard to debug

**Date:** 2026-11-16
**Status:** Approved

---

### 20. Logging Strategy

**Decision:** Use Python logging module with structured JSON format

**Rationale:**
- Standard library, no dependencies
- Structured for parsing and analysis
- Multiple log levels for different environments

**Alternatives Considered:**
- Third-party logging libraries: Unnecessary dependencies
- Plain text logs: Harder to parse

**Date:** 2026-11-16
**Status:** Approved

---

## Design Principles

### 1. Security First
- No remote execution capability
- Input validation on all endpoints
- Conservative scanning defaults

### 2. Local First
- All data stored locally
- Offline capability for vulnerability lookup
- No cloud infrastructure requirements

### 3. User Control
- Explicit scan authorization
- Configurable scanning parameters
- Clear progress and status indicators

### 4. Transparency
- Confidence levels on all findings
- Evidence tracking for correlations
- Scan results preserved

### 5. Extensibility
- Modular engine architecture
- Pluggable intelligence sources
- Extension points for new features

## Known Limitations (Initial Release)

1. Only macOS supported initially
2. Single user per installation
3. No distributed scanning capability
4. Basic role-based access control
5. Limited scan scheduling (manual only in Phase 1)

## Future Considerations

- Multi-platform support
- Cloud sync option
- Collaborative scanning features
- Advanced authentication (OAuth, SSO)
- Export to various formats (PDF, CSV, JSON)
