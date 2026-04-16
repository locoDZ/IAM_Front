import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Mock authentication endpoint
  app.post("/api/login", (req, res) => {
    const { email, password } = req.body;

    // VERY SIMPLE MOCK CHECK
    // In a real app, this would check a database and return a JWT
    if (email === "admin@example.com" && password === "password123") {
      return res.json({
        success: true,
        user: {
          id: "1",
          email: "admin@example.com",
          name: "Administrator",
        },
      });
    }

    return res.status(401).json({
      success: false,
      message: "Invalid email or password",
    });
  });

  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
