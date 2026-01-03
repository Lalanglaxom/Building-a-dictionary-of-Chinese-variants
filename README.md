📁 Folder Structure

crawl folder (Chứa các script thu thập dữ liệu)

    crawl_standard.py: Khởi tạo database, lấy danh sách mục lục ~30.000 chữ chính (bảng Summary).

    crawl_variants.py: Lấy danh sách liên kết và ảnh glyph của ~70.000 dị tự (bảng Variants).

    standard_details.py: Truy cập từng trang chữ chính để lấy Thuyết văn, âm đọc, định nghĩa (bảng Descriptions).

    variants_details.py: Truy cập từng trang dị tự để lấy thông tin người nghiên cứu, ghi chú nguồn gốc (bảng Variant_details).

    crawl_search_result.py: Xử lý logic tìm kiếm và thu thập danh sách phụ lục (Họ, tên, địa danh).

    crawl_appendix_details.py: Lấy nội dung chi tiết cho các mục trong phụ lục.

    download_required_fonts.py: Script tự động quét và tải các file font còn thiếu từ server về máy.

images folder (Chứa tài nguyên ảnh offline)

    variant_images: Chứa ảnh glyph (mặt chữ) của các dị tự không có trong Unicode.

    summary_images: Chứa ảnh minh họa chèn trong bài giải thích chữ chính (VD: ảnh triện thư).

    variant_desc_images: Chứa ảnh minh họa chèn trong bài nghiên cứu dị tự.

database folder

    alter_drop_clear_database.py: Chứa các lệnh SQL để xóa bảng, reset dữ liệu hoặc sửa cấu trúc DB khi cần.

fonts folder

    Chứa các file .woff, .ttf (như MOE-Sung-Regular.woff, TW-Kai-98_1.ttf...) để render các ký tự hiếm (Extension A, B, C, D, E).

html folder

    Lưu các trang HTML tải về tạm thời để kiểm tra cấu trúc thẻ (debug).

📦 Files

    dictionary.db: Cơ sở dữ liệu SQLite chứa toàn bộ text, đường dẫn ảnh và quan hệ giữa các chữ.

    main_search.py: Ứng dụng chính (GUI) chạy bằng PyQt5, tích hợp trình duyệt nhúng và bộ quản lý Font.
