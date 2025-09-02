import { statsData } from '../constants/adminData'; // Bỏ recentConversations vì ta sẽ lấy từ API
import StatCard from '../components/ui/StatCard';
import ChatbotManager from '../components/admin/ChatbotManager'; // Import component mới
import styles from './AdminPage.module.css';

const AdminPage = () => {
    return (
        <div className={styles.adminPage}>
            <h1>Tổng quan</h1>

            <div className={styles.statsGrid}>
                {statsData.map((stat, index) => <StatCard key={index} {...stat} />)}
            </div>

            {/* Thêm component quản lý chatbot vào đây */}
            <ChatbotManager />

        </div>
    );
};
export default AdminPage;