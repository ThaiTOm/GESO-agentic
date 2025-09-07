// src/pages/ChatbotDetailPage.js
import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getDocumentsByChatbot, uploadDocument, deleteDocument } from '../services/adminService';
import styles from './ChatbotDetailPage.module.css';
import { FiFile, FiTrash2, FiUploadCloud, FiArrowLeft, FiSettings } from 'react-icons/fi';

const ChatbotDetailPage = () => {
    const { chatbotName } = useParams();
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef(null);

    const fetchDocuments = async () => {
        try {
            setLoading(true);
            setError('');
            const docs = await getDocumentsByChatbot(chatbotName);
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
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, [chatbotName]);

    const handleFileChange = (event) => setSelectedFile(event.target.files[0]);

    const handleUpload = async () => {
        if (!selectedFile) return;
        setIsUploading(true);
        setError('');
        try {
            await uploadDocument(chatbotName, selectedFile);
            setSelectedFile(null);
            if (fileInputRef.current) fileInputRef.current.value = null;
            await fetchDocuments();
        } catch (err) {
            setError(`Upload thất bại: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async (docTitle) => {
        if (window.confirm(`Bạn có chắc muốn xóa tất cả dữ liệu của file "${docTitle}" không?`)) {
            try {
                await deleteDocument(chatbotName, docTitle);
                await fetchDocuments();
            } catch (err) {
                alert(`Xóa tài liệu thất bại: ${err.response?.data?.detail || err.message}`);
            }
        }
    };

    return (
        <div className={styles.detailPage}>
            <Link to="/admin" className={styles.backLink}><FiArrowLeft /> Quay lại danh sách</Link>
            <h1>Quản lý Agent: <span>{chatbotName}</span></h1>
            <div className={styles.grid}>
                <div className={styles.card}>
                    <h2><FiUploadCloud /> Kho tri thức</h2>
                    <div className={styles.uploadSection}>
                        <input type="file" ref={fileInputRef} onChange={handleFileChange} className={styles.fileInput} />
                        <button onClick={handleUpload} disabled={!selectedFile || isUploading} className={styles.uploadButton}>
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
                                <button onClick={() => handleDelete(doc.name)} className={styles.deleteButton} title="Xóa tài liệu">
                                    <FiTrash2 />
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>
                {/*<div className={styles.card}>*/}
                {/*    <h2><FiSettings /> Các chức năng (Tools)</h2>*/}
                {/*    <p className={styles.toolDescription}>Chọn các công cụ mà agent này có thể sử dụng.</p>*/}
                {/*    <div className={styles.toolOptions}>*/}
                {/*        <label><input type="checkbox" name="tool"/> Phân tích dữ liệu (Excel)</label>*/}
                {/*        <label><input type="checkbox" name="tool"/> Tìm kiếm Google</label>*/}
                {/*        <label><input type="checkbox" name="tool"/> Chat bằng giọng nói</label>*/}
                {/*    </div>*/}
                {/*</div>*/}
            </div>
        </div>
    );
};

export default ChatbotDetailPage;