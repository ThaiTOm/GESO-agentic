import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/common/Sidebar';
import styles from './AppLayout.module.css'; // We will create this CSS file next

const AppLayout = () => (
  <div className={styles.appLayout}>
    <Sidebar />
    <main className={styles.mainContent}>
      {/* The Outlet is where your ChatInterface will be rendered */}
      <Outlet />
    </main>
  </div>
);

export default AppLayout;