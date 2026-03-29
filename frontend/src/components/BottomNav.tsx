/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


import { Link, useLocation } from 'react-router-dom';

export function BottomNav() {
  const location = useLocation();

  const isDashboard = location.pathname === '/';
  // If we ever add more paths, you can check them similarly here

  return (
    <nav className="fixed bottom-0 left-0 w-full flex justify-around items-center px-4 pt-3 pb-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md z-50 rounded-t-3xl shadow-[0_-10px_40px_rgba(25,28,30,0.06)]">
      {/* Dashboard */}
      <Link
        to="/"
        className={`flex flex-col items-center justify-center rounded-xl px-4 py-1 active:scale-90 duration-150 ${isDashboard ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-300'}`}
      >
        <span className="material-symbols-outlined mb-0.5" style={isDashboard ? { fontVariationSettings: "'FILL' 1" } : {}}>dashboard</span>
        <span className="font-['Inter'] text-[11px] font-semibold uppercase tracking-wider">Dashboard</span>
      </Link>

      {/* Applications (Placeholder for now) */}
      <div className="flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 px-4 py-1 hover:text-blue-600 dark:hover:text-blue-300 active:scale-90 duration-150 cursor-not-allowed opacity-50">
        <span className="material-symbols-outlined mb-0.5">description</span>
        <span className="font-['Inter'] text-[11px] font-semibold uppercase tracking-wider">Applications</span>
      </div>

      {/* Profile */}
      <Link
        to="/profile"
        className={`flex flex-col items-center justify-center rounded-xl px-4 py-1 active:scale-90 duration-150 ${location.pathname === '/profile' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-300'}`}
      >
        <span className="material-symbols-outlined mb-0.5" style={location.pathname === '/profile' ? { fontVariationSettings: "'FILL' 1" } : {}}>person</span>
        <span className="font-['Inter'] text-[11px] font-semibold uppercase tracking-wider">Profile</span>
      </Link>
    </nav>
  );
}