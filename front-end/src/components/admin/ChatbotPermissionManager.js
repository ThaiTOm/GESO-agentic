import React from 'react';
import { useState } from 'react';
import * as XLSX from 'xlsx';
import styles from './ChatbotPermissionManager.module.css';
import { FiUpload, FiSave, FiUserPlus, FiEdit2, FiTrash2, FiX, FiCheck, FiFilter, FiPlusCircle, FiHelpCircle, FiXCircle } from 'react-icons/fi';
import axios from "axios";

// --- CÁC ĐỊNH NGHĨA CỐ ĐỊNH ---
let URL_FOR_UPLOAD;
URL_FOR_UPLOAD = "http://ai.tvssolutions.vn:2111/api/v1/typesense/document/upload/"
// Định nghĩa các cấp độ quyền CỘT
const PERMISSION_LEVELS = {
    ALLOW: 'Được đọc',
    DENY: 'Cấm',
};
const PERMISSION_KEYS = Object.keys(PERMISSION_LEVELS);

// Định nghĩa các KIỂU LỌC DÒNG
const FILTER_TYPES = {
    MATCH_CURRENT_USER_ID: { text: 'Lọc theo ID người dùng hiện tại', description: 'Hệ thống sẽ tự động lọc để người dùng chỉ thấy các dòng có giá trị trong cột này khớp với ID của chính họ.', requiresValue: false },
    MATCH_CURRENT_USER_PROPERTY: { text: 'Lọc theo thuộc tính người dùng (vd: phòng ban)', description: 'Lọc các dòng có giá trị trong cột này khớp với một thuộc tính của người dùng (vd: department, location).', requiresValue: true, valuePlaceholder: 'Nhập tên thuộc tính (vd: department)...' },
    IN_STATIC_LIST: { text: 'Lọc theo danh sách giá trị cố định', description: 'Người dùng chỉ thấy các dòng có giá trị trong cột này nằm trong danh sách bạn cung cấp (ngăn cách bởi dấu phẩy).', requiresValue: true, valuePlaceholder: 'Nhập các giá trị, vd: Hà Nội, Hồ Chí Minh...' },
};

// --- COMPONENT CHÍNH ---
const ChatbotPermissionManager = ({ chatbotName }) => {
    // === STATE MANAGEMENT ===
    const [fileName, setFileName] = useState('');
    const [selectedFile, setSelectedFile] = useState(null); // State to hold the file object
    const [allColumns, setAllColumns] = useState([]);
    const [users, setUsers] = useState(['sales_team', 'marketing_team', 'manager']);
    const [newUserName, setNewUserName] = useState('');
    const [editingUser, setEditingUser] = useState({ originalName: null, newName: '' });
    const [columnPermissions, setColumnPermissions] = useState({});
    const [rowRules, setRowRules] = useState({});
    const [showHelp, setShowHelp] = useState(false);

    // === HANDLER FUNCTIONS ===

    /**
     * --- MODIFIED: Handles both Excel and PDF files ---
     * Xử lý khi người dùng chọn file.
     */
    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Set state common to all file types
        setFileName(file.name);
        setSelectedFile(file);

        const fileExtension = file.name.split('.').pop().toLowerCase();

        // If it's an Excel file, read columns and set up permissions UI
        if (['xlsx', 'xls'].includes(fileExtension)) {
            const reader = new FileReader();
            reader.onload = (event) => {
                try {
                    // This first step is still fast as it only reads the file structure
                    const workbook = XLSX.read(event.target.result, { type: 'binary' });
                    const worksheet = workbook.Sheets['data'];

                    if (!worksheet) {
                        alert('Lỗi: Không tìm thấy sheet có tên là "data" trong file Excel.');
                        setAllColumns([]); // Clear columns on error
                        return;
                    }

                    // ==================== OPTIMIZATION START ====================
                    // This is the optimized part. Instead of reading the whole file into JSON,
                    // we only read the very first row to get the column headers.
                    // - header: 1 -> returns an array of arrays
                    // - range: 0  -> tells sheetjs to ONLY process the first row (index 0)
                    const headerRow = XLSX.utils.sheet_to_json(worksheet, {
                        header: 1,
                        range: 0,
                        defval: ""
                    });

                    // Check if the header row was found and is not empty
                    if (!headerRow || headerRow.length === 0 || headerRow[0].length === 0) {
                        alert("Sheet 'data' không có dữ liệu hoặc hàng tiêu đề trống.");
                        setAllColumns([]); // Clear columns if empty
                        return;
                    }

                    // The columns are the first (and only) item in our result.
                    // We also filter out any completely empty header cells just in case.
                    const columns = headerRow[0].filter(c => c.toString().trim() !== '');

                    if (columns.length === 0) {
                        alert("Không tìm thấy tên cột nào trong hàng đầu tiên của sheet 'data'.");
                        setAllColumns([]);
                        return;
                    }
                    // ===================== OPTIMIZATION END =====================

                    setAllColumns(columns);

                    // Initialize permissions based on detected columns
                    const initialPermissions = {};
                    const initialRowRules = {};
                    users.forEach(user => {
                        initialPermissions[user] = {};
                        initialRowRules[user] = [];
                        columns.forEach(col => {
                            initialPermissions[user][col] = 'ALLOW';
                        });
                    });
                    setColumnPermissions(initialPermissions);
                    setRowRules(initialRowRules);

                } catch (error) {
                    console.error("Lỗi khi xử lý file Excel:", error);
                    alert("Đã xảy ra lỗi khi xử lý file Excel. Vui lòng kiểm tra file và thử lại.");
                    setAllColumns([]); // Clear columns on error
                }
            };
            reader.readAsBinaryString(file);
        }
        // If it's a PDF or other file type, just prepare for upload without permissions UI
        else {
            console.log("PDF file selected. Permission UI will be hidden.");
            // Clear any previous column-based permission settings
            setAllColumns([]);
            setColumnPermissions({});
            setRowRules({});
        }
    };


    // --- Logic Quản lý User (Không thay đổi) ---
    const handleAddUser = (e) => {
        e.preventDefault();
        const trimmedName = newUserName.trim();
        if (trimmedName && !users.includes(trimmedName)) {
            setUsers(prev => [...prev, trimmedName]);
            // Only add column permissions if columns exist
            if (allColumns.length > 0) {
                 const newUserPermissions = {};
                 allColumns.forEach(col => { newUserPermissions[col] = 'ALLOW'; });
                 setColumnPermissions(prev => ({ ...prev, [trimmedName]: newUserPermissions }));
            }
            setRowRules(prev => ({ ...prev, [trimmedName]: [] }));
            setNewUserName('');
        } else {
            alert("Tên người dùng không hợp lệ hoặc đã tồn tại.");
        }
    };
    const handleDeleteUser = (userToDelete) => {
        if (window.confirm(`Bạn có chắc muốn xóa "${userToDelete}"?`)) {
            setUsers(prev => prev.filter(user => user !== userToDelete));
            const newPermissions = { ...columnPermissions };
            delete newPermissions[userToDelete];
            setColumnPermissions(newPermissions);
            const newRowRules = { ...rowRules };
            delete newRowRules[userToDelete];
            setRowRules(newRowRules);
        }
    };
    const handleSaveEditUser = (originalName) => {
        const newName = editingUser.newName.trim();
        if (newName && !users.includes(newName)) {
            setUsers(users.map(u => (u === originalName ? newName : u)));
            const newPermissions = { ...columnPermissions };
            newPermissions[newName] = newPermissions[originalName];
            delete newPermissions[originalName];
            setColumnPermissions(newPermissions);
            const newRowRules = { ...rowRules };
            newRowRules[newName] = newRowRules[originalName];
            delete newRowRules[originalName];
            setRowRules(newRowRules);
            setEditingUser({ originalName: null, newName: '' });
        } else {
            alert("Tên người dùng mới không hợp lệ hoặc đã tồn tại.");
        }
    };

    // --- Logic Quản lý Quyền (Không thay đổi) ---
    const handleColumnPermissionChange = (user, column, level) => {
        setColumnPermissions(prev => ({ ...prev, [user]: { ...prev[user], [column]: level } }));
    };
    const handleAddRowRule = (user) => {
        if (!allColumns.length) return;
        const newRule = { id: Date.now(), column: allColumns[0], filterType: 'IN_STATIC_LIST', value: '' };
        setRowRules(prev => ({ ...prev, [user]: [...(prev[user] || []), newRule] }));
    };
    const handleDeleteRowRule = (user, ruleId) => {
        setRowRules(prev => ({ ...prev, [user]: prev[user].filter(rule => rule.id !== ruleId) }));
    };
    const handleRowRuleChange = (user, ruleId, field, value) => {
        setRowRules(prev => ({
            ...prev,
            [user]: prev[user].map(rule => {
                if (rule.id === ruleId) {
                    const updatedRule = { ...rule, [field]: value };
                    if (field === 'filterType' && !FILTER_TYPES[value].requiresValue) {
                        updatedRule.value = '';
                    }
                    return updatedRule;
                }
                return rule;
            })
        }));
    };

    // --- Logic Gửi Dữ liệu Lên Server (Không thay đổi) ---
    const handleUploadAndSave = async () => {
        if (!selectedFile) {
            alert("Vui lòng chọn một file để tải lên trước.");
            return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);

        // Only append permissions if there are columns defined (i.e., it was an Excel file)
        // This aligns with the optional permissions on the backend
        if (allColumns.length > 0) {
            const permissionConfig = {
                botName: chatbotName,
                dataSourceIdentifier: fileName,
                users: users,
                columnPermissions: columnPermissions,
                rowRules: rowRules,
            };
            formData.append('permissions', JSON.stringify(permissionConfig));
            console.log("Đang gửi file CÙNG VỚI cấu hình phân quyền:", permissionConfig);
        } else {
            console.log("Đang gửi CHỈ CÓ file (không có cấu hình phân quyền).");
        }

        try {
            alert("Đang tải lên file và xử lý...");
            const response = await axios.post(URL_FOR_UPLOAD + chatbotName, formData, {
                headers: { 'accept': 'application/json' }
            });

            console.log("Server response:", response.data);
            alert(`Thành công! File "${response.data.file_name}" đã được xử lý. ${response.data.message}`);

        } catch (error) {
            console.error("Error uploading file and configuration:", error);
            let errorMessage = "Đã có lỗi xảy ra khi tải file lên.";
            if (error.response) {
                errorMessage = `Lỗi từ máy chủ: ${error.response.status} - ${error.response.data.detail || error.message}`;
            } else if (error.request) {
                errorMessage = "Không thể kết nối tới máy chủ. Vui lòng kiểm tra lại kết nối mạng và địa chỉ API.";
            }
            alert(errorMessage);
        }
    };


    // === JSX RENDER (Không thay đổi) ===
    return (
        <div className={styles.container}>
            {/* --- Phần 1: Tải File --- */}
            <div className={styles.section}>
                <h3>1. Tải lên Nguồn dữ liệu</h3>
                <div className={styles.uploadSection}>
                    <label htmlFor="excel-upload" className={styles.uploadButton}><FiUpload /> Chọn File (Excel hoặc PDF)</label>
                    <input id="excel-upload" type="file" accept=".xlsx, .xls, .pdf" onChange={handleFileChange} style={{ display: 'none' }} />
                    {fileName && <p>File đã chọn: <strong>{fileName}</strong></p>}
                </div>
                {selectedFile && !['xlsx', 'xls'].includes(fileName.split('.').pop().toLowerCase()) &&
                    <p className={styles.sectionDescription}>
                        Bạn đã chọn một file PDF. Cấu hình phân quyền chi tiết cần được thực hiện sau khi file được xử lý ở backend.
                    </p>
                }
            </div>

            {/* --- Phần 2, 3, 4 only show if columns were detected (from an Excel file) --- */}
            {allColumns.length > 0 && (
                <>
                    {/* --- Phần 2: Quản lý User --- */}
                    <div className={styles.section}>
                        <h3>2. Quản lý Người dùng / Vai trò</h3>
                        <form onSubmit={handleAddUser} className={styles.addUserForm}>
                            <input type="text" value={newUserName} onChange={(e) => setNewUserName(e.target.value)} placeholder="Nhập tên user/vai trò mới..." className={styles.input} />
                            <button type="submit" className={styles.actionButton}><FiUserPlus /> Thêm</button>
                        </form>
                        <ul className={styles.userList}>
                            {users.map(user => (
                                <li key={user} className={styles.userItem}>
                                    {editingUser.originalName === user ? (
                                        <>
                                            <input type="text" value={editingUser.newName} onChange={(e) => setEditingUser({ ...editingUser, newName: e.target.value })} className={styles.input} autoFocus />
                                            <button onClick={() => handleSaveEditUser(user)} className={styles.iconButton} title="Lưu"><FiCheck color="green" /></button>
                                            <button onClick={() => setEditingUser({ originalName: null, newName: '' })} className={styles.iconButton} title="Hủy"><FiX color="gray" /></button>
                                        </>
                                    ) : (
                                        <>
                                            <span>{user}</span>
                                            <div className={styles.userActions}>
                                                <button onClick={() => setEditingUser({ originalName: user, newName: user })} className={styles.iconButton} title="Sửa"><FiEdit2 /></button>
                                                <button onClick={() => handleDeleteUser(user)} className={styles.iconButton} title="Xóa"><FiTrash2 color="red" /></button>
                                            </div>
                                        </>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* --- Phần 3: Phân quyền Cột --- */}
                    <div className={styles.section}>
                        <h3>3. Phân quyền Truy cập Cột</h3>
                        <div className={styles.tableContainer}>
                            <table className={styles.permissionTable}>
                                <thead><tr><th>Cột Dữ liệu</th>{users.map(user => <th key={user}>{user}</th>)}</tr></thead>
                                <tbody>
                                    {allColumns.map(col => (
                                        <tr key={col}><td>{col}</td>
                                            {users.map(user => (
                                                <td key={user}><select value={columnPermissions[user]?.[col] || 'ALLOW'} onChange={(e) => handleColumnPermissionChange(user, col, e.target.value)} className={`${styles.permissionSelect} ${styles[columnPermissions[user]?.[col]]}`}>{PERMISSION_KEYS.map(key => <option key={key} value={key}>{PERMISSION_LEVELS[key]}</option>)}</select></td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* --- Phần 4: Phân quyền Dòng --- */}
                    <div className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <h3><FiFilter /> 4. Phân quyền Truy cập Dòng (Lọc dữ liệu)</h3>
                            <button onClick={() => setShowHelp(true)} className={styles.helpButton} title="Giải thích các kiểu lọc"><FiHelpCircle /> Trợ giúp</button>
                        </div>
                        {showHelp && (
                            <div className={styles.helpOverlay} onClick={() => setShowHelp(false)}>
                                <div className={styles.helpModal} onClick={e => e.stopPropagation()}>
                                    <div className={styles.helpModalHeader}><h4>Giải thích các Kiểu Lọc</h4><button onClick={() => setShowHelp(false)} className={styles.iconButton}><FiXCircle /></button></div>
                                    <table className={styles.helpTable}>
                                        <thead><tr><th>Kiểu Lọc</th><th>Ý nghĩa</th></tr></thead>
                                        <tbody>{Object.keys(FILTER_TYPES).map(key => (<tr key={key}><td>{FILTER_TYPES[key].text}</td><td>{FILTER_TYPES[key].description}</td></tr>))}</tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                        <div className={styles.rowFilterContainer}>
                            {users.map(user => (
                                <div key={user} className={styles.userFilterCard}><h4>Quy tắc cho: <strong>{user}</strong></h4><div className={styles.rulesList}>
                                    {(rowRules[user] || []).map(rule => (
                                        <div key={rule.id} className={styles.ruleRow}>
                                            <select value={rule.column} onChange={(e) => handleRowRuleChange(user, rule.id, 'column', e.target.value)} className={styles.ruleComponent}>{allColumns.map(col => <option key={col} value={col}>{col}</option>)}</select>
                                            <select value={rule.filterType} onChange={(e) => handleRowRuleChange(user, rule.id, 'filterType', e.target.value)} className={styles.ruleComponent}>{Object.keys(FILTER_TYPES).map(key => <option key={key} value={key}>{FILTER_TYPES[key].text}</option>)}</select>
                                            {FILTER_TYPES[rule.filterType]?.requiresValue && (<input type="text" value={rule.value} onChange={(e) => handleRowRuleChange(user, rule.id, 'value', e.target.value)} placeholder={FILTER_TYPES[rule.filterType].valuePlaceholder} className={`${styles.ruleComponent} ${styles.ruleInput}`} />)}
                                            <button onClick={() => handleDeleteRowRule(user, rule.id)} className={styles.iconButton} title="Xóa quy tắc"><FiTrash2 color="red" /></button>
                                        </div>
                                    ))}
                                    {(!rowRules[user] || rowRules[user].length === 0) && <p className={styles.noRulesText}>Chưa có quy tắc nào.</p>}
                                </div><button onClick={() => handleAddRowRule(user)} className={styles.addRuleButton}><FiPlusCircle /> Thêm quy tắc lọc</button></div>
                            ))}
                        </div>
                    </div>
                </>
            )}

            {/* --- Phần 5: Lưu Cấu hình --- */}
            {/* MODIFIED: Show button as long as a file is selected */}
            {selectedFile &&
                <div className={styles.saveSection}>
                    <button onClick={handleUploadAndSave} className={styles.saveButton}>
                        <FiSave /> {allColumns.length > 0 ? 'Tải lên File và Lưu Cấu hình' : 'Tải lên File'}
                    </button>
                </div>
            }
        </div>
    );
};

export default ChatbotPermissionManager;