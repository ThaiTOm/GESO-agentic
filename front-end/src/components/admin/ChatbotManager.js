// src/components/admin/ChatbotManager.js
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAllChatbots, createChatbot, deleteChatbot } from '../../services/adminService';
import styles from './ChatbotManager.module.css';
import { FiPlus, FiTrash2, FiRefreshCw, FiSettings } from 'react-icons/fi';

const ChatbotManager = () => {
    const [chatbots, setChatbots] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [newBotName, setNewBotName] = useState('');

    const fetchChatbots = async () => {
        try {
            setLoading(true);
            setError('');
            const bots = await getAllChatbots();
            setChatbots(bots || []); // Đảm bảo bots luôn là một mảng
        } catch (err) {
            setError('Không thể tải danh sách chatbot. Vui lòng đảm bảo server backend đang chạy và đã cấu hình CORS.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchChatbots();
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!newBotName.trim()) return;
        try {
            await createChatbot(newBotName);
            setNewBotName('');
            fetchChatbots();
        } catch (err) {
            alert(`Tạo chatbot thất bại: ${err.response?.data?.detail || err.message}`);
        }
    };

    const handleDelete = async (botName) => {
        if (window.confirm(`Bạn có chắc muốn xóa chatbot "${botName}" không? Hành động này không thể hoàn tác.`)) {
            try {
                await deleteChatbot(botName);
                fetchChatbots();
            } catch (err) {
                alert(`Xóa chatbot thất bại: ${err.response?.data?.detail || err.message}`);
            }
        }
    };

    return (
        <div className={styles.managerCard}>
            <div className={styles.header}>
                <h2>Quản lý Chatbot</h2>
                <button onClick={fetchChatbots} className={styles.refreshButton} disabled={loading} title="Tải lại danh sách">
                    <FiRefreshCw className={loading ? styles.spinning : ''} />
                </button>
            </div>

            <form onSubmit={handleCreate} className={styles.createForm}>
                <input
                    type="text"
                    value={newBotName}
                    onChange={(e) => setNewBotName(e.target.value)}
                    placeholder="Nhập tên chatbot mới (vd: sales_bot)..."
                    className={styles.input}
                />
                <button type="submit" className={styles.addButton}>
                    <FiPlus /> Thêm mới
                </button>
            </form>

            {error && <p className={styles.error}>{error}</p>}

            <div className={styles.tableContainer}>
                <table className={styles.chatbotTable}>
                    <thead>
                    <tr>
                        <th>Tên Chatbot</th>
                        <th>ID</th>
                        <th style={{ textAlign: 'center' }}>Hành động</th>
                    </tr>
                    </thead>
                    <tbody>
                    {loading ? (
                        <tr><td colSpan="3" style={{ textAlign: 'center' }}>Đang tải...</td></tr>
                    ) : chatbots.length > 0 ? (
                        chatbots.map(bot => (
                            <tr key={bot.chatbot_id}>
                                <td className={styles.botName}>{bot.name}</td>
                                <td>{bot.chatbot_id}</td>
                                <td className={styles.actionsCell}>
                                    <Link to={`/admin/${bot.name}`} className={styles.manageButton}>
                                        <FiSettings /> Quản lý
                                    </Link>
                                    <button onClick={() => handleDelete(bot.name)} className={styles.deleteButton} title="Xóa Chatbot">
                                        <FiTrash2 />
                                    </button>
                                </td>
                            </tr>
                        ))
                    ) : (
                        <tr><td colSpan="3" style={{ textAlign: 'center', padding: '1rem' }}>Chưa có chatbot nào.</td></tr>
                    )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ChatbotManager;