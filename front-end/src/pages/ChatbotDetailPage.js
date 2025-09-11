import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';

// Services để tương tác với API backend cho "Kho tri thức"
import { getDocumentsByChatbot, uploadDocument, deleteDocument } from '../services/adminService';

// Import CSS cho trang này
import styles from './ChatbotDetailPage.module.css';

// Import các icon cần thiết
import { FiFile, FiTrash2, FiUploadCloud, FiArrowLeft, FiDatabase } from 'react-icons/fi';

// Import component con để quản lý quyền Excel
import ChatbotPermissionManager from '../components/admin/ChatbotPermissionManager';

const ChatbotDetailPage = () => {
    // Lấy tên chatbot từ URL, ví dụ: "/admin/sales_bot" -> "sales_bot"
    const { chatbotName } = useParams();

    // ===================================================================
    // VÙNG STATE VÀ LOGIC CHO "KHO TRI THỨC" (FUNCTIONALITY A)
    // Toàn bộ phần này được giữ nguyên từ file gốc của bạn.
    // ===================================================================
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef(null);

    // Hàm gọi API để lấy danh sách tài liệu của "Kho tri thức"
    const fetchDocuments = async () => {
        try {
            setLoading(true);
            setError('');
            const docs = await getDocumentsByChatbot(chatbotName);
            // Nhóm các chunks lại theo tên file để hiển thị
            const groupedDocs = (docs || []).reduce((acc, doc) => {
                if (!acc[doc.file_name]) {
                    acc[doc.file_name] = { name: doc.file_name, chunks: 0 };
                }
                acc[doc.file_name].chunks += 1;
                return acc;
            }, {});
            setDocuments(Object.values(groupedDocs));
        } catch (err) {
            setError('Không thể tải danh sách tài liệu.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // Chạy hàm fetchDocuments khi component được mount hoặc chatbotName thay đổi
    useEffect(() => {
        // Đặt tên hàm rõ ràng để tránh nhầm lẫn với logic của component khác
        fetchKnowledgeBaseDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [chatbotName]);

    // Đổi tên hàm để rõ ràng hơn
    const fetchKnowledgeBaseDocuments = fetchDocuments;

    const handleKnowledgeFileChange = (event) => setSelectedFile(event.target.files[0]);

    const handleKnowledgeUpload = async () => {
        if (!selectedFile) return;
        setIsUploading(true);
        setError('');
        try {
            await uploadDocument(chatbotName, selectedFile);
            setSelectedFile(null);
            if (fileInputRef.current) fileInputRef.current.value = null; // Reset input file
            await fetchKnowledgeBaseDocuments(); // Tải lại danh sách
        } catch (err) {
            setError(`Upload thất bại: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleKnowledgeDelete = async (docTitle) => {
        if (window.confirm(`Bạn có chắc muốn xóa tất cả dữ liệu của file "${docTitle}" không?`)) {
            try {
                await deleteDocument(chatbotName, docTitle);
                await fetchKnowledgeBaseDocuments(); // Tải lại danh sách
            } catch (err) {
                alert(`Xóa tài liệu thất bại: ${err.response?.data?.detail || err.message}`);
            }
        }
    };

    // ===================================================================
    // PHẦN RENDER GIAO DIỆN (JSX)
    // ===================================================================
    return (
        <div className={styles.detailPage}>
            {/* Header của trang với link quay lại và tiêu đề */}
            <Link to="/admin" className={styles.backLink}>
                <FiArrowLeft /> Quay lại danh sách
            </Link>
            <h1>Quản lý Agent: <span>{chatbotName}</span></h1>

            <div className={styles.grid}>
                <div className={styles.card}>
                    <h2><FiUploadCloud /> Kho tri thức (PDF, TXT...)</h2>
                    <p className={styles.cardDescription}>Tải lên các tài liệu để Agent học và trả lời câu hỏi dựa trên nội dung.</p>

                    <div className={styles.uploadSection}>
                        <input type="file" ref={fileInputRef} onChange={handleKnowledgeFileChange} className={styles.fileInput} />
                        <button onClick={handleKnowledgeUpload} disabled={!selectedFile || isUploading} className={styles.uploadButton}>
                            {isUploading ? 'Đang upload...' : 'Upload File'}
                        </button>
                    </div>
                    {selectedFile && <p className={styles.selectedFile}>Đã chọn: {selectedFile.name}</p>}
                    {error && <p className={styles.error}>{error}</p>}

                    <h3 className={styles.docListHeader}>Tài liệu đã nạp</h3>
                    {loading && <p>Đang tải...</p>}
                    <ul className={styles.docList}>
                        {!loading && documents.length === 0 && <li>Chưa có tài liệu nào.</li>}
                        {documents.map((doc) => (
                            <li key={doc.name} className={styles.docItem}>
                                <FiFile />
                                <span className={styles.docName}>{doc.name} <span>({doc.chunks} chunks)</span></span>
                                <button onClick={() => handleKnowledgeDelete(doc.name)} className={styles.deleteButton} title="Xóa tài liệu">
                                    <FiTrash2 />
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* --- CARD 2: NGUỒN DỮ LIỆU & PHÂN QUYỀN (Chức năng mới) --- */}
                <div className={styles.card}>
                    <h2><FiDatabase /> Nguồn dữ liệu & Phân quyền (Excel)</h2>
                    <p className={styles.cardDescription}>Tải lên file Excel và cấu hình quyền truy cập dữ liệu theo từng cột cho người dùng.</p>

                    {/* 
                      Đây là nơi nhúng component quản lý quyền Excel.
                      Tất cả logic phức tạp về đọc file Excel, hiển thị bảng quyền, v.v.
                      được gói gọn bên trong component này, giúp trang chính luôn gọn gàng.
                      Chúng ta chỉ cần truyền `chatbotName` vào cho nó.
                    */}
                    <ChatbotPermissionManager chatbotName={chatbotName} />
                </div>

            </div>
        </div>
    );
};

export default ChatbotDetailPage;