# CHƯƠNG 1. GIỚI THIỆU ĐỀ TÀI

## 1.1 Đặt vấn đề

Trong xu hướng chuyển đổi số hiện nay, phần lớn doanh nghiệp vận hành hệ thống thông tin trên cơ sở dữ liệu quan hệ (RDBMS) hoặc các kho dữ liệu doanh nghiệp (Enterprise Data Warehouse). Khi tổ chức chuyển dịch sang mô hình quản trị dựa trên dữ liệu, các phòng ban từ kinh doanh, tiếp thị, mua hàng đến quản lý kho đều cần trích xuất số liệu kịp thời để phục vụ quyết định điều hành.

Mặc dù vậy, khoảng cách giữa nhu cầu phân tích nghiệp vụ và năng lực truy xuất kỹ thuật trong doanh nghiệp vẫn còn lớn. Khảo sát thường niên của NewVantage Partners năm 2024 đối với các lãnh đạo công nghệ tại các tập đoàn lớn cho thấy hơn 70% tổ chức thừa nhận chưa đạt được trạng thái vận hành dựa trên dữ liệu, phần lớn do thiếu công cụ phân tích tự phục vụ (self-service analytics) hiệu quả [1]. Báo cáo từ Gartner cũng chỉ ra tình trạng nghẽn cổ chai trong khai thác dữ liệu xuất phát từ sự lệch pha kỹ năng giữa hai nhóm nhân sự [2]:

Chuyên viên phân tích nghiệp vụ (Business Analyst) nắm rõ bài toán thị trường, quy trình vận hành và các chỉ số hiệu suất chính, có nhu cầu trích xuất dữ liệu thường xuyên. Tuy nhiên, phần lớn nhân sự nghiệp vụ không thành thạo các câu lệnh SQL phức tạp, chẳng hạn như truy vấn qua nhiều bảng quan hệ, gom nhóm nhiều cấp hoặc sử dụng hàm cửa sổ. Khi phát sinh nhu cầu phân tích, họ phải tạo yêu cầu hỗ trợ sang đội ngũ kỹ thuật và thường mất từ hai đến năm ngày làm việc mới nhận được kết quả.

Ngược lại, chuyên viên phân tích dữ liệu (Data Analyst) sử dụng thành thạo SQL và cấu trúc dữ liệu, nhưng thường xuyên rơi vào tình trạng quá tải vì các yêu cầu trích xuất lặp đi lặp lại từ các phòng ban. Nhiều khảo sát cho thấy nhân sự kỹ thuật dữ liệu phải dành từ 40% đến 60% thời gian làm việc trong ngày để viết lại các truy vấn cơ bản hoặc giải thích cấu trúc bảng, làm giảm thời gian dành cho các bài toán phân tích chuyên sâu, tối ưu hóa quy trình hoặc xây dựng mô hình dự báo.

Sự chậm trễ này tạo ra nhu cầu cấp thiết về một công cụ hỗ trợ người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên và tự động sinh câu truy vấn SQL chính xác, kết nối trực tiếp logic nghiệp vụ với cơ sở dữ liệu mà không làm tăng tải cho đội ngũ kỹ thuật.

Chuyển đổi câu hỏi ngôn ngữ tự nhiên sang truy vấn cơ sở dữ liệu quan hệ (Text-to-SQL) là bài toán nghiên cứu quan trọng trong lĩnh vực xử lý ngôn ngữ tự nhiên [3]. Với sự phát triển của các mô hình ngôn ngữ lớn (LLM), khả năng hiểu ngữ nghĩa câu hỏi và sinh cú pháp SQL đã có những bước tiến rõ rệt trên các tập dữ liệu học thuật như Spider [4]. Dù vậy, khi triển khai vào môi trường kho dữ liệu doanh nghiệp thực tế, hệ thống phải đối mặt với nhiều rào cản kỹ thuật:

Thứ nhất, quy mô lược đồ cơ sở dữ liệu doanh nghiệp thường gồm nhiều bảng với hàng trăm cột liên kết theo các quan hệ đa tầng. Việc đưa toàn bộ định nghĩa cấu trúc bảng vào ngữ cảnh của mô hình dễ làm vượt quá giới hạn tính toán, tăng chi phí vận hành, kéo dài thời gian phản hồi và khiến mô hình dễ tạo ra các mối liên kết không có thực.

Thứ hai, trong các kho dữ liệu phân tích, các bảng sự kiện thường không lưu trực tiếp ngày tháng dưới dạng chuỗi hay timestamp mà dùng khóa thay thế dạng số nguyên liên kết sang bảng chiều thời gian. Mô hình ngôn ngữ cần nhận thức được cấu trúc này để tự động thực hiện phép nối bảng khi xử lý các điều kiện lọc theo năm, quý hoặc tháng.

Thứ ba, người dùng thường đưa ra các câu hỏi chứa giá trị thực tế của doanh nghiệp như tên ngành hàng, phương thức thanh toán hoặc hình thức vận chuyển. Đánh giá từ benchmark BIRD tại NeurIPS 2023 cho thấy hơn một nửa lỗi của các mô hình Text-to-SQL xuất phát từ việc chọn nhầm cột hoặc không khớp được giá trị phân loại thực tế lưu trong cơ sở dữ liệu [5]. Nếu thiếu bước tìm kiếm và liên kết giá trị phân loại, câu truy vấn sinh ra sẽ lọc sai hoặc trả về bảng rỗng.

Thứ tư, người dùng nghiệp vụ thường đặt câu hỏi ngắn gọn và ngầm định phạm vi. Những bài toán phân tích kinh doanh thường đòi hỏi chuỗi truy vấn thăm dò trên nhiều khía cạnh nghiệp vụ thay vì một câu lệnh đơn lẻ. Khi câu hỏi thiếu các điều kiện quan trọng về mốc thời gian hay phạm vi dữ liệu, hệ thống cần chủ động hỏi lại để làm rõ thay vì tự suy đoán.

Các hướng tiếp cận hiện tại bộc lộ nhiều hạn chế khi áp dụng vào môi trường doanh nghiệp:

Các công cụ kinh doanh thông minh truyền thống đòi hỏi kỹ sư dữ liệu phải thiết lập sẵn tầng ngữ nghĩa hoặc các khối dữ liệu đa chiều. Người dùng chỉ có thể thao tác trong phạm vi các chỉ số đã được định nghĩa từ trước, khó trả lời các câu hỏi phát sinh ngoài cấu trúc có sẵn.

Trong khi đó, việc sử dụng một mô hình ngôn ngữ lớn đơn lẻ để giải quyết toàn bộ quy trình từ lọc bảng, suy luận điều kiện nối, viết cú pháp đến sửa lỗi thường dẫn đến quá tải suy luận [6]. Khi gặp lỗi cú pháp hoặc kết quả rỗng, mô hình thường lặp lại lỗi cũ thay vì tìm ra nguyên nhân gốc rễ.

Đặc biệt, dự án OWASP Top 10 for LLM Applications cảnh báo nguy cơ nghiêm trọng khi để mô hình ngôn ngữ thực thi trực tiếp câu lệnh xuống cơ sở dữ liệu, bao gồm rủi ro tiêm mã độc SQL hoặc vô tình sinh các lệnh làm biến đổi và xóa dữ liệu [7]. Hầu hết các giải pháp thử nghiệm hiện nay chưa tích hợp hàng rào kiểm soát an toàn tất định, chưa hỗ trợ phân quyền theo vai trò để bảo vệ dữ liệu định danh cá nhân nhạy cảm, và thiếu cơ chế người dùng duyệt trước đối với các truy vấn quét lượng dữ liệu lớn. Ngoài ra, việc bóc tách câu truy vấn từ văn bản tự do bằng biểu thức chính quy thường thiếu ổn định, dễ gây lỗi hiển thị trên giao diện người dùng.

## 1.2 Mục tiêu và phạm vi đề tài

### 1.2.1 Mục tiêu đề tài

Đề tài hướng tới việc nghiên cứu và xây dựng hệ thống tác nhân AI hỗ trợ phân tích dữ liệu tự phục vụ, cho phép người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên tiếng Việt, tự động chuyển đổi thành câu truy vấn cơ sở dữ liệu chính xác, bảo đảm an toàn và trực quan hóa kết quả phân tích. Để đạt được mục tiêu tổng quát này, đồ án thực hiện bốn mục tiêu cụ thể sau:

1. Khảo sát cơ sở lý thuyết và các nghiên cứu hiện có về bài toán chuyển đổi ngôn ngữ tự nhiên sang truy vấn cơ sở dữ liệu, các mô hình tác nhân AI, cùng các thách thức về độ chính xác và an toàn dữ liệu khi ứng dụng mô hình ngôn ngữ lớn trong môi trường doanh nghiệp.
2. Khảo sát nhu cầu người dùng và xác định tập yêu cầu đối với hệ thống phân tích dữ liệu tự phục vụ, bao gồm yêu cầu chức năng, yêu cầu phi chức năng, yêu cầu bảo đảm an toàn dữ liệu và các tiêu chí đánh giá chất lượng câu truy vấn được tạo ra.
3. Nghiên cứu và lựa chọn giải pháp công nghệ phù hợp để thiết kế kiến trúc và triển khai hệ thống tác nhân AI, bao gồm các thành phần tiếp nhận câu hỏi tiếng Việt, làm rõ ý định khi thiếu thông tin, lập kế hoạch truy vấn, kiểm soát an toàn trước khi thực thi và tổng hợp kết quả trực quan cho người dùng.
4. Kiểm thử và đánh giá hệ thống thông qua các kịch bản truy vấn thực tế, từ đó phân tích độ chính xác của câu lệnh, khả năng tự sửa lỗi khi gặp sự cố, tính ổn định và mức độ đáp ứng nhu cầu phân tích của người dùng.

### 1.2.2 Phạm vi đề tài

Phạm vi nghiên cứu và triển khai của đề tài được xác định như sau:

* Về dữ liệu: Đồ án tập trung nghiên cứu trên các cơ sở dữ liệu quan hệ mô phỏng hoạt động quản lý kinh doanh và chuỗi phân phối trong doanh nghiệp, bao gồm các bảng dữ liệu về giao dịch bán hàng, thông tin khách hàng, danh mục sản phẩm và dữ liệu theo thời gian.
* Về hạ tầng lưu trữ: Sử dụng cơ sở dữ liệu nhúng DuckDB phục vụ phân tích dữ liệu cục bộ tốc độ cao trong quá trình phát triển và kiểm thử [8], kết hợp cấu hình kết nối Google BigQuery Sandbox mô phỏng kho dữ liệu đám mây doanh nghiệp.
* Về ngôn ngữ: Hệ thống tiếp nhận câu hỏi đầu vào bằng tiếng Việt tự nhiên; hỗ trợ diễn giải thông tin phân tích và hiển thị giao diện báo cáo bằng tiếng Việt.
* Về đối tượng sử dụng: Phân quyền phục vụ hai nhóm vai trò chính gồm chuyên viên phân tích nghiệp vụ với quyền hạn đọc dữ liệu tổng hợp không chứa thông tin định danh cá nhân nhạy cảm, và quản trị viên có đầy đủ quyền hạn tra cứu nhật ký kiểm toán và cấu hình hệ thống.
* Giới hạn phạm vi: Đề tài tập trung vào bài toán trích xuất và phân tích dữ liệu chỉ đọc. Hệ thống không hỗ trợ các thao tác ghi dữ liệu, thay đổi cấu trúc bảng hoặc vận hành giao dịch nghiệp vụ thời gian thực.

## 1.3 Định hướng giải pháp

Xuất phát từ các mục tiêu và yêu cầu đã xác định, đồ án lựa chọn định hướng tiếp cận bài toán theo mô hình tác nhân AI kết hợp quy trình kiểm soát an toàn tất định, mô phỏng cách làm việc của một chuyên viên dữ liệu thực tế.

Về phương pháp xử lý ngôn ngữ và lập luận, thay vì dồn toàn bộ bài toán vào một câu lệnh duy nhất, hệ thống phân chia quá trình xử lý thành chuỗi nhiệm vụ chuyên biệt. Khi nhận câu hỏi từ người dùng, hệ thống chủ động đánh giá độ rõ ràng của thông tin để hỏi lại nếu cần thiết, sau đó lập kế hoạch phân rã yêu cầu phân tích thành các bước truy vấn cụ thể, trích xuất cấu trúc bảng phù hợp và tra cứu giá trị phân loại trước khi tạo câu lệnh SQL.

Về kiểm soát an toàn và tính toàn vẹn dữ liệu, hệ thống áp dụng nguyên tắc kiểm soát lai: tận dụng thế mạnh hiểu ngôn ngữ tự nhiên của mô hình ngôn ngữ lớn, nhưng tách biệt toàn bộ khâu thẩm định an toàn sang mã nguồn tất định. Mọi câu lệnh trước khi thực thi đều phải đi qua các chốt kiểm tra cú pháp bằng cây cú pháp trừu tượng, thẩm tra quyền truy cập theo vai trò người dùng, ước tính tài nguyên quét dữ liệu và kích hoạt cơ chế người dùng duyệt trước đối với các truy vấn chi phí cao. Dữ liệu kết quả được trả về dưới dạng cấu trúc định kiểu chặt chẽ nhằm tránh lỗi hiển thị khi chuyển giao cho tầng trực quan hóa.

Kết quả đóng góp chính của đề tài là xây dựng hoàn chỉnh một ứng dụng phân tích dữ liệu tự phục vụ bằng tiếng Việt. Hệ thống giúp nhân sự nghiệp vụ chủ động tra cứu số liệu phân tích trong thời gian ngắn mà không phụ thuộc vào đội ngũ kỹ thuật, đồng thời giảm tải đáng kể các tác vụ truy vấn thủ công cho chuyên viên dữ liệu và bảo đảm an toàn thông tin theo tiêu chuẩn doanh nghiệp.

## 1.4 Bố cục đồ án

Phần còn lại của báo cáo đồ án tốt nghiệp này được tổ chức như sau.

Chương 2 trình bày về khảo sát và phân tích yêu cầu. Chương này tập trung khảo sát hiện trạng khai thác dữ liệu trong doanh nghiệp, phân tích những khó khăn của người dùng nghiệp vụ và xác định các tác nhân tham gia hệ thống. Trên cơ sở đó, chương xây dựng biểu đồ use case tổng quát, mô tả quy trình nghiệp vụ phân tích dữ liệu tự phục vụ, đặc tả chi tiết các ca sử dụng quan trọng và làm rõ các yêu cầu phi chức năng cần đáp ứng.

Chương 3 giới thiệu về nền tảng lý thuyết và công nghệ sử dụng. Chương này tổng hợp các kiến thức cơ sở về bài toán chuyển đổi ngôn ngữ tự nhiên sang SQL, mô hình ngôn ngữ lớn và kiến trúc tác nhân AI. Nội dung chương cũng trình bày kỹ thuật liên kết lược đồ cơ sở dữ liệu, tra cứu giá trị danh mục, phương pháp phân tích cú pháp truy vấn bằng cây cú pháp trừu tượng, đồng thời phân tích các tiêu chí lựa chọn công nghệ và hệ quản trị cơ sở dữ liệu phù hợp với đề tài.

Chương 4 mô tả quá trình phân tích thiết kế, triển khai và đánh giá hệ thống. Nội dung chương bao gồm việc lựa chọn kiến trúc phần mềm, thiết kế tổng quan và thiết kế chi tiết từng gói thành phần, thiết kế giao diện tương tác, thiết kế lớp và cấu trúc cơ sở dữ liệu. Chương này cũng trình bày danh mục thư viện, công cụ phát triển, kết quả đóng gói ứng dụng, minh họa các chức năng chính, cùng kế hoạch kiểm thử chức năng và phương án triển khai thử nghiệm hệ thống.

Chương 5 trình bày các giải pháp và đóng góp nổi bật của đồ án. Đây là nội dung trọng tâm thể hiện các kết quả nghiên cứu và giải pháp kỹ thuật do tác giả đề xuất, bao gồm: mô hình phối hợp giữa tác nhân lập kế hoạch phân rã truy vấn và đường ống kiểm soát an toàn tất định; giải pháp định tuyến lược đồ và tự động tìm đường nối giữa các bảng quan hệ phức tạp; cơ chế chẩn đoán lỗi có ngữ cảnh phục vụ việc tự động sửa lỗi truy vấn; và giải pháp giao tiếp dữ liệu có cấu trúc định kiểu mạnh nhằm ngăn chặn hoàn toàn lỗi hiển thị trên giao diện người dùng.

Chương 6 đưa ra kết luận và hướng phát triển của đề tài. Chương này tổng kết toàn bộ các kết quả nghiên cứu và sản phẩm ứng dụng đã hoàn thành, đối chiếu với các mục tiêu ban đầu, thẳng thắn đánh giá những mặt còn hạn chế trong quá trình thực hiện, từ đó đề xuất các hướng mở rộng và hoàn thiện hệ thống trong tương lai.

---

## Tài liệu tham khảo Chương 1

[1] NewVantage Partners. (2024). *Data and AI Leadership Executive Survey: Accelerating Business Value from Data and AI*. Boston, MA.  
[2] Gartner. (2023). *Market Guide for Augmented Analytics and Self-Service BI*. Gartner Research Report G00784912.  
[3] Katsogiannis-Meimarakis, N., & Koutrika, G. (2023). A Survey on Deep Learning Approaches for Text-to-SQL Systems. *The VLDB Journal*, 32(4), 905-936.  
[4] Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., Ma, J., Li, I., Yao, Q., Roman, S., Zhang, Z., & Radev, D. (2018). Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task. In *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, Brussels, Belgium, pp. 387-398.  
[5] Li, J., Hui, B., Qu, G., Yang, J., Li, B., Li, B., Wang, B., Qin, B., Geng, R., Huo, N., Zhou, C., Ma, J., & Li, Y. (2023). Can LLM Already Serve as A Database Interface? A Big Bench for Large-Scale Database Grounded Text-to-SQL (BIRD). In *Thirty-seventh Conference on Neural Information Processing Systems (NeurIPS 2023)*, New Orleans, LA.  
[6] Pourreza, M., & Rafiei, D. (2023). DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction. In *Thirty-seventh Conference on Neural Information Processing Systems (NeurIPS 2023)*, New Orleans, LA.  
[7] OWASP Foundation. (2023). *OWASP Top 10 for Large Language Model Applications (Version 1.1)*. Open Web Application Security Project.  
[8] Raasveldt, M., & Mühleisen, H. (2019). DuckDB: An Embeddable Analytical Database. In *Proceedings of the 2019 International Conference on Management of Data (SIGMOD '19)*, Amsterdam, Netherlands, pp. 1981-1984.

### Mã nguồn trích dẫn BibTeX (BibTeX References)

```bibtex
@techreport{newvantage2024data,
  author      = {{NewVantage Partners}},
  title       = {Data and {AI} Leadership Executive Survey: Accelerating Business Value from Data and {AI}},
  institution = {NewVantage Partners},
  year        = {2024},
  address     = {Boston, MA, USA},
  url         = {https://www.newvantage.com}
}

@techreport{gartner2023market,
  author      = {{Gartner}},
  title       = {Market Guide for Augmented Analytics and Self-Service {BI}},
  institution = {Gartner, Inc.},
  year        = {2023},
  number      = {G00784912},
  type        = {Research Report},
  address     = {Stamford, CT, USA}
}

@article{katsogiannis2023survey,
  author    = {Katsogiannis-Meimarakis, Nikolaos and Koutrika, Georgia},
  title     = {A survey on deep learning approaches for text-to-{SQL} systems},
  journal   = {The VLDB Journal},
  volume    = {32},
  number    = {4},
  pages     = {905--936},
  year      = {2023},
  publisher = {Springer},
  doi       = {10.1007/s00778-022-00776-8}
}

@inproceedings{yu2018spider,
  author    = {Yu, Tao and Zhang, Rui and Yang, Kai and Yasunaga, Michihiro and Wang, Dongxu and Li, Zifan and Ma, James and Li, Irene and Yao, Qingning and Roman, Shanelle and Zhang, Zilin and Radev, Dragomir},
  title     = {{Spider}: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-{SQL} Task},
  booktitle = {Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
  pages     = {387--398},
  year      = {2018},
  address   = {Brussels, Belgium},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/D18-1036}
}

@inproceedings{li2023bird,
  author    = {Li, Jinyang and Hui, Binyuan and Qu, Ge and Yang, Jiaxi and Li, Binhua and Li, Bowen and Wang, Bailin and Qin, Bowen and Geng, Ruiying and Huo, Nan and Zhou, Chang and Ma, Jun and Li, Yongbin},
  title     = {Can {LLM} Already Serve as a Database Interface? {A} {BIg} Bench for Large-Scale Database Grounded Text-to-{SQL} ({BIRD})},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS 2023)},
  volume    = {36},
  pages     = {42431--42459},
  year      = {2023},
  address   = {New Orleans, LA, USA}
}

@inproceedings{pourreza2023dinsql,
  author    = {Pourreza, Mohammadreza and Rafiei, Davood},
  title     = {{DIN-SQL}: Decomposed In-Context Learning of Text-to-{SQL} with Self-Correction},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS 2023)},
  volume    = {36},
  pages     = {36338--36350},
  year      = {2023},
  address   = {New Orleans, LA, USA}
}

@online{owasp2023llmtop10,
  author       = {{OWASP Foundation}},
  title        = {{OWASP} Top 10 for Large Language Model Applications (Version 1.1)},
  organization = {Open Web Application Security Project},
  year         = {2023},
  url          = {https://owasp.org/www-project-top-10-for-large-language-model-applications/}
}

@inproceedings{raasveldt2019duckdb,
  author    = {Raasveldt, Mark and M{\"u}hleisen, Hannes},
  title     = {{DuckDB}: an Embeddable Analytical Database},
  booktitle = {Proceedings of the 2019 International Conference on Management of Data (SIGMOD '19)},
  pages     = {1981--1984},
  year      = {2019},
  address   = {Amsterdam, Netherlands},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3299869.3320212}
}
```
