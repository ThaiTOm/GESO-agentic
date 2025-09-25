FACT_DOANH_THU_DESCRIPTION = """
Bảng dữ liệu này đồng thời phản ánh chỉ số hoạt động của đội ngũ bán hàng, bao gồm: nhân viên bán hàng, giám sát bán hàng, RSM phụ trách khu vực, số lượng khách hàng quản lý, sản phẩm phân phối (SKU), doanh số đạt được.
Các cột chi tiết trong bảng dữ liệu bao gồm:
    KH_FK: Mã khách hàng.
    SP_FK: Mã sản phẩm.
    KHO_FK: Mã kho.
    DDKD_FK: Mã đại diện kinh doanh.
    GSBH_FK: Mã giám sát bán hàng.
    RSM_FK: Mã RSM/ BM .
    DMS_ID: MÃ DMS.
    SAP_ID: Mã số SAP.
    MARSM: Mã RSM (Regional Sales Manager). Mã định danh Giám đốc Miền, giám đốc vùng.
    NGAYDONHANG: Ngày chính xác mà đơn hàng được ghi nhận trong hệ thống. Cho phép xác định hiệu suất bán hàng hàng ngày và đánh giá độ chính xác của kế hoạch bán hàng.
    THANG: Tháng giao dịch.
    NAM: Năm giao dịch.
    MAHOPDONG: Mã hợp đồng.
    SOHOPDONG: Số hợp đồng.
    RSM: Tên của Giám đốc Miền , giám đốc vùng.
    KENH: Phân loại kênh phân phối nơi phát sinh đơn hàng, ví dụ: OTC (nhà thuốc), ETC (bệnh viện), MT (siêu thị, chuỗi), GT (tạp hóa)
    VUNG: Vùng phụ trách kinh doanh, ví dụ: Miền Bắc, Trung, Nam.
    KHUVUC: Khu vực quản lý, ASM quản lý khu vực.
    NHAPHANPHOI: là nhà phân phối, Đơn vị trung gian chịu trách nhiệm phân phối sản phẩm đến điểm bán. 
    TINHTHANH: thông tin tỉnh thành, địa chỉ hành chính nơi khách hàng (nhà thuốc, cửa hàng) hoạt động.
    QUANHUYEN: Quận/Huyện của khách hàng/nhà thuốc, hỗ trợ giám sát vùng hoạt động của nhân viên
    MAGSBH: KHÔNG XÀI.
    GIAMSATBANHANG: Tên Giám sát bán hàng, giám sát bán hàng quản lý nhân viên bán hàng.
    MANVBH: KHÔNG XÀI.
    NHANVIENBANHANG: Tên nhân viên phụ trách bán hàng,  trình dược viên, đại diện kinh doanh.
    MAKHACHHANG: KHÔNG XÀI.
    NGUOIMUAHANG: Người trực tiếp mua hàng.
    NGANHHANG: Phân loại sản phẩm theo nhóm ngành, ví dụ: thuốc ho, kháng sinh, thực phẩm chức năng.
    NHANHANG: thông tin nhãn hàng, Thương hiệu sản phẩm (ví dụ: Panadol, Hapacol), hỗ trợ phân tích hiệu suất thương hiệu.
    GAMHANG: Mã gam hàng
    MASANPHAM: KHÔNG XÀI.
    TENSANPHAM: Tên sản phẩm, hỗ trợ báo cáo bán hàng, đối chiếu với người dùng cuối.
    DOANHSO: Tổng doanh thu chưa tính thuế VAT. Đây là giá trị gốc để phân tích hiệu quả kinh doanh thực tế.
    DOANHTHUTRUOCVAT: Tổng doanh thu chưa tính thuế VAT. Đây là giá trị gốc để phân tích hiệu quả kinh doanh thực tế.
    TIENVAT: Tiền thuế VAT của từng giao dịch.
    DOANHTHUSAUTHUE: Tổng doanh thu bao gồm VAT (giá trị khách hàng phải thanh toán). Nói lên dòng tiền thực tế mà công ty thu về.
    SOLUONG: Số lượng trên sản phẩm trong 1 đơn hàng
    MAKHO: KHÔNG XÀI.
    TENKHO: Tên của kho.
    DONVI: Đơn vị.
    ID: Không xài.
    is_sync_redis: Không xài.
    is_sync_pt:  Không xài.
"""