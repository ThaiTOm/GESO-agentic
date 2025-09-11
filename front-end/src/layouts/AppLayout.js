import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
// Ensure this path is correct for your project structure
import Sidebar from '../components/common/Sidebar';
import styles from './AppLayout.module.css';
import { FiMenu } from 'react-icons/fi'; // The "hamburger" menu icon

const AppLayout = () => {
    // State to manage sidebar visibility on mobile
    const [isSidebarOpen, setSidebarOpen] = useState(false);

    const toggleSidebar = () => {
        setSidebarOpen(!isSidebarOpen);
    };

    return (
        <div className={styles.appLayout}>
            {/* We pass the state and the toggle function down to the Sidebar */}
            <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

            <main className={styles.mainContent}>
                {/* This button is only visible on mobile (controlled by CSS) */}
                <button className={styles.menuButton} onClick={toggleSidebar}>
                    <FiMenu />
                </button>
                <Outlet />
            </main>

            {/* An overlay that darkens the content when the sidebar is open on mobile */}
            {/* Clicking the overlay will also close the sidebar */}
            {isSidebarOpen && <div className={styles.overlay} onClick={toggleSidebar}></div>}
        </div>
    );
};

export default AppLayout;