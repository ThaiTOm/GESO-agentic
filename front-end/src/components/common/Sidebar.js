import { NavLink } from 'react-router-dom';
import { FiGrid, FiMessageSquare, FiHome } from 'react-icons/fi';
import styles from './Sidebar.module.css';

const Sidebar = () => {
    return (
        <div className={styles.sidebar}>
            <div className={styles.logo}>AgentBot</div>
            <nav className={styles.nav}>
                <NavLink to="/admin" className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
                    <FiGrid /><span>Tổng quan</span>
                </NavLink>
                <NavLink to="/chat" className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
                    <FiMessageSquare /><span>Chat</span>
                </NavLink>
            </nav>
            <div className={styles.footer}>
                <NavLink to="/" className={styles.navLink}>
                    <FiHome /><span>Về trang chủ</span>
                </NavLink>
            </div>
        </div>
    );
};
export default Sidebar;