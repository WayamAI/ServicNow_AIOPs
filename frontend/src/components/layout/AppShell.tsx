import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Moon, Sun, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Sidebar from './Sidebar';
import LivePanel from './LivePanel';
import StatusBar from './StatusBar';

export default function AppShell() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem('theme');
    return stored ? stored === 'dark' : true;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  return (
    <div className="flex flex-col h-screen bg-background">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b bg-card px-4 py-3 shrink-0">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <span className="font-semibold text-sm">AIOPs Dashboard</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDark(!dark)}
            className="h-8 w-8"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </header>

        {/* 3-column layout */}
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
          <div className="hidden xl:flex">
            <LivePanel />
          </div>
        </div>

        <StatusBar />
      </div>
  );
}
