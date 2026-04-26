import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, ShieldAlert, ShieldCheck, ChevronDown, ChevronUp, Zap } from "lucide-react";

const ATTACKS = [
  {
    id: "asrep",
    name: "AS-REP Roasting",
    type: "Centralized",
    description: "Request a TGT for users with pre-authentication disabled — no password needed.",
    fields: [{ key: "username", label: "Target Username", placeholder: "carol or dave", type: "text" }],
    endpoint: "asrep",
    fix: "Secure /login requires password verification for all users.",
  },
  {
    id: "kerberoast",
    name: "Kerberoasting",
    type: "Centralized",
    description: "Request service tickets encrypted with weak static keys — crackable offline.",
    fields: [
      { key: "username", label: "Username", placeholder: "alice", type: "text" },
      { key: "password", label: "Password", placeholder: "123", type: "password" },
    ],
    endpoint: "kerberoast",
    fix: "Secure tickets use strong randomly generated session keys.",
  },
  {
    id: "golden",
    name: "Golden Ticket",
    type: "Centralized",
    description: "Expose the krbtgt secret then forge a TGT for any user with any role and 10-year expiry.",
    fields: [
      { key: "username", label: "Target Username", placeholder: "any username", type: "text" },
      { key: "role", label: "Forged Role", placeholder: "Admin", type: "text" },
    ],
    endpoint: "golden",
    fix: "krbtgt secret never exposed in secure mode. No such endpoint exists.",
  },
  {
    id: "silver",
    name: "Silver Ticket",
    type: "Centralized",
    description: "Forge a service ticket using weak service keys — no KDC interaction needed.",
    fields: [
      { key: "username", label: "Username", placeholder: "attacker", type: "text" },
      { key: "role", label: "Forged Role", placeholder: "Admin", type: "text" },
      { key: "department", label: "Department", placeholder: "IT", type: "text" },
      { key: "clearance", label: "Clearance", placeholder: "secret", type: "text" },
      { key: "service", label: "Service", placeholder: "hr_service", type: "text" },
    ],
    endpoint: "silver",
    fix: "Resource Server always validates tickets with KDC — forged tickets rejected by HMAC.",
  },
  {
    id: "replay",
    name: "Replay Attack",
    type: "Decentralized",
    description: "Reuse an already-used service ticket — no replay protection in vulnerable endpoint.",
    fields: [{ key: "service_ticket", label: "Service Ticket", placeholder: "paste a service ticket", type: "text" }],
    endpoint: "replay",
    fix: "Secure endpoint tracks used ticket IDs and rejects any reuse.",
  },
  {
    id: "tamper",
    name: "Ticket Tampering",
    type: "Centralized",
    description: "Modify a valid service ticket to change the role — attempt privilege escalation.",
    fields: [
      { key: "service_ticket", label: "Valid Service Ticket", placeholder: "paste a service ticket", type: "text" },
      { key: "role", label: "Forged Role", placeholder: "Admin", type: "text" },
    ],
    endpoint: "tamper",
    fix: "Fernet HMAC detects any modification and rejects tampered tickets.",
  },
  {
    id: "dcsync",
    name: "Privilege Escalation (DCSync)",
    type: "Centralized",
    description: "Send role=Admin in request body to dump all user hashes — role never verified via ticket.",
    fields: [{ key: "role", label: "Claimed Role", placeholder: "Admin", type: "text" }],
    endpoint: "dcsync",
    fix: "Role must be extracted from a validated KDC ticket, not from user-controlled input.",
  },
  {
    id: "unauthorized",
    name: "Unauthorized Access",
    type: "Decentralized",
    description: "Access a resource endpoint with no ticket at all — authentication completely bypassed.",
    fields: [],
    endpoint: "unauthorized",
    fix: "Every endpoint must validate a service ticket before returning any data.",
  },
];

const TYPE_COLORS: Record<string, string> = {
  Centralized: "bg-blue-100 text-blue-700 border-blue-200",
  Decentralized: "bg-purple-100 text-purple-700 border-purple-200",
};

export default function AttackPage() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem("user") || "{}");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, Record<string, string>>>({});
  const [results, setResults] = useState<Record<string, { success: boolean; data: any } | null>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  if (user.role !== "Admin") {
    navigate("/dashboard");
    return null;
  }

  const setField = (attackId: string, key: string, value: string) => {
    setFields(prev => ({
      ...prev,
      [attackId]: { ...(prev[attackId] || {}), [key]: value }
    }));
  };

  const runAttack = async (attack: typeof ATTACKS[0]) => {
    setLoading(prev => ({ ...prev, [attack.id]: true }));
    setResults(prev => ({ ...prev, [attack.id]: null }));

    const payload: Record<string, string> = {
      type: attack.endpoint,
      ...(fields[attack.id] || {})
    };

    try {
      const resp = await fetch("http://localhost:8000/api/attack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      setResults(prev => ({ ...prev, [attack.id]: { success: resp.ok, data } }));
    } catch {
      setResults(prev => ({ ...prev, [attack.id]: { success: false, data: { error: "Connection error" } } }));
    } finally {
      setLoading(prev => ({ ...prev, [attack.id]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center gap-4">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-zinc-400 hover:text-white transition-colors flex items-center gap-2 text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <div className="h-4 w-px bg-zinc-700" />
          <span className="font-mono text-sm text-red-400 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4" />
            Attack Simulation
          </span>
          <span className="ml-auto text-xs text-zinc-500 font-mono">Admin only · {user.username}</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight">IAM Attack Simulation</h1>
          <p className="text-zinc-500 text-sm mt-1">
            8 attacks demonstrated: 6 centralized (Kerberos) + 2 decentralized (token-based).
            Each shows the exploit and its mitigation.
          </p>
        </motion.div>

        <div className="space-y-3">
          {ATTACKS.map((attack, index) => {
            const result = results[attack.id];
            const isExpanded = expanded === attack.id;
            const isLoading = loading[attack.id];

            return (
              <motion.div
                key={attack.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden"
              >
                {/* Attack Header */}
                <button
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
                  onClick={() => setExpanded(isExpanded ? null : attack.id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-red-950 rounded-lg flex items-center justify-center shrink-0">
                      <Zap className="w-4 h-4 text-red-400" />
                    </div>
                    <div className="text-left">
                      <p className="font-semibold text-sm">{attack.name}</p>
                      <p className="text-xs text-zinc-500 mt-0.5">{attack.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 ml-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${TYPE_COLORS[attack.type]}`}>
                      {attack.type}
                    </span>
                    {result && (
                      <span className={`text-xs font-mono ${result.success ? "text-emerald-400" : "text-red-400"}`}>
                        {result.success ? "✓ Done" : "✗ Error"}
                      </span>
                    )}
                    {isExpanded
                      ? <ChevronUp className="w-4 h-4 text-zinc-500" />
                      : <ChevronDown className="w-4 h-4 text-zinc-500" />
                    }
                  </div>
                </button>

                {/* Expanded Panel */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="border-t border-zinc-800"
                    >
                      <div className="px-6 py-5 space-y-4">
                        {/* Fields */}
                        {attack.fields.length > 0 && (
                          <div className="grid grid-cols-2 gap-3">
                            {attack.fields.map(field => (
                              <div key={field.key}>
                                <label className="text-xs text-zinc-400 mb-1 block">{field.label}</label>
                                <input
                                  type={field.type}
                                  placeholder={field.placeholder}
                                  value={fields[attack.id]?.[field.key] || ""}
                                  onChange={e => setField(attack.id, field.key, e.target.value)}
                                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-red-500 transition-colors"
                                />
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Execute button */}
                        <button
                          onClick={() => runAttack(attack)}
                          disabled={isLoading}
                          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
                        >
                          {isLoading ? (
                            <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          ) : (
                            <Zap className="w-3 h-3" />
                          )}
                          Execute Attack
                        </button>

                        {/* Fix */}
                        <div className="flex items-start gap-2 bg-emerald-950/40 border border-emerald-900 rounded-xl px-4 py-3">
                          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                          <div>
                            <p className="text-xs font-semibold text-emerald-400 mb-0.5">Mitigation</p>
                            <p className="text-xs text-emerald-300/70">{attack.fix}</p>
                          </div>
                        </div>

                        {/* Result */}
                        <AnimatePresence>
                          {result && (
                            <motion.div
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              className="bg-zinc-800 rounded-xl p-4"
                            >
                              <p className="text-xs text-zinc-400 mb-2 font-mono uppercase tracking-widest">Response</p>
                              <pre className="text-xs text-zinc-300 overflow-auto max-h-56 whitespace-pre-wrap break-all">
                                {JSON.stringify(result.data, null, 2)}
                              </pre>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
