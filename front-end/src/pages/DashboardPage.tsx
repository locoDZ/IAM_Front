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

const options = [
  {
    id: "management",
    title: "Management",
    description: "Overview of operations, team performance, and strategic planning tools.",
    icon: Users,
    color: "bg-blue-500",
    gradient: "from-blue-500 to-indigo-600"
  },
  {
    id: "finance",
    title: "Finance",
    description: "Budget tracking, financial reporting, and revenue analytics dashboard.",
    icon: Wallet,
    color: "bg-emerald-500",
    gradient: "from-emerald-500 to-teal-600"
  },
  {
    id: "marketing",
    title: "Marketing",
    description: "Campaign performance, social reach, and customer engagement metrics.",
    icon: TrendingUp,
    color: "bg-orange-500",
    gradient: "from-orange-500 to-rose-600"
  }
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem("user") || "{}");

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
              <span className="text-xs text-zinc-500">{user.email || "admin@example.com"}</span>
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

        {/* Quick Stats Banner */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-12 bg-zinc-900 rounded-3xl p-8 text-white flex flex-col md:flex-row items-center justify-between gap-8"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-lg">Daily Statistics Overview</h4>
              <p className="text-white/60 text-sm">Real-time data synchronization across all departments is active.</p>
            </div>
          </div>
          
          <div className="flex gap-8">
            <div className="text-center">
              <p className="text-white/40 text-[10px] uppercase tracking-widest font-bold mb-1">System Load</p>
              <p className="text-2xl font-mono font-bold">14%</p>
            </div>
            <div className="text-center">
              <p className="text-white/40 text-[10px] uppercase tracking-widest font-bold mb-1">Active Users</p>
              <p className="text-2xl font-mono font-bold">842</p>
            </div>
            <div className="text-center">
              <p className="text-white/40 text-[10px] uppercase tracking-widest font-bold mb-1">API Latency</p>
              <p className="text-2xl font-mono font-bold">12ms</p>
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
