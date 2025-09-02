import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Dict, Any
import typesense
from typing import Dict, List, Any
import logging
import time
import uuid
import random
import string
from config import settings


logger = logging.getLogger(__name__)


class TypesenseClient:
    def __init__(
            self,
            host: str = "localhost",
            port: int = 6211,
            protocol: str = "http",
            api_key: str = "avision",
            connection_timeout_seconds: int = 10,
            retry_interval_seconds: float = 0.1,
            num_retries: int = 3,
            embedding_dim: int = 1024
    ):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.api_key = api_key
        self.connection_timeout_seconds = connection_timeout_seconds
        self.retry_interval_seconds = retry_interval_seconds
        self.num_retries = num_retries
        self.embedding_dim = embedding_dim

        self.client_config = {
            'nodes': [{
                'host': self.host,
                'port': self.port,
                'protocol': self.protocol
            }],
            'api_key': self.api_key,
            'connection_timeout_seconds': self.connection_timeout_seconds
        }
        self._init_client_with_retry()

    def _init_client_with_retry(self):
        """Khởi tạo client với cơ chế retry."""
        retry_count = 0
        while retry_count < self.num_retries:
            try:
                self.client = typesense.Client(self.client_config)
                # Kiểm tra kết nối bằng cách truy xuất danh sách collection
                self.client.collections.retrieve()
                logger.info("Kết nối Typesense thành công")
                return
            except Exception as e:
                retry_count += 1
                logger.warning(f"Kết nối Typesense thất bại (lần {retry_count}/{self.num_retries}): {e}")
                if retry_count < self.num_retries:
                    time.sleep(self.retry_interval_seconds)
        logger.error("Kết nối Typesense thất bại sau nhiều lần thử")
        raise ConnectionError("Không thể kết nối đến server Typesense")

    # -------- Schema cho collection tài liệu của chatbot --------
    def _get_document_schema(self, chatbot_name: str) -> Dict[str, Any]:
        schema = {
            "name": chatbot_name,
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "text", "type": "string"},
                {"name": "page_num", "type": "int32"},
                {"name": "chunk_num", "type": "int32"},
                {"name": "start_index", "type": "int32"},
                {"name": "end_index", "type": "int32"},
                {"name": "embedding", "type": "float[]", "num_dim": self.embedding_dim}
            ]
        }
        return schema

    # -------- Schema cho collection thông tin chatbot chung --------
    def _get_chatbot_info_schema(self) -> Dict[str, Any]:
        schema = {
            "name": "chatbot_info",
            "fields": [
                {"name": "name", "type": "string"},
                {"name": "description", "type": "string"},
                {"name": "id", "type": "string"},
                {"name": "api_key", "type": "string"}
            ]
        }
        return schema

    def _collection_exists(self, collection_name: str) -> bool:
        try:
            collections = self.client.collections.retrieve()
            return any(col["name"] == collection_name for col in collections)
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra sự tồn tại của collection '{collection_name}': {e}")
            return False

    def _generate_random_api_key(self, length: int = 32) -> str:
        """Tạo một API key ngẫu nhiên."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def _get_next_chatbot_id(self) -> str:
        """
        Lấy id chatbot tiếp theo dựa trên các document trong collection 'chatbot_info'.
        Nếu chưa có chatbot nào, trả về "0".
        """
        try:
            # Lấy tất cả các document trong chatbot_info với limit 250 (giới hạn của Typesense)
            docs = self.client.collections["chatbot_info"].documents.search({
                "q": "*",
                "query_by": "name",
                "limit": 250  # thay vì 1000 để tránh lỗi 422
            })
            existing_ids = []
            if docs.get("hits"):
                for hit in docs["hits"]:
                    doc = hit["document"]
                    # Giả sử field "id" là một số dạng string
                    try:
                        existing_ids.append(int(doc.get("id", "0")))
                    except Exception:
                        continue
            return str(max(existing_ids) + 1) if existing_ids else "0"
        except Exception as e:
            logger.error(f"Lỗi khi lấy chatbot_id tiếp theo: {e}")
            # Nếu có lỗi, trả về uuid
            return str(uuid.uuid4())

    # --------------- Chatbot operations ---------------
    def create_chatbot(self, chatbot_name: str, description: str) -> Dict[str, Any]:
        """
        Tạo chatbot mới:
          - Tạo collection tài liệu với tên chatbot_name.
          - Đảm bảo collection 'chatbot_info' tồn tại.
          - Thêm document vào 'chatbot_info' chứa thông tin của chatbot.
        """
        # Tạo collection thông tin chung nếu chưa tồn tại
        if not self._collection_exists("chatbot_info"):
            try:
                info_schema = self._get_chatbot_info_schema()
                self.client.collections.create(info_schema)
                logger.info("Tạo collection 'chatbot_info' thành công")
            except typesense.exceptions.ObjectAlreadyExists:
                logger.info("Collection 'chatbot_info' đã tồn tại")
            except Exception as e:
                logger.error(f"Lỗi khi tạo collection 'chatbot_info': {e}")
                raise

        # Tạo collection tài liệu cho chatbot
        doc_schema = self._get_document_schema(chatbot_name)
        try:
            self.client.collections.create(doc_schema)
            logger.info(f"Tạo collection tài liệu '{chatbot_name}' thành công")
        except typesense.exceptions.ObjectAlreadyExists:
            logger.info(f"Collection tài liệu '{chatbot_name}' đã tồn tại")
        except Exception as e:
            logger.error(f"Lỗi khi tạo collection tài liệu '{chatbot_name}': {e}")
            raise

        # Lấy chatbot id mới (số tăng dần)
        chatbot_id = self._get_next_chatbot_id()
        api_key = self._generate_random_api_key()

        # Tạo document meta cho chatbot
        chatbot_meta = {
            "id": chatbot_id,
            "name": chatbot_name,
            "description": description,
            "api_key": api_key
        }
        try:
            self.client.collections["chatbot_info"].documents.create(chatbot_meta)
            logger.info(f"Đã index thông tin chatbot '{chatbot_name}' vào 'chatbot_info'")
        except typesense.exceptions.ObjectAlreadyExists:
            logger.info(f"Thông tin chatbot '{chatbot_name}' đã tồn tại trong 'chatbot_info'")
        except Exception as e:
            logger.error(f"Lỗi khi index thông tin chatbot: {e}")
            raise

        return chatbot_meta

    def get_chatbot(self, chatbot_name: str) -> Dict[str, Any]:
        """
        Lấy thông tin của chatbot từ collection 'chatbot_info' bằng cách tìm kiếm theo field 'name'.
        """
        try:
            result = self.client.collections["chatbot_info"].documents.search({
                "q": chatbot_name,
                "query_by": "name",
                "limit": 1
            })
            if result.get("hits") and len(result["hits"]) > 0:
                return result["hits"][0]["document"]
            else:
                return {"error": f"Không tìm thấy chatbot '{chatbot_name}'"}
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin chatbot '{chatbot_name}': {e}")
            return {"error": str(e)}

    def update_chatbot(self, chatbot_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật thông tin chatbot trong collection 'chatbot_info'.
        Tìm document theo field 'name' và update.
        """
        try:
            # Tìm document theo field name
            result = self.client.collections["chatbot_info"].documents.search({
                "q": chatbot_name,
                "query_by": "name",
                "limit": 1
            })
            if result.get("hits") and len(result["hits"]) > 0:
                doc_id = result["hits"][0]["document"]["id"]
                updated_doc = self.client.collections["chatbot_info"].documents[doc_id].update(update_data)
                logger.info(f"Cập nhật thông tin chatbot '{chatbot_name}' thành công")
                return updated_doc
            else:
                return {"error": f"Không tìm thấy chatbot '{chatbot_name}' để cập nhật"}
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin chatbot '{chatbot_name}': {e}")
            return {"error": str(e)}

    def delete_chatbot(self, chatbot_name: str) -> Dict[str, Any]:
        """
        Xóa chatbot: xóa collection tài liệu có tên chatbot_name và xóa document tương ứng trong 'chatbot_info'.
        """
        responses = {}
        # Xóa collection tài liệu của chatbot
        try:
            responses["documents_collection"] = self.client.collections[chatbot_name].delete()
            logger.info(f"Xóa collection tài liệu '{chatbot_name}' thành công")
        except Exception as e:
            logger.error(f"Lỗi khi xóa collection tài liệu '{chatbot_name}': {e}")
            responses["documents_collection_error"] = str(e)
        # Xóa document meta trong 'chatbot_info'
        try:
            result = self.client.collections["chatbot_info"].documents.search({
                "q": chatbot_name,
                "query_by": "name",
                "limit": 1
            })
            if result.get("hits") and len(result["hits"]) > 0:
                doc_id = result["hits"][0]["document"]["id"]
                responses["chatbot_info"] = self.client.collections["chatbot_info"].documents[doc_id].delete()
                logger.info(f"Xóa thông tin chatbot '{chatbot_name}' khỏi 'chatbot_info' thành công")
            else:
                responses["chatbot_info_error"] = f"Không tìm thấy chatbot '{chatbot_name}' trong 'chatbot_info'"
        except Exception as e:
            logger.error(f"Lỗi khi xóa thông tin chatbot '{chatbot_name}': {e}")
            responses["chatbot_info_error"] = str(e)
        return responses

    def create_collection_if_not_exists(self) -> Dict[str, Any]:
        """
        Đảm bảo rằng luôn tồn tại một chatbot có tên 'chatbot_master'
        với description là 'original chatbot'. Nếu chưa tồn tại, tạo mới.
        """
        meta = self.get_chatbot("chatbot_master")
        if "error" in meta:
            logger.info("Chatbot 'chatbot_master' không tồn tại, tiến hành tạo mới.")
            meta = self.create_chatbot("chatbot_master", "original chatbot")
        return meta

    # --------------- Document operations ---------------
    def add_document(self, chatbot_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thêm document vào collection tài liệu của chatbot.
        Document phải tuân theo schema đã định nghĩa.
        """
        if not document:
            raise ValueError("Document là bắt buộc")
        try:
            response = self.client.collections[chatbot_name].documents.create(document)
            logger.info(f"Thêm document vào '{chatbot_name}' thành công")
            return response
        except Exception as e:
            logger.error(f"Lỗi khi thêm document vào '{chatbot_name}': {e}")
            raise

    def get_document(self, chatbot_name: str, document_id: str) -> Dict[str, Any]:
        """
        Lấy document từ collection tài liệu của chatbot theo document_id.
        """
        try:
            doc = self.client.collections[chatbot_name].documents[document_id].retrieve()
            return doc
        except Exception as e:
            logger.error(f"Lỗi khi lấy document '{document_id}' từ '{chatbot_name}': {e}")
            return {"error": str(e)}

    def update_document(self, chatbot_name: str, document_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật document trong collection tài liệu của chatbot.
        """
        try:
            updated_doc = self.client.collections[chatbot_name].documents[document_id].update(update_data)
            logger.info(f"Cập nhật document '{document_id}' trong '{chatbot_name}' thành công")
            return updated_doc
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật document '{document_id}' trong '{chatbot_name}': {e}")
            return {"error": str(e)}

    def delete_document(self, chatbot_name: str, document_title: str):
        """
        Xóa tất cả document từ collection dựa vào title

        Args:
            chatbot_name: Tên của chatbot (collection)
            document_title: Title của document cần xóa

        Returns:
            Kết quả xóa document
        """
        try:
            # Kiểm tra collection có tồn tại không
            try:
                self.client.collections[chatbot_name].retrieve()
            except Exception as e:
                logger.error(f"Collection '{chatbot_name}' không tồn tại: {e}")
                raise Exception(f"Collection '{chatbot_name}' không tồn tại: {e}")

            # Thử sử dụng batch delete nếu API hỗ trợ
            try:
                delete_query = {
                    "filter_by": f"title:={document_title}"
                }
                batch_delete_result = self.client.collections[chatbot_name].documents.delete(delete_query)
                logger.info(
                    f"Đã xóa tất cả document với title='{document_title}' từ collection '{chatbot_name}' bằng batch delete")
                return {
                    "status": "success",
                    "message": f"Đã xóa tất cả document với title='{document_title}' từ chatbot '{chatbot_name}'",
                    "result": batch_delete_result
                }
            except Exception as batch_err:
                # Batch delete không hoạt động, chuyển sang phương pháp 2 sử dụng phân trang
                logger.info(f"Batch delete không thành công ({batch_err}), chuyển sang phương pháp phân trang")

                total_deleted = 0
                all_deleted_docs = []

                # Tìm tổng số document cần xóa (chỉ cần lấy thông tin, không cần kết quả chi tiết)
                count_params = {
                    "q": "*",
                    "filter_by": f"title:={document_title}",
                    "per_page": 0  # Chỉ lấy tổng số, không lấy kết quả
                }
                count_results = self.client.collections[chatbot_name].documents.search(count_params)
                total_to_delete = count_results["found"]

                if total_to_delete == 0:
                    logger.warning(
                        f"Không tìm thấy document nào với title '{document_title}' trong collection '{chatbot_name}'")
                    return {
                        "status": "error",
                        "message": f"Không tìm thấy document nào với title '{document_title}' trong collection '{chatbot_name}'"
                    }

                # Lấy và xóa document theo từng trang (tối đa 250 mỗi trang)
                page = 1
                per_page = 250  # Giới hạn của Typesense

                while total_deleted < total_to_delete:
                    search_parameters = {
                        "q": "*",
                        "filter_by": f"title:={document_title}",
                        "per_page": per_page,
                        "page": page
                    }

                    search_results = self.client.collections[chatbot_name].documents.search(search_parameters)

                    if len(search_results["hits"]) == 0:
                        break  # Không còn document nào

                    # Xóa từng document trong trang hiện tại
                    batch_result = []
                    for hit in search_results["hits"]:
                        doc_id = hit["document"]["id"]
                        try:
                            delete_result = self.client.collections[chatbot_name].documents[doc_id].delete()
                            batch_result.append(delete_result)
                            total_deleted += 1
                        except Exception as del_err:
                            logger.error(f"Lỗi khi xóa document id={doc_id}: {del_err}")

                    all_deleted_docs.extend(batch_result)
                    logger.info(
                        f"Đã xóa {len(batch_result)} document trong trang {page}, tổng số đã xóa: {total_deleted}/{total_to_delete}")

                    # Không tăng page number vì chúng ta luôn lấy trang đầu tiên
                    # (sau khi xóa trang 1, trang 2 trở thành trang 1 mới)

                # Kiểm tra lại sau khi xóa
                final_check = self.client.collections[chatbot_name].documents.search(count_params)
                remaining = final_check["found"]

                if remaining > 0:
                    logger.warning(f"Vẫn còn {remaining} document với title='{document_title}' sau khi xóa")

                return {
                    "status": "success",
                    "message": f"Đã xóa {total_deleted} document với title='{document_title}' từ chatbot '{chatbot_name}'",
                    "result": {
                        "deleted_count": total_deleted,
                        "remaining": remaining
                    }
                }
        except Exception as e:
            logger.error(f"Lỗi khi xóa document '{document_title}' từ '{chatbot_name}': {e}")
            raise

    # --------------- Search operations ---------------
    def search_documents(self, chatbot_name: str, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Tìm kiếm full-text trong field 'text' của collection tài liệu.
        """
        try:
            result = self.client.collections[chatbot_name].documents.search({
                "q": query,
                "query_by": "text",
                "limit": limit
            })
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm trong '{chatbot_name}': {e}")
            return {"error": str(e)}

    def vector_search(self, chatbot_name: str, vector: List[float], limit: int = 10) -> Dict[str, Any]:
        """
        Tìm kiếm theo vector embedding trong field 'embedding' của collection tài liệu.
        """
        vector_str = ",".join(str(x) for x in vector)
        try:
            result = self.client.collections[chatbot_name].documents.search({
                "q": "*",
                "vector_query": f"embedding:([{vector_str}], k:{limit})",
                "limit": limit
            })
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm vector trong '{chatbot_name}': {e}")
            return {"error": str(e)}

    def hybrid_search(self, chatbot_name: str, query: str, vector: List[float], limit: int = 10) -> Dict[str, Any]:
        """
        Thực hiện hybrid search: kết hợp full-text search trên 'text' và vector search trên 'embedding'.
        """
        vector_str = ",".join(str(x) for x in vector)
        try:
            result = self.client.collections[chatbot_name].documents.search({
                "q": query,
                "query_by": "text",
                "vector_query": f"embedding:([{vector_str}], k:{limit})",
                "limit": limit
            })
            return result
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện hybrid search trong '{chatbot_name}': {e}")
            return {"error": str(e)}

    def multi_search(self, queries: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực hiện multi search trên nhiều query (có thể trên nhiều collection) và trả về kết quả.
        """
        try:
            result = self.client.multi_search.perform(queries)
            return result
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện multi search: {e}")
            return {"error": str(e)}


_typesense_client_instance = None

def get_typesense_instance_service() -> TypesenseClient:
    """
    Returns the singleton instance of the EmbeddingModel.
    Initializes it if it hasn't been initialized yet.
    """
    global _typesense_client_instance
    if _typesense_client_instance is None:
        _typesense_client_instance = TypesenseClient(
            host=settings.TYPESENSE_HOST,
            port=settings.TYPESENSE_PORT,
            protocol=settings.TYPESENSE_PROTOCOL,
            api_key=settings.TYPESENSE_API_KEY,
            embedding_dim=settings.EMBEDDING_DIMENSION
        ) # Instantiate your wrapper class
    return _typesense_client_instance


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quản lý chatbot và tài liệu trong Typesense")
    parser.add_argument("--host", default="localhost", help="Typesense host")
    parser.add_argument("--port", type=int, default=6211, help="Typesense port")
    parser.add_argument("--protocol", default="http", help="HTTP protocol")
    parser.add_argument("--api-key", default="avision", help="API key")
    parser.add_argument("--chatbot", required=True, help="Tên của chatbot")
    parser.add_argument("--action", choices=["create", "delete", "info", "update", "ensure_master"], default="create",
                        help="Hành động cần thực hiện")
    parser.add_argument("--dim", type=int, default=1024, help="Kích thước embedding")
    parser.add_argument("--description", default="", help="Mô tả của chatbot")
    # Các tham số cho document nếu cần thêm/sửa document
    parser.add_argument("--doc_id", default=None, help="ID của document")
    parser.add_argument("--title", default="", help="Title (tên file)")
    parser.add_argument("--text", default="", help="Nội dung document")
    parser.add_argument("--page_num", type=int, default=0, help="Số trang")
    parser.add_argument("--chunk_num", type=int, default=0, help="Thứ tự chunk")
    parser.add_argument("--start_index", type=int, default=0, help="Index bắt đầu")
    parser.add_argument("--end_index", type=int, default=0, help="Index kết thúc")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    client = TypesenseClient(
        host=args.host,
        port=args.port,
        protocol=args.protocol,
        api_key=args.api_key,
        embedding_dim=args.dim
    )

    if args.action == "create":
        result = client.create_chatbot(args.chatbot, args.description)
        print(f"Created chatbot: {result}")
    elif args.action == "info":
        result = client.get_chatbot(args.chatbot)
        print(f"Chatbot info: {result}")
    elif args.action == "update":
        update_data = {"description": args.description}
        result = client.update_chatbot(args.chatbot, update_data)
        print(f"Updated chatbot: {result}")
    elif args.action == "delete":
        result = client.delete_chatbot(args.chatbot)
        print(f"Deleted chatbot: {result}")
    elif args.action == "ensure_master":
        result = client.create_collection_if_not_exists()
        print(f"Ensured chatbot_master exists: {result}")