📁 Folder Structure

crawl folder

    crawl_standard.py: lấy dữ liệu 30000 chữ thông dụng
    crawl_variants.py: lấy dữ liệu 70000 chữ biến thể
    standard_details_2.py, standard_details_resume.py: lấy thông tin phần mô tả ký tự thường
    variants_details.py: lấy thông tin phần mô tả dị tự
    test_crawl.py: lấy thử 1 page HTML

images folder

    variants_images: lưu hình ảnh những dị tự không có font
    summary_images: hình ảnh trong phần mô tả ký tự thường
    variant_desc_images, variant_glyphs: hình ảnh trong phần mô tả của dị tự

database folder

    alter_drop_clear_database.py: mấy lệnh để xóa, thay đổi database

font folder

    lưu các loại font cần dùng

html folder

    lưu mấy trang HTML để test

📦 Files

    dictionary.db: Database các chữ
    main.py: App chính để tra từ
    test_app, test_app2: App fix lỗi
