import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/common/Sidebar';

const AppLayout = () => (
  <div className="flex h-screen bg-slate-100 dark:bg-slate-900">
    <Sidebar />
    <main className="flex-1 flex flex-col overflow-hidden">
      <Outlet />
    </main>
  </div>
);

export default AppLayout;
