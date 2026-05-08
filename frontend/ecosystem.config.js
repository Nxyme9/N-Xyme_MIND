module.exports = {
  apps: [
    {
      name: "frontend",
      script: "npm",
      args: "run dev -- --port",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "development",
      },
      env_production: {
        NODE_ENV: "production",
      },
      error_file: "/tmp/frontend-error.log",
      out_file: "/tmp/frontend-out.log",
      log_file: "/tmp/frontend-combined.log",
      time: true,
      restart_delay: 4000,
      max_restarts: 10,
      min_uptime: "10s",
      listen_timeout: 8000,
      kill_timeout: 5000,
      port: 3000,
    },
  ],
};
