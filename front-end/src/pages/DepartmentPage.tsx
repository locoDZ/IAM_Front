import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft, FileText, Lock, ShieldAlert,
  Eye, Pencil, Trash2, CheckCircle, XCircle, Loader2
} from "lucide-react";
import { Button } from "../components/ui/Button";

// Map department to its resources
const DEPARTMENT_RESOURCES: Record<string, { name: string; label: string; classification: string }[]> = {
  HR: [
    { name: "employee_records", label: "Employee Records", classification: "confidential" },
    { name: "operations_schedule", label: "Public Announcements", classification: "public" },
  ],
  Finance: [
    { name: "financial_reports", label: "Budget Reports", classification: "secret" },
    { name: "operations_schedule", label: "Invoices", classification: "confidential" },
  ],
  IT: [
    { name: "system_logs", label: "System Configurations", classification: "secret" },
    { name: "system_logs", label: "Incident Logs", classification: "confidential" },
  ],
  Operations: [
    { name: "operations_schedule", label: "Workflow Docs", classification: "public" },
    { name: "employee_records", label: "Supply Chain Data", classification: "confidential" },
  ],
};

const CLASSIFICATION_COLORS: Record<string, string> = {
  public: "bg-emerald-100 text-emerald-700 border-emerald-200",
  confidential: "bg-amber-100 text-amber-700 border-amber-200",
  secret: "bg-red-100 text-red-700 border-red-200",
};

type ActionResult = {
  success: boolean;
  message: string;
  content?: string;
};

export default function DepartmentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem("user") || "{}");
  const serviceTicket = sessionStorage.getItem("service_ticket") || "";

  const [results, setResults] = useState<Record<string, ActionResult | null>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [activeResource, setActiveResource] = useState<string | null>(null);

  const resources = DEPARTMENT_RESOURCES[id || ""] || [];

  const performAction = async (resourceName: string, action: "Read" | "Write" | "Delete") => {
    const key = `${resourceName}-${action}`;
    setLoading(prev => ({ ...prev, [key]: true }));
    setResults(prev => ({ ...prev, [key]: null }));

    try {
      const endpoint = action === "Read" ? "/api/resource/read"
        : action === "Write" ? "/api/resource/write"
          : "/api/resource/delete";

      const body: Record<string, string> = {
        service_ticket: serviceTicket,
        name: resourceName,
        action,
      };
      if (action === "Write") body.content = `Updated by ${user.username} at ${new Date().toISOString()}`;

      const resp = await fetch(`http://localhost:8000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await resp.json();

      if (resp.ok) {
        setResults(prev => ({
          ...prev,
          [key]: {
            success: true,
            message: action === "Read" ? "Access granted" : `${action} successful`,
            content: data.content
          }
        }));
      } else {
        let reason = "Access denied";
        try {
          const detail = data.detail;
          if (typeof detail === "string") {
            reason = detail;
          } else if (Array.isArray(detail)) {
            // Pydantic validation error
            reason = detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
          } else if (typeof detail === "object" && detail !== null) {
            reason = detail.reason
              || detail.detail?.reason
              || detail.detail
              || detail.message
              || "Access denied by policy";
          }
        } catch {
          reason = "Access denied";
        }
        setResults(prev => ({
          ...prev,
          [key]: { success: false, message: reason || "Access denied" }
        }));
      }
    } catch (err) {
      setResults(prev => ({
        ...prev,
        [key]: { success: false, message: "Connection error" }
      }));
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center gap-4">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-zinc-400 hover:text-white transition-colors flex items-center gap-2 text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <div className="h-4 w-px bg-zinc-700" />
          <span className="font-mono text-sm text-zinc-300">
            {id} Department
          </span>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-zinc-500 font-mono">
              {user.role} · {user.username}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-2xl font-bold tracking-tight">{id} Resources</h1>
          <p className="text-zinc-500 text-sm mt-1">
            Access controlled by your role and clearance level
          </p>
        </motion.div>

        <div className="space-y-4">
          {resources.map((resource, index) => (
            <motion.div
              key={`${resource.name}-${index}`}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden"
            >
              {/* Resource Header */}
              <div className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-zinc-800 rounded-lg flex items-center justify-center">
                    <FileText className="w-4 h-4 text-zinc-400" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{resource.label}</p>
                    <p className="text-xs text-zinc-500 font-mono">{resource.name}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full border font-medium ${CLASSIFICATION_COLORS[resource.classification]}`}>
                  {resource.classification}
                </span>
              </div>

              {/* Actions */}
              <div className="px-6 pb-4 flex flex-wrap gap-2">
                {[
                  { action: "Read" as const, icon: Eye, label: "Read" },
                  { action: "Write" as const, icon: Pencil, label: "Write" },
                  { action: "Delete" as const, icon: Trash2, label: "Delete" },
                ].map(({ action, icon: Icon, label }) => {
                  const key = `${resource.name}-${action}`;
                  const result = results[key];
                  const isLoading = loading[key];

                  return (
                    <div key={action} className="flex items-center gap-2">
                      <button
                        onClick={() => performAction(resource.name, action)}
                        disabled={isLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white text-xs font-medium transition-all disabled:opacity-50"
                      >
                        {isLoading ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Icon className="w-3 h-3" />
                        )}
                        {label}
                      </button>

                      {/* Result badge */}
                      <AnimatePresence>
                        {result && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.8 }}
                            className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg ${result.success
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : "bg-red-950 text-red-400 border border-red-900"
                              }`}
                          >
                            {result.success
                              ? <CheckCircle className="w-3 h-3" />
                              : <XCircle className="w-3 h-3" />
                            }
                            {result.success ? "Allowed" : "Denied"}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>

              {/* Result detail */}
              <AnimatePresence>
                {Object.entries(results).filter(([k]) => k.startsWith(resource.name) && results[k]).map(([key, result]) => (
                  result && (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className={`mx-6 mb-4 px-4 py-3 rounded-xl text-xs font-mono ${result.success
                        ? "bg-emerald-950/50 text-emerald-300 border border-emerald-900"
                        : "bg-red-950/50 text-red-300 border border-red-900"
                        }`}
                    >
                      <div className="flex items-start gap-2">
                        {result.success
                          ? <CheckCircle className="w-3 h-3 mt-0.5 shrink-0" />
                          : <ShieldAlert className="w-3 h-3 mt-0.5 shrink-0" />
                        }
                        <span>{result.content || (typeof result.message === "string" ? result.message : JSON.stringify(result.message))}</span>
                      </div>
                    </motion.div>
                  )
                ))}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>

        {/* User context panel */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-8 bg-zinc-900 border border-zinc-800 rounded-2xl px-6 py-4"
        >
          <p className="text-xs text-zinc-500 uppercase tracking-widest font-semibold mb-3">Your Access Context</p>
          <div className="flex flex-wrap gap-4 text-sm">
            {[
              { label: "Role", value: user.role },
              { label: "Department", value: user.department },
              { label: "Clearance", value: user.clearance },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center gap-2">
                <span className="text-zinc-500 text-xs">{label}:</span>
                <span className="font-mono text-xs bg-zinc-800 px-2 py-0.5 rounded text-zinc-300">{value}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
