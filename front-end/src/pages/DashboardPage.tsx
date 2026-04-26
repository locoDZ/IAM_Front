import { motion } from "motion/react";
import {
  LayoutDashboard,
  BarChart3,
  Users,
  TrendingUp,
  Wallet,
  Target,
  LogOut,
  ChevronRight
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { useEffect, useState } from "react";

const options = [
  {
    id: "HR",
    title: "HR",
    description: "Employee records and company announcements.",
    icon: Users,
    gradient: "from-blue-500 to-indigo-600"
  },
  {
    id: "Finance",
    title: "Finance",
    description: "Budget reports and financial invoices.",
    icon: Wallet,
    gradient: "from-emerald-500 to-teal-600"
  },
  {
    id: "IT",
    title: "IT",
    description: "System configurations and incident logs.",
    icon: BarChart3,
    gradient: "from-purple-500 to-violet-600"
  },
  {
    id: "Operations",
    title: "Operations",
    description: "Workflow documents and supply chain data.",
    icon: TrendingUp,
    gradient: "from-orange-500 to-rose-600"
  }
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem("user") || "{}");

  const [users, setUsers] = useState<Record<string, any>>({});

  const fetchUsers = async () => {
    const resp = await fetch("http://localhost:8000/api/users");
    const data = await resp.json();
    setUsers(data);
  };

  useEffect(() => {
    if (user.role === "Admin") fetchUsers();
  }, [user.role]);

  const [showUserPanel, setShowUserPanel] = useState(false);
  const [newUser, setNewUser] = useState({
    username: "", password: "", role: "Employee",
    department: "HR", clearance: "public"
  });
  const [userMsg, setUserMsg] = useState<{ text: string, success: boolean } | null>(null);

  const handleCreateUser = async () => {
    const tgt = sessionStorage.getItem("tgt");
    try {
      const resp = await fetch("http://localhost:8000/api/users/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newUser),
      });
      const data = await resp.json();
      setUserMsg({ text: resp.ok ? `User '${newUser.username}' created` : data.detail, success: resp.ok });
    } catch {
      setUserMsg({ text: "Connection error", success: false });
    }
  };

  const handleDeleteUser = async (username: string) => {
    try {
      const resp = await fetch(`http://localhost:8000/api/users/${username}`, { method: "DELETE" });
      const data = await resp.json();
      setUserMsg({ text: resp.ok ? `User '${username}' deleted` : data.detail, success: resp.ok });
    } catch {
      setUserMsg({ text: "Connection error", success: false });
    }
  };

  const handleDepartmentClick = async (departmentId: string) => {
    const tgt = sessionStorage.getItem("tgt");
    try {
      const resp = await fetch("http://localhost:8000/api/request-ticket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tgt_token: tgt,
          service: `${departmentId.toLowerCase()}_service`
        }),
      });
      const data = await resp.json();
      sessionStorage.setItem("service_ticket", data.service_ticket);
      navigate(`/department/${departmentId}`);
    } catch (err) {
      console.error("Failed to get service ticket", err);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#fafafa]">
      {/* Header */}
      <header className="h-16 border-b border-zinc-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto h-full px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-black rounded flex items-center justify-center">
              <LayoutDashboard className="text-white w-5 h-5" />
            </div>
            <span className="font-bold text-lg tracking-tight">PORTAL</span>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex flex-col items-end mr-2">
              <span className="text-sm font-semibold">{user.name || "Administrator"}</span>

            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-zinc-500 hover:text-red-500">
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="mb-12">
          <motion.h2
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-3xl font-bold text-zinc-900 tracking-tight"
          >
            Welcome back, {user.name?.split(' ')[0] || "User"}
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="text-zinc-500 mt-2"
          >
            Select a department to view detailed analytics and management tools.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {options.map((option, index) => (
            <motion.div
              key={option.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * (index + 1) }}
              whileHover={{ y: -5 }}
              className="group relative bg-white border border-zinc-200 rounded-3xl p-8 hover:shadow-2xl hover:shadow-zinc-200/50 transition-all cursor-pointer overflow-hidden"
              onClick={() => handleDepartmentClick(option.id)}
            >
              <div className={`w-14 h-14 rounded-2xl mb-6 flex items-center justify-center bg-gradient-to-br ${option.gradient} text-white shadow-lg`}>
                <option.icon className="w-7 h-7" />
              </div>

              <h3 className="text-xl font-bold text-zinc-900 mb-3">{option.title}</h3>
              <p className="text-zinc-500 text-sm leading-relaxed mb-6">
                {option.description}
              </p>

              <div className="flex items-center text-sm font-semibold text-zinc-900 group-hover:gap-2 transition-all">
                Enter Department
                <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-all" />
              </div>

              {/* Decorative graphic */}
              <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-zinc-50 rounded-full blur-3xl group-hover:bg-opacity-50 transition-all opacity-20" />
            </motion.div>
          ))}
        </div>
        {user.role === "Admin" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-8 bg-white border border-zinc-200 rounded-3xl p-8"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-zinc-900">User Management</h3>
              <button
                onClick={() => setShowUserPanel(!showUserPanel)}
                className="text-sm text-zinc-500 hover:text-zinc-900 transition-colors"
              >
                {showUserPanel ? "Hide" : "Add User"}
              </button>
            </div>

            {showUserPanel && (
              <div className="grid grid-cols-2 gap-3 mb-4">
                <input placeholder="Username" value={newUser.username}
                  onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                  className="border border-zinc-200 rounded-lg px-3 py-2 text-sm" />
                <input placeholder="Password" type="password" value={newUser.password}
                  onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                  className="border border-zinc-200 rounded-lg px-3 py-2 text-sm" />
                <select value={newUser.role}
                  onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                  className="border border-zinc-200 rounded-lg px-3 py-2 text-sm">
                  <option>Admin</option>
                  <option>Manager</option>
                  <option>Employee</option>
                </select>
                <select value={newUser.department}
                  onChange={e => setNewUser({ ...newUser, department: e.target.value })}
                  className="border border-zinc-200 rounded-lg px-3 py-2 text-sm">
                  <option>HR</option>
                  <option>Finance</option>
                  <option>IT</option>
                  <option>Operations</option>
                </select>
                <select value={newUser.clearance}
                  onChange={e => setNewUser({ ...newUser, clearance: e.target.value })}
                  className="border border-zinc-200 rounded-lg px-3 py-2 text-sm">
                  <option value="public">Public</option>
                  <option value="confidential">Confidential</option>
                  <option value="secret">Secret</option>
                </select>
                <button onClick={handleCreateUser}
                  className="bg-black text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-zinc-800 transition-colors">
                  Create User
                </button>
              </div>
            )}

            {userMsg && (
              <div className={`text-sm px-4 py-2 rounded-lg mb-4 ${userMsg.success ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                }`}>
                {userMsg.text}
              </div>
            )}

            <div className="text-xs text-zinc-400 mt-2">
              <div className="mt-4 space-y-2">
                {Object.entries(users).map(([username, data]: [string, any]) => (
                  <div key={username} className="flex items-center justify-between px-4 py-2 bg-zinc-50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sm text-zinc-900">{username}</span>
                      <span className="text-xs text-zinc-500">{data.role} · {data.department}</span>
                    </div>
                    <button
                      onClick={() => handleDeleteUser(username).then(fetchUsers)}
                      className="text-xs text-red-500 hover:text-red-700 transition-colors font-medium"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

      </main>
    </div>
  );
}
