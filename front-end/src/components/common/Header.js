import { Link } from 'react-router-dom';
import styles from './Header.module.css';

export const Header = () => (
    <header className={styles.header}>
        <div className={styles.container}>
            <Link to="/" className={styles.logo}>AgentBot</Link>
            <nav className={styles.nav}>
                <Link to="/admin" className={styles.navLink}>Quản lý</Link>
                <Link to="/chat" className={styles.ctaButton}>Bắt đầu Chat</Link>
            </nav>
        </div>
    </header>
);
export default Header;