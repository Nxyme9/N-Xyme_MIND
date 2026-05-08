export const dynamic = 'force-static';
import { NextResponse } from "next/server";
import os from "os";

interface SystemStats {
  cpu: number;
  memory: number;
  totalMemory: number;
  freeMemory: number;
  uptime: number;
  timestamp: string;
}

export async function GET(): Promise<NextResponse<SystemStats>> {
  const cpus = os.cpus();
  let totalIdle = 0;
  let totalTick = 0;

  for (const cpu of cpus) {
    for (const type in cpu.times) {
      totalTick += cpu.times[type as keyof typeof cpu.times];
    }
    totalIdle += cpu.times.idle;
  }

  const cpuUsage = Math.floor((1 - totalIdle / totalTick) * 100);
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const memoryUsage = Math.floor(((totalMem - freeMem) / totalMem) * 100);

  const response: SystemStats = {
    cpu: cpuUsage,
    memory: memoryUsage,
    totalMemory: totalMem,
    freeMemory: freeMem,
    uptime: os.uptime(),
    timestamp: new Date().toISOString(),
  };

  return NextResponse.json(response);
}