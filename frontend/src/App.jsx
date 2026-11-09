
import React, { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, Bell,
  BookOpen, Bot, BrainCircuit, Check, CheckCircle2, ChevronDown, CircleHelp,
  Clock3, Cloud, Code2, Command, Database, Download, FileText, Gauge,
  GraduationCap, Layers3, LifeBuoy, Menu, Plus, RefreshCw, Search, Server,
  ShieldCheck, Sparkles, Terminal, TrendingUp, X, Zap
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const STORAGE_KEY = "runbook-ai-incidents-v1";

const initialIncidents = [
  {
    incident_id: "DEMO-1042",
    description: "Payment API latency increased after a database connection pool spike.",
    remediation_plan: "1. Inspect active database connections and identify pool saturation.\n2. Check for leaked connections and long-running queries.\n3. Restart only the affected worker if required.\n4. Tune pool limits and add utilization alerts.\n5. Verify p95 latency and error rate return to baseline.",
    status: "analyzed",
    resolution_status: "",
    created_at: new Date(Date.now() - 1000 * 60 * 44).toISOString(),
    demo: true
  },
  {
    incident_id: "DEMO-1038",
    description: "Repeated failed SSH authentication attempts from an unfamiliar IP range.",
    remediation_plan: "1. Preserve authentication logs and source IP evidence.\n2. Check whether any login succeeded.\n3. Block confirmed malicious sources using the approved firewall process.\n4. Rotate exposed credentials and enforce MFA.\n5. Review access logs for lateral movement.",
    status: "analyzed",
    resolution_status: "resolved",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    demo: true
  },
  {
    incident_id: "DEMO-1029",
    description: "CPU utilization reached 94% on production worker nodes.",
    remediation_plan: "1. Identify the top CPU-consuming processes.\n2. Compare traffic and deployment changes with the spike.\n3. Scale workers temporarily if capacity is constrained.\n4. Profile the hot path and apply a permanent fix.\n5. Add a sustained CPU saturation alert.",
    status: "analyzed",
    resolution_status: "resolved",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 22).toISOString(),
    demo: true
  }
];

function readIncidents() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    return Array.isArray(saved) && saved.length ? saved : initialIncidents;
  } catch {
    return initialIncidents;
  }
}

function saveIncidents(items) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {}
}

function shortId(id = "") {
  return id.startsWith("DEMO-") ? id : `INC-${id.slice(0, 6).toUpperCase()}`;
}

function timeAgo(value) {
  const diff = Math.max(0, Date.now() - new Date(value).getTime());
  const mins = Math.floor(diff / 60000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;

  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;

  return `${Math.floor(hrs / 24)}d ago`;
}

function categoryOf(text = "") {
  const s = text.toLowerCase();

  if (/database|sql|query|connection|pool/.test(s)) return "Database";
  if (/cpu|memory|disk|server|latency|load/.test(s)) return "Infrastructure";
  if (/ssh|login|auth|security|token|credential/.test(s)) return "Security";
  if (/network|dns|http|api|timeout/.test(s)) return "Network / API";

  return "Application";
}

function StatusPill({ status }) {
  const value =
    status === "resolved"
      ? "Resolved"
      : status === "failed"
        ? "Failed"
        : "Investigating";

  return (
    <span className={`status-pill ${status || "analyzed"}`}>
      <i />
      {value}
    </span>
  );
}

function MetricCard({ icon: Icon, label, value, change, tone = "purple", foot }) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${tone}`}>
        <Icon size={18} />
      </div>
      <div className="metric-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{foot || change}</small>
      </div>
      <div className="metric-spark">
        <Activity size={34} />
      </div>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("Overview");
  const [incidents, setIncidents] = useState(readIncidents);
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [description, setDescription] = useState("");

  // Multimodal upload state
  const [imageFiles, setImageFiles] = useState([]);
  const [logFiles, setLogFiles] = useState([]);

  const [submitting, setSubmitting] = useState(false);
  const [apiState, setApiState] = useState("checking");
  const [apiMessage, setApiMessage] = useState("Checking API connection");
  const [selected, setSelected] = useState(null);
  const [resolutionText, setResolutionText] = useState("");
  const [resolutionStatus, setResolutionStatus] = useState("resolved");
  const [savingResolution, setSavingResolution] = useState(false);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantMessages, setAssistantMessages] = useState([]);
  const [sendingAssistantMessage, setSendingAssistantMessage] = useState(false);
  const [toast, setToast] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    saveIncidents(incidents);
  }, [incidents]);

  useEffect(() => {
    if (!selected || selected.demo) return;

    let active = true;
    setAssistantMessages(prev =>
      prev.filter(entry => entry.incidentId !== selected.incident_id)
    );

    fetch(`${API_BASE}/incidents/${selected.incident_id}/conversation`)
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load conversation.");
        return data;
      })
      .then(data => {
        if (!active) return;
        const restored = (data.messages || []).map(item => ({
          incidentId: item.incident_id,
          role: item.role,
          text: item.text,
          approvalId: item.approval_id,
          approvalStatus: item.approval_status,
          proposedAction: item.proposed_action,
          riskLevel: item.risk_level,
          approvalBusy: false
        }));
        setAssistantMessages(prev => [
          ...prev.filter(entry => entry.incidentId !== selected.incident_id),
          ...restored
        ]);
      })
      .catch(err => {
        if (active) setToast(`Conversation history: ${err.message}`);
      });

    return () => { active = false; };
  }, [selected?.incident_id, selected?.demo]);

  async function persistConversationMessage(incidentId, entry) {
    const response = await fetch(
      `${API_BASE}/incidents/${incidentId}/conversation`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(entry)
      }
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not save conversation.");
    return data;
  }

  useEffect(() => {
    let active = true;

    fetch(`${API_BASE}/health`)
      .then(r => {
        if (!r.ok) throw new Error("API returned an error");
        return r.json();
      })
      .then(() => {
        if (active) {
          setApiState("online");
          setApiMessage("Backend connected");
        }
      })
      .catch(() => {
        if (active) {
          setApiState("offline");
          setApiMessage("API offline · start FastAPI");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;

    const t = setTimeout(() => setToast(""), 3600);
    return () => clearTimeout(t);
  }, [toast]);

  const resolved = incidents.filter(
    i => i.resolution_status === "resolved"
  ).length;

  const openCount = incidents.filter(
    i => !i.resolution_status
  ).length;

  const successRate = incidents.length
    ? Math.round((resolved / incidents.length) * 100)
    : 0;

  const filtered = incidents.filter(i =>
    `${i.description} ${i.incident_id}`
      .toLowerCase()
      .includes(query.toLowerCase())
  );

  const categories = useMemo(() => {
    const counts = {};

    incidents.forEach(i => {
      const c = categoryOf(i.description);
      counts[c] = (counts[c] || 0) + 1;
    });

    return Object.entries(counts).map(([name, value]) => ({
      name,
      value
    }));
  }, [incidents]);

  const trend = useMemo(() => {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    return days.map((day, idx) => {
      const count = incidents.filter(
        i => new Date(i.created_at).getDay() === (idx + 1) % 7
      ).length;

      return { day, incidents: count };
    });
  }, [incidents]);

  const learning = useMemo(() => {
    const groups = {};

    incidents.forEach(i => {
      const category = categoryOf(i.description);

      groups[category] = groups[category] || {
        category,
        count: 0,
        resolved: 0,
        examples: []
      };

      groups[category].count += 1;

      if (i.resolution_status === "resolved") {
        groups[category].resolved += 1;
      }

      if (groups[category].examples.length < 2) {
        groups[category].examples.push(i.description);
      }
    });

    return Object.values(groups).sort((a, b) => b.count - a.count);
  }, [incidents]);

  // Create a text-only or multimodal incident
  async function createIncident(e) {
    e.preventDefault();

    if (description.trim().length < 5) return;

    if (imageFiles.length > 3) {
      setToast("Maximum 3 screenshots are allowed.");
      return;
    }

    if (logFiles.length > 10) {
      setToast("Maximum 10 log files are allowed.");
      return;
    }

    const invalidImage = imageFiles.find(
      file => file.size > 6 * 1024 * 1024
    );

    if (invalidImage) {
      setToast("Each screenshot must be 6 MB or smaller.");
      return;
    }

    const invalidLog = logFiles.find(
      file => file.size > 1 * 1024 * 1024
    );

    if (invalidLog) {
      setToast("Each log file must be 1 MB or smaller.");
      return;
    }

    setSubmitting(true);

    try {
      let response;

      if (imageFiles.length > 0 || logFiles.length > 0) {
        const formData = new FormData();

        formData.append("description", description.trim());

        imageFiles.forEach(file => {
          formData.append("images", file);
        });

        logFiles.forEach(file => {
          formData.append("logs", file);
        });

        response = await fetch(`${API_BASE}/incidents/multimodal`, {
          method: "POST",
          body: formData
        });
      } else {
        response = await fetch(`${API_BASE}/incidents`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            description: description.trim()
          })
        });
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Incident request failed");
      }

      const item = {
        ...data,
        created_at: new Date().toISOString(),
        resolution_status: "",
        demo: false
      };

      setIncidents(prev => [item, ...prev]);
      setSelected(item);

      setDescription("");
      setImageFiles([]);
      setLogFiles([]);

      setShowCreate(false);
      setPage("Incidents");

      setToast("Incident analyzed successfully by RunBook AI.");
    } catch (err) {
      setToast(
        `Could not analyze incident: ${err.message}. Check that FastAPI is running.`
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function recordResolution() {
    if (!selected || selected.demo) {
      setToast(
        "Demo incidents cannot be sent to the backend. Create a live incident first."
      );
      return;
    }

    if (resolutionText.trim().length < 5) {
      setToast("Please enter at least 5 characters describing the outcome.");
      return;
    }

    setSavingResolution(true);

    try {
      const response = await fetch(
        `${API_BASE}/incidents/${selected.incident_id}/resolution`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            status: resolutionStatus,
            resolution_details: resolutionText.trim()
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not record resolution");
      }

      setIncidents(prev =>
        prev.map(i =>
          i.incident_id === selected.incident_id
            ? {
                ...i,
                resolution_status: resolutionStatus,
                resolution_details: resolutionText.trim()
              }
            : i
        )
      );

      setSelected(prev => ({
        ...prev,
        resolution_status: resolutionStatus,
        resolution_details: resolutionText.trim()
      }));

      setResolutionText("");
      setToast("Resolution saved and linked to the original incident.");
    } catch (err) {
      setToast(err.message);
    } finally {
      setSavingResolution(false);
    }
  }

  async function sendIncidentMessage(e) {
    e.preventDefault();
    const message = assistantInput.trim();

    if (!selected || selected.demo || message.length < 5 || sendingAssistantMessage) {
      if (selected?.demo) setToast("Create a live incident to use its AI conversation.");
      return;
    }

    const incidentId = selected.incident_id;
    setAssistantMessages(prev => [...prev, { incidentId, role: "user", text: message }]);
    setAssistantInput("");
    setSendingAssistantMessage(true);

    try {
      await persistConversationMessage(incidentId, {
        role: "user",
        text: message
      });

      const response = await fetch(`${API_BASE}/assistant/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, incident_id: incidentId })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Assistant request failed");

      let reply =
        data.answer ||
        data.clarification ||
        data.remediation_plan ||
        data.message ||
        "RunBook AI processed your message.";

      if (data.approval_required) {
        reply += `\n\nRequested action: ${data.proposed_action}\nRisk level: ${data.risk_level}`;
      }

      if (
        data.historical_reflection &&
        data.historical_reflection !== "No historical reflection available."
      ) {
        reply += `\n\n### Hindsight — Historical Memory\n\n${data.historical_reflection}`;

        if (data.reflection_facts?.length) {
          reply += "\n\n**Supporting memories:**";
          reply += data.reflection_facts.map(fact => `\n- ${fact}`).join("");
        }
      }

      const assistantEntry = {
        incidentId,
        role: "assistant",
        text: reply,
        approvalId: data.approval_id || null,
        approvalStatus: data.approval_required ? "pending" : null,
        proposedAction: data.proposed_action || null,
        riskLevel: data.risk_level || null
      };

      await persistConversationMessage(incidentId, {
        role: "assistant",
        text: reply,
        approval_id: data.approval_id || null,
        proposed_action: data.proposed_action || null,
        risk_level: data.risk_level || null
      });

      setAssistantMessages(prev => [...prev, assistantEntry]);
    } catch (err) {
      setAssistantMessages(prev => [...prev, {
        incidentId,
        role: "assistant",
        text: `Could not process your message: ${err.message}`
      }]);
    } finally {
      setSendingAssistantMessage(false);
    }
  }

  async function decideIncidentApproval(approvalId, decision) {
    setAssistantMessages(prev => prev.map(entry =>
      entry.approvalId === approvalId ? { ...entry, approvalBusy: true } : entry
    ));

    try {
      const response = await fetch(
        `${API_BASE}/approvals/${approvalId}/decision`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision })
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Approval decision failed");

      setAssistantMessages(prev => prev.map(entry =>
        entry.approvalId === approvalId
          ? {
              ...entry,
              approvalStatus: data.approval_status,
              executionStatus: data.execution_status,
              approvalBusy: false
            }
          : entry
      ));
      setToast(
        decision === "approved"
          ? "Approval recorded. No infrastructure operation was executed."
          : "Request rejected. No infrastructure operation was executed."
      );
    } catch (err) {
      setAssistantMessages(prev => prev.map(entry =>
        entry.approvalId === approvalId
          ? { ...entry, approvalBusy: false }
          : entry
      ));
      setToast(err.message);
    }
  }

  function exportReport() {
    const rows = [
      ["Incident ID", "Description", "Status", "Resolution", "Created"]
    ];

    incidents.forEach(i =>
      rows.push([
        i.incident_id,
        i.description,
        i.status,
        i.resolution_status || "open",
        i.created_at
      ])
    );

    const csv = rows
      .map(row =>
        row
          .map(v => `"${String(v ?? "").replaceAll('"', '""')}"`)
          .join(",")
      )
      .join("\n");

    const blob = new Blob([csv], {
      type: "text/csv;charset=utf-8;"
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = "runbook-incidents.csv";
    a.click();

    URL.revokeObjectURL(url);
    setToast("Incident report exported.");
  }

  const nav = [
    {
      label: "WORKSPACE",
      items: [
        { name: "Overview", icon: Gauge },
        { name: "Incidents", icon: AlertCircle },
        { name: "Learning", icon: GraduationCap },
        { name: "Reports", icon: FileText }
      ]
    },
    {
      label: "SYSTEM",
      items: [
        { name: "Integrations", icon: Layers3 },
        { name: "Documentation", icon: BookOpen }
      ]
    }
  ];

  const titleMap = {
    Overview: ["Command center", "Your incident response, at a glance."],
    Agent: ["AI operations agent", "Ask, investigate, and approve safely."],
    Incidents: [
      "Incident management",
      "Investigate, understand, and close the loop."
    ],
    Learning: [
      "Engineering intelligence",
      "Turn every incident into reusable team knowledge."
    ],
    Reports: [
      "Reports & exports",
      "A clear view of operational activity."
    ],
    Integrations: [
      "Connected services",
      "The systems powering your response workflow."
    ],
    Documentation: [
      "RunBook guide",
      "A quick guide to the incident response workflow."
    ]
  };

  function go(name) {
    setPage(name);
    setMobileOpen(false);
    setSelected(null);
  }

  const header = titleMap[page] || titleMap.Overview;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Command size={20} />
          </div>
          <div>
            <b>runbook<span>.ai</span></b>
            <small>INCIDENT COMMAND</small>
          </div>
          <button
            className="mobile-close icon-button"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="workspace-switch" aria-label="Active workspace: RunBook AI">
          <div className="workspace-avatar">RB</div>
          <div>
            <b>RunBook AI</b>
            <small>Incident operations</small>
          </div>
          <span className="workspace-active-dot" />
        </div>

        <div className="nav-wrap">
          {nav.map(group => (
            <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map(item => (
                <button
                  key={item.name}
                  className={`nav-link ${page === item.name ? "active" : ""}`}
                  onClick={() => go(item.name)}
                >
                  <item.icon size={17} />
                  <span>{item.name}</span>
                  {item.name === "Incidents" && openCount > 0 && (
                    <em>{openCount}</em>
                  )}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="memory-card">
            <div className="memory-card-icon">
              <BrainCircuit size={17} />
            </div>
            <b>Memory is learning</b>
            <p>Every resolved incident makes your runbooks smarter.</p>
            <button onClick={() => go("Learning")}>
              Explore insights <ArrowUpRight size={14} />
            </button>
          </div>

          <div className="profile-menu-wrap">
            <button type="button" className="user-row profile-trigger"
              aria-expanded={showProfileMenu}
              onClick={() => setShowProfileMenu(v => !v)}>
              <span className="user-avatar">RB</span>
              <span className="profile-copy">
                <b>On-call Engineer</b>
                <small>Incident responder</small>
              </span>
              <ChevronDown size={15} />
            </button>
            {showProfileMenu && (
              <div className="profile-menu">
                <div className="profile-menu-title">Operator profile</div>
                <div className="profile-menu-line"><span>Role</span><b>On-call Engineer</b></div>
                <div className="profile-menu-line"><span>Workspace</span><b>RunBook AI</b></div>
                <div className="profile-menu-line">
                  <span>API status</span>
                  <b className={`profile-api-status ${apiState}`}>
                    {apiState === "online" ? "Connected" : apiState === "checking" ? "Checking" : "Offline"}
                  </b>
                </div>
                <button type="button" className="profile-menu-action"
                  onClick={() => { setShowProfileMenu(false); go("Documentation"); }}>
                  Open operator guide <ArrowRight size={13} />
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="top-left">
            <button
              className="icon-button menu-button"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={20} />
            </button>
            <div className="breadcrumb">
              Workspace <span>/</span> <b>{page}</b>
            </div>
          </div>

          <div className="top-actions">
            <div className={`api-indicator ${apiState}`}>
              <i />
              {apiMessage}
            </div>

            <button
              className="icon-button"
              title="Refresh API status"
              onClick={() => {
                setApiState("checking");

                fetch(`${API_BASE}/health`)
                  .then(r => {
                    if (!r.ok) throw new Error();
                    setApiState("online");
                    setApiMessage("Backend connected");
                  })
                  .catch(() => {
                    setApiState("offline");
                    setApiMessage("API offline · start FastAPI");
                  });
              }}
            >
              <RefreshCw size={17} />
            </button>

            <div className="notification-wrap">
              <button
                className="icon-button notification"
                title="Notifications"
                aria-label="Notifications"
                aria-expanded={showNotifications}
                onClick={() => setShowNotifications(v => !v)}
              >
                <Bell size={17} />
                {incidents.some(i => i.resolution_status !== "resolved") && <i />}
              </button>
              {showNotifications && (
                <div className="notification-panel">
                  <div className="notification-panel-heading">
                    <div><b>Notifications</b><small>Workspace activity</small></div>
                    <button className="icon-button" onClick={() => setShowNotifications(false)} aria-label="Close notifications"><X size={16} /></button>
                  </div>
                  <div className="notification-item">
                    <span className="notification-dot" />
                    <div>
                      <b>{incidents.filter(i => i.resolution_status !== "resolved").length} unresolved incidents</b>
                      <p>Incidents that may need your attention.</p>
                    </div>
                  </div>
                  <div className="notification-item">
                    <span className={`notification-dot ${apiState}`} />
                    <div><b>Backend: {apiState}</b><p>{apiMessage}</p></div>
                  </div>
                  <button className="notification-review" onClick={() => { setShowNotifications(false); go("Incidents"); }}>
                    Review incidents <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </div>

            <div className="top-avatar">RB</div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-dot" /> RUNBOOK CONTROL PLANE
              </div>
              <h1>{header[0]}</h1>
              <p>{header[1]}</p>
            </div>

            <div className="heading-actions">
              <span className="live-label"><i /> LIVE WORKSPACE</span>
              <button
                className="primary-button"
                onClick={() => setShowCreate(true)}
              >
                <Plus size={17} /> New incident
              </button>
            </div>
          </div>

          {page === "Overview" && (
            <>
              <section className="welcome-banner">
                <div className="banner-orb orb-one" />
                <div className="banner-orb orb-two" />

                <div className="banner-content">
                  <div className="banner-kicker">
                    <Sparkles size={14} /> YOUR AI INCIDENT ENGINEER
                  </div>
                  <h2>
                    Master the chaos.
                    <br />
                    <span>Resolve incidents faster.</span>
                  </h2>
                  <p>
                    One workspace to detect, investigate, learn, and prevent
                    the next incident.
                  </p>
                  <div className="banner-buttons">
                    <button
                      className="banner-cta"
                      onClick={() => setShowCreate(true)}
                    >
                      Analyze an incident <ArrowRight size={15} />
                    </button>
                    <button
                      className="banner-secondary"
                      onClick={() => go("Learning")}
                    >
                      Explore learning hub
                    </button>
                  </div>
                </div>

                <div className="banner-visual">
                  <div className="orbit orbit-a" />
                  <div className="orbit orbit-b" />
                  <div className="core-glow">
                    <BrainCircuit size={43} />
                  </div>
                  <div className="float-chip chip-top">
                    <span className="chip-dot green" /> AI ENGINE READY
                  </div>
                  <div className="float-chip chip-bottom">
                    <Activity size={14} /> CONTEXT + MEMORY
                  </div>
                  <div className="float-node node-a"><Database size={17} /></div>
                  <div className="float-node node-b"><ShieldCheck size={17} /></div>
                  <div className="float-node node-c"><Zap size={17} /></div>
                </div>

                <div className="banner-gridline" />
              </section>

              <section className="metrics-grid">
                <MetricCard
                  icon={AlertCircle}
                  label="Total incidents"
                  value={incidents.length}
                  change="Across this workspace"
                  tone="purple"
                  foot="Tracked in this browser"
                />
                <MetricCard
                  icon={Activity}
                  label="Open incidents"
                  value={openCount}
                  change="Awaiting an outcome"
                  tone="orange"
                  foot="Needs investigation"
                />
                <MetricCard
                  icon={CheckCircle2}
                  label="Resolved"
                  value={resolved}
                  change="Verified outcomes"
                  tone="green"
                  foot="Resolution recorded"
                />
                <MetricCard
                  icon={TrendingUp}
                  label="Resolution rate"
                  value={`${successRate}%`}
                  change="Based on tracked incidents"
                  tone="blue"
                  foot="Workspace signal"
                />
              </section>

              <section className="dashboard-grid">
                <div className="panel trend-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Incident activity</h3>
                      <p>Distribution by day of week</p>
                    </div>
                    <span className="panel-tag"><span /> THIS WEEK</span>
                  </div>

                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={trend}
                        margin={{ top: 10, right: 10, left: -24, bottom: 0 }}
                      >
                        <defs>
                          <linearGradient
                            id="incidentFill"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#a78bfa"
                              stopOpacity={0.34}
                            />
                            <stop
                              offset="95%"
                              stopColor="#a78bfa"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid
                          stroke="#282333"
                          strokeDasharray="3 5"
                          vertical={false}
                        />
                        <XAxis
                          dataKey="day"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#827b91", fontSize: 11 }}
                        />
                        <YAxis
                          allowDecimals={false}
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#827b91", fontSize: 11 }}
                        />
                        <Tooltip
                          contentStyle={{
                            background: "#171321",
                            border: "1px solid #3b3150",
                            borderRadius: 10,
                            color: "#fff"
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="incidents"
                          stroke="#a78bfa"
                          strokeWidth={2.5}
                          fill="url(#incidentFill)"
                          activeDot={{
                            r: 5,
                            fill: "#c4b5fd",
                            stroke: "#171321",
                            strokeWidth: 2
                          }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="chart-foot">
                    <span><i className="legend-dot purple-dot" /> Incidents received</span>
                    <span>Local browser activity</span>
                  </div>
                </div>

                <div className="panel category-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Incident categories</h3>
                      <p>Based on incident descriptions</p>
                    </div>
                    <button
                      className="subtle-icon"
                      onClick={() => go("Learning")}
                    >
                      <ArrowUpRight size={16} />
                    </button>
                  </div>

                  <div className="donut-area">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={categories}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={58}
                          outerRadius={81}
                          paddingAngle={4}
                          stroke="none"
                        >
                          {categories.map((entry, index) => (
                            <Cell
                              key={entry.name}
                              fill={[
                                "#a78bfa",
                                "#55d6be",
                                "#f7a76c",
                                "#6ea8fe",
                                "#e879f9"
                              ][index % 5]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: "#171321",
                            border: "1px solid #3b3150",
                            borderRadius: 10,
                            color: "#fff"
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>

                    <div className="donut-center">
                      <strong>{incidents.length}</strong>
                      <small>incidents</small>
                    </div>
                  </div>

                  <div className="category-legend">
                    {categories.slice(0, 4).map((c, i) => (
                      <div key={c.name}>
                        <span>
                          <i
                            style={{
                              background: [
                                "#a78bfa",
                                "#55d6be",
                                "#f7a76c",
                                "#6ea8fe"
                              ][i]
                            }}
                          />
                          {c.name}
                        </span>
                        <b>{c.value}</b>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="panel recent-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Recent incidents</h3>
                    <p>Latest activity across your workspace</p>
                  </div>
                  <button className="text-button" onClick={() => go("Incidents")}>
                    View all <ArrowRight size={14} />
                  </button>
                </div>
                <IncidentList items={incidents.slice(0, 4)} onSelect={setSelected} />
              </section>
            </>
          )}


          {page === "Incidents" && (
            <section className="panel incidents-panel">
              <div className="panel-heading">
                <div>
                  <h3>All incidents</h3>
                  <p>{incidents.length} incidents tracked in this browser session</p>
                </div>
                <div className="table-actions">
                  <div className="search-box">
                    <Search size={15} />
                    <input
                      value={query}
                      onChange={e => setQuery(e.target.value)}
                      placeholder="Search incidents..."
                    />
                  </div>
                  <button className="outline-button" onClick={exportReport}>
                    <Download size={15} /> Export CSV
                  </button>
                </div>
              </div>
              <IncidentList items={filtered} onSelect={setSelected} />
            </section>
          )}

          {page === "Learning" && (
            <LearningPage
              learning={learning}
              incidents={incidents}
              onGoIncidents={() => go("Incidents")}
            />
          )}

          {page === "Reports" && (
            <>
              <section className="metrics-grid">
                <MetricCard icon={Layers3} label="Tracked records" value={incidents.length} tone="purple" foot="Current browser dataset" />
                <MetricCard icon={CheckCircle2} label="Resolved records" value={resolved} tone="green" foot="Resolution submitted" />
                <MetricCard icon={Clock3} label="Still open" value={openCount} tone="orange" foot="No final outcome recorded" />
                <MetricCard icon={TrendingUp} label="Resolution rate" value={`${successRate}%`} tone="blue" foot="Resolved / total" />
              </section>

              <section className="panel report-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Export your incident report</h3>
                    <p>Download a CSV snapshot of the records currently shown in this browser.</p>
                  </div>
                  <button className="primary-button" onClick={exportReport}>
                    <Download size={16} /> Download CSV
                  </button>
                </div>
                <p className="muted-note">
                  Note: this report includes live incidents submitted from this browser and clearly labelled demo examples. It is not a complete export of the server database.
                </p>
              </section>
            </>
          )}

          {page === "Integrations" && (
            <div className="integration-grid">
              <IntegrationCard icon={Bot} name="Groq AI" status="Configured on backend" desc="Generates incident analysis and step-by-step remediation guidance." />
              <IntegrationCard icon={BrainCircuit} name="Hindsight" status="Configured on backend" desc="Recalls relevant historical context and stores incident outcomes." />
              <IntegrationCard icon={Database} name="SQLite" status="Backend storage" desc="Stores incident records and links resolutions to their original incident IDs." />
              <IntegrationCard icon={Cloud} name="FastAPI" status={apiState === "online" ? "Connected" : "Not reachable"} desc={`API base URL: ${API_BASE}`} />
            </div>
          )}

          {page === "Documentation" && (
            <section className="panel guide-panel">
              <div className="panel-heading">
                <div>
                  <h3>RunBook AI response loop</h3>
                  <p>How to use the workspace safely and effectively</p>
                </div>
                <BookOpen size={20} className="muted-icon" />
              </div>

              <div className="guide-steps">
                {[
                  {
                    n: "01",
                    t: "Submit an incident",
                    d: "Describe the service, symptoms, impact, and any known timeline. Avoid secrets, passwords, or personal data."
                  },
                  {
                    n: "02",
                    t: "Review the AI plan",
                    d: "Groq produces a response plan with immediate mitigation, diagnosis, and preventive actions. Treat it as guidance—not an autonomous production change."
                  },
                  {
                    n: "03",
                    t: "Investigate and act",
                    d: "A human responder validates each recommendation and performs approved operational changes."
                  },
                  {
                    n: "04",
                    t: "Record the outcome",
                    d: "Submit the actual resolution or failure details. The backend links the outcome to the original incident and stores it in Hindsight."
                  },
                  {
                    n: "05",
                    t: "Learn and improve",
                    d: "Use the Learning dashboard to inspect recurring categories and turn verified outcomes into better runbooks."
                  }
                ].map(s => (
                  <div className="guide-step" key={s.n}>
                    <span>{s.n}</span>
                    <div>
                      <b>{s.t}</b>
                      <p>{s.d}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <footer className="footer">
          <span>RUNBOOK AI <i /> BUILT FOR THE ENGINEERS ON CALL</span>
          <span>AI-assisted · Human-approved response</span>
        </footer>
      </main>

      {selected && (
        <div
          className="drawer-backdrop"
          onMouseDown={e => {
            if (e.target === e.currentTarget) setSelected(null);
          }}
        >
          <aside className="detail-drawer">
            <div className="drawer-head">
              <div>
                <span className="eyebrow">INCIDENT DETAIL</span>
                <h2>{shortId(selected.incident_id)}</h2>
              </div>
              <button className="icon-button" onClick={() => setSelected(null)}>
                <X size={19} />
              </button>
            </div>

            <StatusPill status={selected.resolution_status || selected.status} />

            <h3 className="detail-title">{selected.description}</h3>

            <div className="detail-meta">
              <span><Clock3 size={14} /> {timeAgo(selected.created_at)}</span>
              <span><Database size={14} /> {categoryOf(selected.description)}</span>
            </div>

            <div className="detail-section">
              <div className="detail-section-title">
                <Sparkles size={15} /> RUNBOOK AI INVESTIGATION & REMEDIATION
              </div>
              <div className="plan-text"><ReactMarkdown>{selected.remediation_plan || ""}</ReactMarkdown></div>
            </div>

            <div className="detail-section incident-assistant">
              <div className="detail-section-title">
                <Sparkles size={15} /> CONTINUE WITH RUNBOOK AI
              </div>
              <p className="muted-note">
                Ask follow-up questions or request an operation. RunBook AI
                uses this incident's context. System-changing actions require
                human approval.
              </p>
              <div className="incident-chat-history">
                {assistantMessages.filter(entry => entry.incidentId === selected.incident_id).length === 0 ? (
                  <p className="muted-note">Your conversation about this incident will appear here.</p>
                ) : assistantMessages
                  .filter(entry => entry.incidentId === selected.incident_id)
                  .map((entry, index) => (
                    <div className={`incident-chat-message ${entry.role}`} key={`${entry.incidentId}-${index}`}>
                      <b>{entry.role === "user" ? "YOU" : "RUNBOOK AI"}</b>
                      <p>{entry.text}</p>
                      {entry.approvalId && (
                        <div className="incident-approval-controls">
                          <small>Approval reference: {entry.approvalId}</small>
                          {entry.approvalStatus === "pending" ? (
                            <>
                              <p className="approval-pending-label">Approval pending — {entry.riskLevel || "unspecified"} risk</p>
                              <div className="incident-approval-actions">
                                <button
                                  type="button"
                                  className="approval-approve-button"
                                  disabled={entry.approvalBusy}
                                  onClick={() => decideIncidentApproval(entry.approvalId, "approved")}
                                >
                                  {entry.approvalBusy ? "Recording…" : "Approve"}
                                </button>
                                <button
                                  type="button"
                                  className="approval-reject-button"
                                  disabled={entry.approvalBusy}
                                  onClick={() => decideIncidentApproval(entry.approvalId, "rejected")}
                                >
                                  Reject
                                </button>
                              </div>
                            </>
                          ) : entry.approvalStatus ? (
                            <p className="approval-decision-label">
                              Decision: {entry.approvalStatus.toUpperCase()}.
                              {" "}No infrastructure operation was executed.
                            </p>
                          ) : null}
                        </div>
                      )}
                    </div>
                  ))}
                {sendingAssistantMessage && (
                  <div className="incident-chat-message assistant">
                    <b>RUNBOOK AI</b><p>Reviewing incident context…</p>
                  </div>
                )}
              </div>
              <form onSubmit={sendIncidentMessage} className="incident-chat-form">
                <textarea
                  value={assistantInput}
                  onChange={e => setAssistantInput(e.target.value)}
                  placeholder="Ask about this incident or request an action…"
                  rows={3}
                  minLength={5}
                  maxLength={5000}
                  disabled={sendingAssistantMessage || selected.demo}
                />
                <button
                  className="primary-button full-button"
                  type="submit"
                  disabled={sendingAssistantMessage || selected.demo || assistantInput.trim().length < 5}
                >
                  {sendingAssistantMessage ? "Thinking…" : "Send to RunBook AI"}
                </button>
              </form>
              {selected.demo && (
                <p className="muted-note">This sample incident is read-only. Create a live incident to start a conversation.</p>
              )}
            </div>

            {selected.resolution_status ? (
              <div className="resolution-saved">
                <CheckCircle2 size={17} />
                <div>
                  <b>Outcome recorded: {selected.resolution_status}</b>
                  <p>
                    {selected.resolution_details ||
                      "Resolution was recorded for this incident."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="detail-section resolution-form">
                <div className="detail-section-title">
                  <CheckCircle2 size={15} /> RECORD OUTCOME
                </div>

                {selected.demo && (
                  <p className="muted-note">
                    This is sample data. Submit a new live incident to test
                    resolution tracking with your backend.
                  </p>
                )}

                <label>Outcome</label>
                <select
                  value={resolutionStatus}
                  onChange={e => setResolutionStatus(e.target.value)}
                >
                  <option value="resolved">Resolved</option>
                  <option value="failed">Unresolved / failed</option>
                </select>

                <label>What actually happened?</label>
                <textarea
                  value={resolutionText}
                  onChange={e => setResolutionText(e.target.value)}
                  placeholder="Describe the verified fix, checks performed, and final outcome..."
                  rows={4}
                />

                <button
                  className="primary-button full-button"
                  onClick={recordResolution}
                  disabled={savingResolution || selected.demo}
                >
                  {savingResolution ? "Saving..." : "Save resolution"}
                  <ArrowRight size={15} />
                </button>
              </div>
            )}
          </aside>
        </div>
      )}

      {showCreate && (
        <div
          className="modal-backdrop"
          onMouseDown={e => {
            if (e.target === e.currentTarget) setShowCreate(false);
          }}
        >
          <div className="create-modal">
            <div className="modal-head">
              <div>
                <span className="eyebrow">
                  <Sparkles size={13} /> AI INCIDENT INTAKE
                </span>
                <h2>What happened?</h2>
                <p>Give RunBook AI the signal. It will bring the context.</p>
              </div>

              <button
                className="icon-button"
                onClick={() => setShowCreate(false)}
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={createIncident}>
              <label htmlFor="incident-description">
                Incident description
              </label>

              <textarea
                id="incident-description"
                autoFocus
                rows={6}
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Example: Payment API requests are timing out. Database connection pool is at 100% capacity after the latest deployment..."
                required
                minLength={5}
              />

              {/* Screenshot and log upload controls */}
              <div className="upload-section">
                <label htmlFor="incident-images">
                  <FileText size={15} /> Upload screenshots
                </label>

                <input
                  id="incident-images"
                  type="file"
                  accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                  multiple
                  onChange={e =>
                    setImageFiles(Array.from(e.target.files || []))
                  }
                />

                <small>
                  PNG, JPG or JPEG · Maximum 3 images · 6 MB each
                </small>

                <label htmlFor="incident-logs">
                  <Terminal size={15} /> Upload log files
                </label>

                <input
                  id="incident-logs"
                  type="file"
                  accept=".txt,.log,text/plain"
                  multiple
                  onChange={e =>
                    setLogFiles(Array.from(e.target.files || []))
                  }
                />

                <small>
                  TXT or LOG · Maximum 10 files · 1 MB each
                </small>

                {(imageFiles.length > 0 || logFiles.length > 0) && (
                  <p className="upload-count">
                    {imageFiles.length} screenshot(s) and {logFiles.length} log file(s) selected.
                  </p>
                )}
              </div>

              <div className="form-hint">
                <ShieldCheck size={14} />
                Include symptoms, affected service, impact, and timeline.
                Do not include credentials or secrets.
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="outline-button"
                  onClick={() => {
                    setShowCreate(false);
                    setImageFiles([]);
                    setLogFiles([]);
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={submitting || description.trim().length < 5}
                >
                  {submitting ? (
                    <>
                      <span className="spinner" /> Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} /> Analyze with AI
                    </>
                  )}
                </button>
              </div>
            </form>

            <div className="modal-api">
              <span
                className={apiState === "online" ? "green-dot" : "orange-dot"}
              />
              {apiState === "online"
                ? "Connected to RunBook API"
                : "API connection required"}
              {" "}· Groq + Hindsight run server-side
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="toast">
          <CheckCircle2 size={17} />
          {toast}
          <button onClick={() => setToast("")}>
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}

function IncidentList({ items, onSelect }) {
  if (!items.length) {
    return (
      <div className="empty-state">
        <Search size={24} />
        <b>No incidents found</b>
        <span>Try a different search or create a new incident.</span>
      </div>
    );
  }

  return (
    <div className="incident-list">
      {items.map(item => (
        <button
          className="incident-row"
          key={item.incident_id}
          onClick={() => onSelect(item)}
        >
          <div
            className={`incident-type-icon type-${categoryOf(item.description)
              .split(" ")[0]
              .toLowerCase()}`}
          >
            <AlertCircle size={17} />
          </div>

          <div className="incident-main">
            <b>{item.description}</b>
            <span>
              {shortId(item.incident_id)} <i /> {categoryOf(item.description)}
              <i /> {timeAgo(item.created_at)}
            </span>
          </div>

          <StatusPill status={item.resolution_status || item.status} />
          <ArrowRight className="row-arrow" size={16} />
        </button>
      ))}
    </div>
  );
}


function LearningPage({ learning, incidents, onGoIncidents }) {
  const resolved = incidents.filter(
    i => i.resolution_status === "resolved"
  ).length;

  return (
    <div className="learning-page">
      <section className="learning-hero">
        <div className="learning-hero-icon">
          <BrainCircuit size={27} />
        </div>

        <div>
          <span className="eyebrow">
            CONTINUOUS ENGINEERING INTELLIGENCE
          </span>
          <h2>
            Don't just resolve incidents.
            <br />
            <span>Get better at preventing them.</span>
          </h2>
          <p>
            RunBook turns incident activity into a learning loop. These
            insights are calculated from the records currently available
            in this browser.
          </p>
        </div>

        <div className="learning-score">
          <span>LEARNING SIGNAL</span>
          <strong>
            {incidents.length
              ? Math.min(99, 35 + resolved * 12 + learning.length * 7)
              : 0}
            <small>/100</small>
          </strong>
          <em>Illustrative workspace score</em>
        </div>
      </section>

      <div className="learning-stats">
        <div className="learning-stat">
          <span>Incident records</span>
          <b>{incidents.length}</b>
          <small>Available in this browser</small>
        </div>
        <div className="learning-stat">
          <span>Verified outcomes</span>
          <b>{resolved}</b>
          <small>Marked resolved</small>
        </div>
        <div className="learning-stat">
          <span>Categories seen</span>
          <b>{learning.length}</b>
          <small>Keyword-based grouping</small>
        </div>
      </div>

      <section className="learning-grid">
        <div className="panel learning-categories">
          <div className="panel-heading">
            <div>
              <h3>What your incidents are teaching</h3>
              <p>Recurring themes from submitted descriptions</p>
            </div>
            <BrainCircuit size={18} className="muted-icon" />
          </div>

          {learning.length ? (
            learning.map(g => (
              <div className="learning-category" key={g.category}>
                <div className="learning-cat-icon">
                  <Activity size={16} />
                </div>
                <div className="learning-cat-copy">
                  <b>{g.category}</b>
                  <span>
                    {g.count} record{g.count === 1 ? "" : "s"} · {g.resolved} resolved
                  </span>
                  <div className="progress-track">
                    <i
                      style={{
                        width: `${Math.round(
                          (g.count / Math.max(1, incidents.length)) * 100
                        )}%`
                      }}
                    />
                  </div>
                </div>
                <strong>
                  {Math.round(
                    (g.count / Math.max(1, incidents.length)) * 100
                  )}%
                </strong>
              </div>
            ))
          ) : (
            <div className="empty-state">
              Submit incidents to start building learning insights.
            </div>
          )}
        </div>

        <div className="panel playbook-panel">
          <div className="panel-heading">
            <div>
              <h3>Field notes</h3>
              <p>Practical habits for incident responders</p>
            </div>
            <BookOpen size={18} className="muted-icon" />
          </div>

          <div className="field-note">
            <span>01 / TRIAGE</span>
            <b>Stabilize before you optimize</b>
            <p>
              Confirm customer impact, establish a timeline, and apply the
              smallest safe mitigation before attempting a broad fix.
            </p>
          </div>

          <div className="field-note">
            <span>02 / DIAGNOSIS</span>
            <b>Follow evidence, not assumptions</b>
            <p>
              Correlate logs, metrics, traces, and recent changes. Record
              what rules out each hypothesis.
            </p>
          </div>

          <div className="field-note">
            <span>03 / LEARNING</span>
            <b>Close the feedback loop</b>
            <p>
              Only record a resolution after a human verifies the outcome.
              Capture the cause, fix, and prevention task.
            </p>
          </div>
        </div>
      </section>

      <section className="panel lessons-panel">
        <div className="panel-heading">
          <div>
            <h3>Incident-to-lesson library</h3>
            <p>Open a record to review its AI plan and outcome</p>
          </div>
          <button className="text-button" onClick={onGoIncidents}>
            Browse incidents <ArrowRight size={14} />
          </button>
        </div>

        <div className="lesson-list">
          {incidents.length === 0 ? (
            <div className="empty-state">
              No lessons yet. Submit an incident to start building your learning library.
            </div>
          ) : incidents.slice(0, 5).map((item, i) => (
            <div className="lesson-row" key={item.incident_id}>
              <div className="lesson-number">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div>
                <b>{categoryOf(item.description)} pattern</b>
                <p>{item.description}</p>
              </div>
              <span
                className={`lesson-outcome ${item.resolution_status || "open"}`}
              >
                {item.resolution_status || "open"}
              </span>
            </div>
          ))}
        </div>
      </section>

      <div className="learning-disclaimer">
        <CircleHelp size={15} />
        Learning insights are heuristic summaries of browser-visible records,
        not verified root-cause analytics. Hindsight stores memory server-side;
        a future memory-search endpoint can enrich this page.
      </div>
    </div>
  );
}

function IntegrationCard({ icon: Icon, name, status, desc }) {
  return (
    <div className="panel integration-card">
      <div className="integration-icon">
        <Icon size={20} />
      </div>
      <div>
        <b>{name}</b>
        <span>{status}</span>
        <p>{desc}</p>
      </div>
      <CheckCircle2 size={17} className="integration-check" />
    </div>
  );
}

export default App;
