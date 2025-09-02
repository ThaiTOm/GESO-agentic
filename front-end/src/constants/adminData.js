import { FiUsers, FiMessageCircle, FiActivity, FiBarChart } from 'react-icons/fi';

export const statsData = [
    { icon: <FiMessageCircle size={24}/>, title: "Tổng hội thoại", value: "1,250", change: "+5.4%" },
    { icon: <FiUsers size={24}/>, title: "Người dùng hoạt động", value: "340", change: "-1.2%" },
    { icon: <FiActivity size={24}/>, title: "Tỷ lệ phản hồi", value: "92.8%", change: "+2.1%" },
    { icon: <FiBarChart size={24}/>, title: "Đánh giá hài lòng", value: "4.7/5", change: "+0.5" },
];

export const recentConversations = [
    { id: 'C001', user: 'Nguyễn Văn A', lastMsg: 'Sản phẩm này có những màu nào?', status: 'Đang chờ' },
    { id: 'C002', user: 'Trần Thị B', lastMsg: 'Cảm ơn bạn đã hỗ trợ.', status: 'Đã đóng' },
    { id: 'C003', user: 'Lê Văn C', lastMsg: 'Tôi cần hỗ trợ kỹ thuật', status: 'Đã xử lý' },
];
