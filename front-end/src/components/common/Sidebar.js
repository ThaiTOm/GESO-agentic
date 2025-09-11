import { NavLink } from 'react-router-dom';
import { FiGrid, FiMessageSquare, FiHome, FiX } from 'react-icons/fi'; // Add FiX for a close icon
import styles from './Sidebar.module.css';

// 1. Receive 'isOpen' and 'toggleSidebar' as props from AppLayout
const Sidebar = ({ isOpen, toggleSidebar }) => {

    // 2. Create a dynamic class string. If 'isOpen' is true, it adds the 'mobileOpen' class.
    const sidebarClasses = `${styles.sidebar} ${isOpen ? styles.mobileOpen : ''}`;

    return (
        <div className={sidebarClasses}>
            {/* 3. Add a close button, only visible on mobile when open */}
            <button className={styles.closeButton} onClick={toggleSidebar}>
                <FiX />
            </button>
            <div className={styles.logo}>AgentBot</div>
            <nav className={styles.nav}>
                {/* 4. Add 'onClick' to NavLinks to close the sidebar after navigation on mobile */}
                <NavLink to="/admin" onClick={toggleSidebar} className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
                    <FiGrid /><span>Tổng quan</span>
                </NavLink>
                <NavLink to="/chat" onClick={toggleSidebar} className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
                    <FiMessageSquare /><span>Chat</span>
                </NavLink>
            </nav>
            <div className={styles.footer}>
                <NavLink to="/" onClick={toggleSidebar} className={styles.navLink}>
                    <FiHome /><span>Về trang chủ</span>
                </NavLink>
            </div>
        </div>
    );
};
export default Sidebar;