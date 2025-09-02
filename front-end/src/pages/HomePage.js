import { Link } from 'react-router-dom';
import Header from '../components/common/Header';
import { Footer } from '../components/common/Footer';
import styles from './HomePage.module.css'; // Import CSS Module

const HomePage = () => {
    return (
        <div className={styles.homePage}>
            <Header />
            <main>
                <section className={styles.heroSection}>
                    <div className={styles.container}>
                        <h1>Agent Chatbot Thông Minh</h1>
                        <p>Giải pháp tự động hóa tương tác, nâng cao trải nghiệm khách hàng.</p>
                        <Link to="/chat" className={styles.ctaButton}>Trải nghiệm ngay</Link>
                    </div>
                </section>
                <section className={styles.featuresSection}>
                    <div className={styles.container}>
                        <h2>Tính năng vượt trội</h2>
                        <div className={styles.featuresGrid}>
                            <div className={styles.featureCard}><h3>Tương tác tự nhiên</h3><p>Chatbot hiểu và trả lời như người thật.</p></div>
                            <div className={styles.featureCard}><h3>Phân tích & Báo cáo</h3><p>Cung cấp báo cáo chi tiết về hiệu suất.</p></div>
                            <div className={styles.featureCard}><h3>Dễ dàng tùy chỉnh</h3><p>Giao diện quản lý trực quan, đơn giản.</p></div>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
};
export default HomePage;